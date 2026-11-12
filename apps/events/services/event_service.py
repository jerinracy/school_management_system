"""Business logic for Notice Board receipts, Unified Calendar, Event RSVPs, and Certificate PDFs."""

from datetime import date, datetime, time
from io import BytesIO
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from apps.accounts.models import User
from apps.communications.models import Notice
from apps.events.models import (
    Certificate,
    Event,
    EventRSVP,
    NoticeReadReceipt,
    RSVPStatus,
)
from apps.institutions.models import Holiday, Institution
from apps.students.models import Student


def mark_notice_as_read(
    *,
    institution: Institution,
    notice: Notice,
    user: User,
) -> tuple[NoticeReadReceipt, bool]:
    """Idempotently record a NoticeReadReceipt for a user."""
    if notice.institution_id != institution.id:
        raise ValidationError("Notice does not belong to this institution.")
    receipt, created = NoticeReadReceipt.objects.get_or_create(
        institution=institution,
        notice=notice,
        user=user,
    )
    return receipt, created


def get_notice_read_summary(*, institution: Institution, notice: Notice) -> dict[str, Any]:
    """Return read receipt count and recent readers for a notice."""
    if notice.institution_id != institution.id:
        raise ValidationError("Notice does not belong to this institution.")
    qs = NoticeReadReceipt.objects.filter(institution=institution, notice=notice).select_related(
        "user"
    )
    total_reads = qs.count()
    return {
        "notice_id": str(notice.id),
        "total_reads": total_reads,
        "recent_readers": [
            {
                "user_id": str(r.user_id),
                "username": r.user.username,
                "read_at": r.read_at.isoformat(),
            }
            for r in qs.order_by("-read_at")[:25]
        ],
    }


@transaction.atomic
def rsvp_to_event(
    *,
    institution: Institution,
    event: Event,
    user: User,
    status: str = RSVPStatus.GOING,
    student: Student | None = None,
    note: str = "",
) -> EventRSVP:
    """Create or update an EventRSVP, enforcing requires_rsvp and max_participants."""
    if event.institution_id != institution.id:
        raise ValidationError("Event does not belong to this institution.")
    if not event.is_published:
        raise ValidationError("Cannot RSVP to an unpublished event.")
    if not event.requires_rsvp:
        raise ValidationError("This event does not accept RSVPs.")
    if student is not None and student.institution_id != institution.id:
        raise ValidationError("Student does not belong to this institution.")

    locked_event = Event.objects.select_for_update().get(id=event.id)
    existing = EventRSVP.objects.filter(
        institution=institution,
        event=locked_event,
        user=user,
    ).first()

    if status == RSVPStatus.GOING and locked_event.max_participants is not None:
        going_count = (
            EventRSVP.objects.filter(
                institution=institution,
                event=locked_event,
                status=RSVPStatus.GOING,
            )
            .exclude(user=user)
            .count()
        )
        if going_count >= locked_event.max_participants:
            raise ValidationError("Event has reached maximum participant capacity.")

    if existing:
        existing.status = status
        existing.student = student
        existing.note = note
        existing.save(update_fields=["status", "student", "note", "responded_at", "updated_at"])
        return existing

    return EventRSVP.objects.create(
        institution=institution,
        event=locked_event,
        user=user,
        student=student,
        status=status,
        note=note,
    )


