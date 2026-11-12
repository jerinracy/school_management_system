"""Circulation services: policy resolution, issue, return, renew, and reservation queue."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Q, Sum
from django.utils import timezone

from apps.fees.models import Invoice, InvoiceStatus
from apps.library.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookIssue,
    BookIssueStatus,
    LibraryFine,
    LibraryFineReason,
    LibraryFineStatus,
    LibraryMember,
    LibraryMemberStatus,
    LibraryPolicy,
    Reservation,
    ReservationStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EffectiveLibraryPolicy:
    """Resolved circulation policy values for a member type."""

    max_books: int = 3
    loan_days: int = 14
    max_renewals: int = 1
    renewal_days: int = 7
    fine_per_day: Decimal = Decimal("5.00")
    grace_days: int = 0
    block_issue_on_library_fines: bool = True
    block_issue_on_fee_dues: bool = False
    max_unpaid_fine_threshold: Decimal = Decimal("0.00")
    reservation_hold_hours: int = 48


def get_effective_policy(
    *,
    institution: Any,
    member_type: str,
    branch: Any = None,
) -> EffectiveLibraryPolicy:
    """Resolve branch-specific policy, institution default policy, or safe defaults."""
    policy: LibraryPolicy | None = None
    if branch is not None:
        policy = LibraryPolicy.objects.filter(
            institution=institution,
            branch=branch,
            member_type=member_type,
        ).first()
    if policy is None:
        policy = LibraryPolicy.objects.filter(
            institution=institution,
            branch__isnull=True,
            member_type=member_type,
        ).first()
    if policy is None:
        return EffectiveLibraryPolicy()
    return EffectiveLibraryPolicy(
        max_books=policy.max_books,
        loan_days=policy.loan_days,
        max_renewals=policy.max_renewals,
        renewal_days=policy.renewal_days,
        fine_per_day=policy.fine_per_day,
        grace_days=policy.grace_days,
        block_issue_on_library_fines=policy.block_issue_on_library_fines,
        block_issue_on_fee_dues=policy.block_issue_on_fee_dues,
        max_unpaid_fine_threshold=policy.max_unpaid_fine_threshold,
        reservation_hold_hours=policy.reservation_hold_hours,
    )


def _get_unpaid_library_fine_total(member: LibraryMember) -> Decimal:
    """Return total unpaid balance across active library fines for a member."""
    agg = LibraryFine.objects.filter(
        institution_id=member.institution_id,
        member=member,
        status__in=[LibraryFineStatus.UNPAID, LibraryFineStatus.PARTIALLY_PAID],
    ).aggregate(outstanding=Sum(F("amount") - F("paid_amount")))
    return agg["outstanding"] or Decimal("0.00")


def _notify_reservation_ready(reservation: Reservation) -> None:
    """Best-effort notification when a reserved copy becomes ready for pickup."""
    try:
        from apps.accounts.models import User, UserType
        from apps.communications.services.notification_service import dispatch_event_notification

        user = None
        if reservation.member.student_id and reservation.member.student:
            user = User.objects.filter(
                institution_id=reservation.institution_id,
                username=reservation.member.student.student_id,
                user_type=UserType.STUDENT,
            ).first()
        elif reservation.member.staff_id and reservation.member.staff:
            user = getattr(reservation.member.staff, "user", None)
        if user is None:
            return
        dispatch_event_notification(
            institution=reservation.institution,
            event_type="library_reservation_ready",
            recipient_users=[user],
            context={
                "book_title": reservation.book.title,
                "card_number": reservation.member.card_number,
                "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else "",
            },
            source_module="library",
            reference_id=reservation.id,
        )
    except Exception:
        logger.exception("Failed to dispatch library reservation ready notification")


def resolve_member_for_circulation(
    *,
    institution: Any,
    member_id: Any = None,
    card_number: str | None = None,
    rfid_card_uid: str | None = None,
    lock: bool = False,
) -> LibraryMember:
    """Find an active LibraryMember by ID, card number, or RFID UID within tenant."""
    qs = LibraryMember.objects.filter(institution=institution, is_deleted=False)
    if lock:
        qs = qs.select_for_update()

    if member_id:
        member = qs.filter(id=member_id).first()
    elif card_number:
        member = qs.filter(card_number=card_number).first()
    elif rfid_card_uid:
        member = qs.filter(rfid_card_uid=rfid_card_uid).first()
    else:
        raise ValidationError("Provide member_id, card_number, or rfid_card_uid.")

    if member is None:
        raise ValidationError("Library member not found.")
    return member


def resolve_copy_for_circulation(
    *,
    institution: Any,
    copy_id: Any = None,
    accession_no: str | None = None,
    barcode: str | None = None,
    rfid_tag: str | None = None,
    lock: bool = False,
) -> BookCopy:
    """Find a BookCopy by ID, accession number, barcode, or RFID tag within tenant."""
    qs = BookCopy.objects.select_related("book").filter(institution=institution, is_deleted=False)
    if lock:
        qs = qs.select_for_update()

    if copy_id:
        copy = qs.filter(id=copy_id).first()
    elif accession_no:
        copy = qs.filter(accession_no=accession_no).first()
    elif barcode:
        copy = qs.filter(barcode=barcode).first()
    elif rfid_tag:
        copy = qs.filter(rfid_tag=rfid_tag).first()
    else:
        raise ValidationError("Provide copy_id, accession_no, barcode, or rfid_tag.")

    if copy is None:
        raise ValidationError("Book copy not found.")
    return copy


def _promote_next_reservation_or_free_copy(
    *,
    copy: BookCopy,
    policy: EffectiveLibraryPolicy,
) -> None:
    """Assign returned/unclaimed copy to next queued reservation or mark available."""
    next_res = (
        Reservation.objects.select_for_update()
        .select_related("member", "member__student", "member__staff", "book", "institution")
        .filter(
            institution_id=copy.institution_id,
            book_id=copy.book_id,
            status=ReservationStatus.QUEUED,
        )
        .order_by("queue_position", "reserved_at")
        .first()
    )
    if next_res is not None:
        now = timezone.now()
        copy.status = BookCopyStatus.RESERVED
        copy.save(update_fields=["status", "updated_at"])
        next_res.status = ReservationStatus.READY_FOR_PICKUP
        next_res.fulfilled_copy = copy
        next_res.notified_at = now
        next_res.expires_at = now + timedelta(hours=policy.reservation_hold_hours)
        next_res.save(
            update_fields=[
                "status",
                "fulfilled_copy",
                "notified_at",
                "expires_at",
                "updated_at",
            ]
        )
        _notify_reservation_ready(next_res)
    else:
        copy.status = BookCopyStatus.AVAILABLE
        copy.save(update_fields=["status", "updated_at"])


def _validate_copy_for_issue(
    *,
    institution: Any,
    copy: BookCopy,
    member: LibraryMember,
) -> Reservation | None:
    """Validate copy availability and return any matching READY_FOR_PICKUP reservation."""
    if copy.book.is_deleted:
        raise ValidationError("This book catalog entry has been deleted.")
    if copy.book.is_reference_only:
        raise ValidationError("Reference-only books cannot be issued.")
    if copy.status == BookCopyStatus.RESERVED:
        matching_ready_res = (
            Reservation.objects.select_for_update()
            .filter(
                institution=institution,
                book=copy.book,
                member=member,
                status=ReservationStatus.READY_FOR_PICKUP,
            )
            .filter(Q(fulfilled_copy=copy) | Q(fulfilled_copy__isnull=True))
            .first()
        )
        if matching_ready_res is None:
            raise ValidationError("This book copy is reserved for another member.")
        return matching_ready_res
    if copy.status != BookCopyStatus.AVAILABLE:
        raise ValidationError(f"Book copy is currently '{copy.status}' and unavailable for issue.")
    return None


def _validate_member_eligibility_for_issue(
    *,
    institution: Any,
    member: LibraryMember,
    policy: EffectiveLibraryPolicy,
    today: date,
) -> None:
    """Validate member status, active borrowing limit, library fines, and school fee dues."""
    if member.status != LibraryMemberStatus.ACTIVE:
        raise ValidationError(f"Library member is {member.status} and cannot borrow books.")
    if member.expiry_date and member.expiry_date < today:
        raise ValidationError("Library membership has expired.")

    active_count = BookIssue.objects.filter(
        institution=institution,
        member=member,
        status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE],
    ).count()
    if active_count >= policy.max_books:
        raise ValidationError(
            f"Borrowing limit reached ({active_count}/{policy.max_books} active books)."
        )

    if policy.block_issue_on_library_fines:
        unpaid_total = _get_unpaid_library_fine_total(member)
        if unpaid_total > policy.max_unpaid_fine_threshold:
            raise ValidationError(
                f"Member has unpaid library fines ({unpaid_total} BDT) exceeding allowed threshold."
            )

    if policy.block_issue_on_fee_dues and member.student_id:
        has_fee_dues = Invoice.objects.filter(
            institution=institution,
            student_id=member.student_id,
            is_deleted=False,
            status__in=[
                InvoiceStatus.ISSUED,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.OVERDUE,
            ],
            due_amount__gt=Decimal("0.00"),
        ).exists()
        if has_fee_dues:
            raise ValidationError("Member has unpaid school fee dues.")


@transaction.atomic
def issue_book(
    *,
    institution: Any,
    actor: Any = None,
    member_id: Any = None,
    card_number: str | None = None,
    rfid_card_uid: str | None = None,
    copy_id: Any = None,
    accession_no: str | None = None,
    barcode: str | None = None,
    rfid_tag: str | None = None,
    due_date: date | None = None,
    remarks: str = "",
) -> BookIssue:
    """Atomically validate eligibility and issue a physical BookCopy to a LibraryMember."""
    member = resolve_member_for_circulation(
        institution=institution,
        member_id=member_id,
        card_number=card_number,
        rfid_card_uid=rfid_card_uid,
        lock=True,
    )
    copy = resolve_copy_for_circulation(
        institution=institution,
        copy_id=copy_id,
        accession_no=accession_no,
        barcode=barcode,
        rfid_tag=rfid_tag,
        lock=True,
    )

    today = timezone.localdate()
    policy = get_effective_policy(
        institution=institution,
        member_type=member.member_type,
        branch=copy.branch or member.branch,
    )
    _validate_member_eligibility_for_issue(
        institution=institution, member=member, policy=policy, today=today
    )
    matching_ready_res = _validate_copy_for_issue(institution=institution, copy=copy, member=member)

    effective_due_date = due_date or (today + timedelta(days=policy.loan_days))
    if effective_due_date < today:
        raise ValidationError("Due date cannot be in the past.")

    issue = BookIssue.objects.create(
        institution=institution,
        copy=copy,
        member=member,
        issued_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
        issue_date=today,
        due_date=effective_due_date,
        status=BookIssueStatus.ISSUED,
        remarks=remarks,
    )
    copy.status = BookCopyStatus.ISSUED
    copy.save(update_fields=["status", "updated_at"])

    if matching_ready_res is not None:
        matching_ready_res.status = ReservationStatus.FULFILLED
        matching_ready_res.fulfilled_copy = copy
        matching_ready_res.save(update_fields=["status", "fulfilled_copy", "updated_at"])

    return issue


@transaction.atomic
def return_book(
    *,
    institution: Any,
    actor: Any = None,
    issue_id: Any = None,
    accession_no: str | None = None,
    barcode: str | None = None,
    rfid_tag: str | None = None,
    return_date: date | None = None,
    mark_damaged: bool = False,
    mark_lost: bool = False,
    damage_fine_amount: Decimal | None = None,
    remarks: str = "",
) -> BookIssue:
    """Return an active BookIssue, assess overdue/loss/damage fines, and trigger reservation hold."""
    if mark_damaged and mark_lost:
        raise ValidationError("Cannot mark a book as both damaged and lost.")

    issue_qs = (
        BookIssue.objects.select_for_update()
        .select_related("copy", "copy__book", "member")
        .filter(
            institution=institution,
            status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE],
        )
    )
    if issue_id:
        issue = issue_qs.filter(id=issue_id).first()
    else:
        copy = resolve_copy_for_circulation(
            institution=institution,
            accession_no=accession_no,
            barcode=barcode,
            rfid_tag=rfid_tag,
            lock=True,
        )
        issue = issue_qs.filter(copy=copy).first()

    if issue is None:
        raise ValidationError("Active book issue record not found.")

    copy = BookCopy.objects.select_for_update().select_related("book").get(id=issue.copy_id)
    effective_return_date = return_date or timezone.localdate()
    policy = get_effective_policy(
        institution=institution,
        member_type=issue.member.member_type,
        branch=copy.branch or issue.member.branch,
    )

    if mark_lost:
        issue.status = BookIssueStatus.LOST
        issue.return_date = effective_return_date
        copy.status = BookCopyStatus.LOST
        copy.save(update_fields=["status", "updated_at"])
        loss_amount = copy.price if copy.price > Decimal("0.00") else Decimal("0.00")
        if loss_amount > Decimal("0.00"):
            LibraryFine.objects.create(
                institution=institution,
                issue=issue,
                member=issue.member,
                reason=LibraryFineReason.LOST,
                overdue_days=0,
                amount=loss_amount,
            )
    else:
        raw_overdue_days = max(0, (effective_return_date - issue.due_date).days)
        chargeable_days = max(0, raw_overdue_days - policy.grace_days)
        if chargeable_days > 0 and policy.fine_per_day > Decimal("0.00"):
            overdue_amount = Decimal(chargeable_days) * policy.fine_per_day
            LibraryFine.objects.create(
                institution=institution,
                issue=issue,
                member=issue.member,
                reason=LibraryFineReason.OVERDUE,
                overdue_days=chargeable_days,
                amount=overdue_amount,
            )

        issue.status = BookIssueStatus.RETURNED
        issue.return_date = effective_return_date

        if mark_damaged:
            copy.status = BookCopyStatus.DAMAGED
            copy.save(update_fields=["status", "updated_at"])
            if damage_fine_amount and damage_fine_amount > Decimal("0.00"):
                LibraryFine.objects.create(
                    institution=institution,
                    issue=issue,
                    member=issue.member,
                    reason=LibraryFineReason.DAMAGED,
                    overdue_days=0,
                    amount=damage_fine_amount,
                )
        else:
            _promote_next_reservation_or_free_copy(copy=copy, policy=policy)

    issue.returned_to = actor if actor and getattr(actor, "is_authenticated", False) else None
    if remarks:
        issue.remarks = f"{issue.remarks}\n{remarks}".strip() if issue.remarks else remarks
    issue.save(update_fields=["status", "return_date", "returned_to", "remarks", "updated_at"])
    return issue


@transaction.atomic
def renew_book(
    *,
    institution: Any,
    issue_id: Any,
    extra_days: int | None = None,
) -> BookIssue:
    """Renew an active BookIssue if renewal limits, fines, and reservation queue permit."""
    issue = (
        BookIssue.objects.select_for_update()
        .select_related("copy", "copy__book", "member")
        .filter(
            institution=institution,
            id=issue_id,
            status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE],
        )
        .first()
    )
    if issue is None:
        raise ValidationError("Active book issue record not found.")

    policy = get_effective_policy(
        institution=institution,
        member_type=issue.member.member_type,
        branch=issue.copy.branch or issue.member.branch,
    )
    if issue.renewal_count >= policy.max_renewals:
        raise ValidationError(
            f"Renewal limit reached ({issue.renewal_count}/{policy.max_renewals})."
        )

    has_waiting_reservation = Reservation.objects.filter(
        institution=institution,
        book=issue.copy.book,
        status=ReservationStatus.QUEUED,
    ).exists()
    if has_waiting_reservation:
        raise ValidationError("Cannot renew: another member has reserved this book.")

    if policy.block_issue_on_library_fines:
        unpaid_total = _get_unpaid_library_fine_total(issue.member)
        if unpaid_total > policy.max_unpaid_fine_threshold:
            raise ValidationError("Cannot renew while unpaid library fines exceed threshold.")

    days_to_add = extra_days if extra_days and extra_days > 0 else policy.renewal_days
    base_date = max(issue.due_date, timezone.localdate())
    issue.due_date = base_date + timedelta(days=days_to_add)
    issue.renewal_count += 1
    issue.status = BookIssueStatus.ISSUED
    issue.save(update_fields=["due_date", "renewal_count", "status", "updated_at"])
    return issue


@transaction.atomic
def reserve_book(
    *,
    institution: Any,
    book: Book,
    member: LibraryMember,
) -> Reservation:
    """Place a FIFO reservation for a Book on behalf of an active LibraryMember."""
    if book.institution_id != institution.id or book.is_deleted:
        raise ValidationError("Book not found in this institution.")
    if member.institution_id != institution.id or member.is_deleted:
        raise ValidationError("Library member not found in this institution.")
    if member.status != LibraryMemberStatus.ACTIVE:
        raise ValidationError("Only active library members can place reservations.")

    already_reserved = Reservation.objects.filter(
        institution=institution,
        book=book,
        member=member,
        status__in=[ReservationStatus.QUEUED, ReservationStatus.READY_FOR_PICKUP],
    ).exists()
    if already_reserved:
        raise ValidationError("Member already has an active reservation for this book.")

    max_pos = (
        Reservation.objects.filter(
            institution=institution,
            book=book,
            status__in=[ReservationStatus.QUEUED, ReservationStatus.READY_FOR_PICKUP],
        ).aggregate(pos=Max("queue_position"))["pos"]
        or 0
    )

    return Reservation.objects.create(
        institution=institution,
        book=book,
        member=member,
        queue_position=max_pos + 1,
        status=ReservationStatus.QUEUED,
    )


@transaction.atomic
def cancel_reservation(*, institution: Any, reservation: Reservation) -> Reservation:
    """Cancel an active reservation and promote the next queued member if a copy was held."""
    locked = (
        Reservation.objects.select_for_update()
        .select_related("fulfilled_copy", "book")
        .get(id=reservation.id, institution=institution)
    )
    if locked.status not in [ReservationStatus.QUEUED, ReservationStatus.READY_FOR_PICKUP]:
        raise ValidationError(f"Reservation in '{locked.status}' state cannot be cancelled.")

    held_copy = locked.fulfilled_copy
    was_ready = locked.status == ReservationStatus.READY_FOR_PICKUP
    locked.status = ReservationStatus.CANCELLED
    locked.fulfilled_copy = None
    locked.save(update_fields=["status", "fulfilled_copy", "updated_at"])

    if was_ready and held_copy is not None and held_copy.status == BookCopyStatus.RESERVED:
        policy = get_effective_policy(
            institution=institution,
            member_type=locked.member.member_type,
            branch=held_copy.branch,
        )
        _promote_next_reservation_or_free_copy(copy=held_copy, policy=policy)

    return locked
