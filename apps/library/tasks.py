"""Celery background tasks for Library Management."""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.library.models import (
    BookCopy,
    BookCopyStatus,
    BookIssue,
    BookIssueStatus,
    Reservation,
    ReservationStatus,
)
from apps.library.services.circulation_service import (
    _promote_next_reservation_or_free_copy,
    get_effective_policy,
)

logger = logging.getLogger(__name__)


@shared_task(acks_late=True)
def sync_overdue_issues_and_notify() -> dict[str, int]:
    """Mark active BookIssues past due_date as OVERDUE and dispatch idempotent reminders."""
    today = timezone.localdate()
    overdue_issues = list(
        BookIssue.objects.select_related(
            "institution",
            "copy",
            "copy__book",
            "member",
            "member__student",
            "member__staff",
        ).filter(status=BookIssueStatus.ISSUED, due_date__lt=today)
    )
    updated_count = 0
    notified_count = 0

    for issue in overdue_issues:
        issue.status = BookIssueStatus.OVERDUE
        issue.save(update_fields=["status", "updated_at"])
        updated_count += 1

        try:
            from apps.accounts.models import User, UserType
            from apps.communications.services.notification_service import (
                dispatch_event_notification,
            )

            user = None
            if issue.member.student_id and issue.member.student:
                user = User.objects.filter(
                    institution_id=issue.institution_id,
                    username=issue.member.student.student_id,
                    user_type=UserType.STUDENT,
                ).first()
            elif issue.member.staff_id and issue.member.staff:
                user = getattr(issue.member.staff, "user", None)
            if user is not None:
                dispatch_event_notification(
                    institution=issue.institution,
                    event_type="library_overdue",
                    recipient_users=[user],
                    context={
                        "book_title": issue.copy.book.title,
                        "due_date": issue.due_date.isoformat(),
                        "accession_no": issue.copy.accession_no,
                    },
                    source_module="library",
                    reference_id=issue.id,
                )
                notified_count += 1
        except Exception:
            logger.exception("Failed to send overdue notification for issue %s", issue.id)

    return {"marked_overdue": updated_count, "notified": notified_count}


@shared_task(acks_late=True)
def expire_stale_reservations() -> dict[str, int]:
    """Expire READY_FOR_PICKUP reservations past expires_at and promote next queued member."""
    now = timezone.now()
    stale_ids = list(
        Reservation.objects.filter(
            status=ReservationStatus.READY_FOR_PICKUP,
            expires_at__isnull=False,
            expires_at__lt=now,
        ).values_list("id", flat=True)
    )

    expired_count = 0
    for res_id in stale_ids:
        with transaction.atomic():
            res = (
                Reservation.objects.select_for_update()
                .select_related("fulfilled_copy", "member")
                .filter(id=res_id, status=ReservationStatus.READY_FOR_PICKUP)
                .first()
            )
            if res is None:
                continue
            held_copy = res.fulfilled_copy
            res.status = ReservationStatus.EXPIRED
            res.fulfilled_copy = None
            res.save(update_fields=["status", "fulfilled_copy", "updated_at"])
            expired_count += 1

            if held_copy is not None:
                locked_copy = BookCopy.objects.select_for_update().get(id=held_copy.id)
                if locked_copy.status == BookCopyStatus.RESERVED:
                    policy = get_effective_policy(
                        institution=res.institution,
                        member_type=res.member.member_type,
                        branch=locked_copy.branch,
                    )
                    _promote_next_reservation_or_free_copy(copy=locked_copy, policy=policy)

    return {"expired": expired_count}