def get_unified_calendar(
    *,
    institution: Institution,
    start_date: date,
    end_date: date,
    include_unpublished: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate Events, Holidays, and published Notices into a unified chronological calendar."""
    if end_date < start_date:
        raise ValidationError("end_date cannot be earlier than start_date.")

    tz = timezone.get_current_timezone()
    range_start = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    range_end = timezone.make_aware(datetime.combine(end_date, time.max), tz)

    items: list[dict[str, Any]] = []

    # 1. Events overlapping [range_start, range_end]
    event_qs = Event.objects.filter(
        institution=institution,
        is_deleted=False,
        start_datetime__lte=range_end,
        end_datetime__gte=range_start,
    )
    if not include_unpublished:
        event_qs = event_qs.filter(is_published=True)

    for ev in event_qs.order_by("start_datetime"):
        items.append(
            {
                "id": str(ev.id),
                "source_type": "event",
                "category": ev.category,
                "title_en": ev.title_en,
                "title_bn": ev.title_bn,
                "description": ev.description_en,
                "start": ev.start_datetime.isoformat(),
                "end": ev.end_datetime.isoformat(),
                "is_all_day": ev.is_all_day,
                "venue": ev.venue,
                "is_pinned": False,
            }
        )

    # 2. Holidays overlapping [start_date, end_date]
    holiday_qs = Holiday.objects.filter(
        institution=institution,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).order_by("start_date")

    for hol in holiday_qs:
        items.append(
            {
                "id": str(hol.id),
                "source_type": "holiday",
                "category": hol.type,
                "title_en": hol.name,
                "title_bn": "",
                "description": hol.description,
                "start": hol.start_date.isoformat(),
                "end": hol.end_date.isoformat(),
                "is_all_day": True,
                "venue": "",
                "is_pinned": False,
            }
        )

    # 3. Published Notices active in [start_date, end_date]
    notice_qs = Notice.objects.filter(
        institution=institution,
        is_deleted=False,
        is_published=True,
        publish_date__date__lte=end_date,
    ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__date__gte=start_date))

    for notice in notice_qs.order_by("-is_pinned", "-publish_date"):
        items.append(
            {
                "id": str(notice.id),
                "source_type": "notice",
                "category": notice.category,
                "title_en": notice.title_en,
                "title_bn": notice.title_bn,
                "description": notice.content_en,
                "start": notice.publish_date.isoformat(),
                "end": notice.expiry_date.isoformat() if notice.expiry_date else None,
                "is_all_day": False,
                "venue": "",
                "is_pinned": notice.is_pinned,
            }
        )

    items.sort(key=lambda item: str(item["start"]))
    return items


def generate_certificate_pdf(certificate: Certificate) -> bytes:
    """Render a landscape A4 PDF certificate using reportlab."""
    buffer = BytesIO()
    width, height = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Border frame
    pdf.setLineWidth(3)
    pdf.rect(36, 36, width - 72, height - 72)
    pdf.setLineWidth(1)
    pdf.rect(44, 44, width - 88, height - 88)

    # Header
    inst_name = getattr(certificate.institution, "name_en", None) or getattr(
        certificate.institution, "name", "School Management System"
    )
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, height - 105, str(inst_name))

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 160, "CERTIFICATE OF ACHIEVEMENT")

    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 210, "This certificate is proudly presented to")

    student_name = certificate.student.name_en or certificate.student.name_bn
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 255, student_name)

    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(
        width / 2,
        height - 285,
        f"Student ID: {certificate.student.student_id}",
    )

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 335, certificate.title_en)

    if certificate.achievement and certificate.achievement.description:
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width / 2, height - 365, certificate.achievement.description[:110])

    # Footer metadata & signatory
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 90, f"Certificate No: {certificate.certificate_number}")
    pdf.drawString(72, 72, f"Issued Date: {certificate.issued_date.isoformat()}")

    sig_name = certificate.signatory_name or "Head Teacher"
    sig_title = certificate.signatory_title or "Authorized Signatory"
    pdf.drawRightString(width - 72, 95, sig_name)
    pdf.line(width - 230, 110, width - 72, 110)
    pdf.drawRightString(width - 72, 78, sig_title)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def get_event_rsvp_counts(event_id: UUID) -> dict[str, int]:
    """Return RSVP status counts for an event."""
    rows = EventRSVP.objects.filter(event_id=event_id).values("status").annotate(total=Count("id"))
    counts = {
        RSVPStatus.GOING.value: 0,
        RSVPStatus.INTERESTED.value: 0,
        RSVPStatus.DECLINED.value: 0,
    }
    for row in rows:
        counts[row["status"]] = row["total"]
    return counts
