"""Tests for FIFO reservation queue, hold promotion/expiry, and concurrency on last copy."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.institutions.models import Branch, Institution
from apps.library.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookIssue,
    LibraryMember,
    LibraryMemberType,
    ReservationStatus,
)
from apps.library.services import (
    cancel_reservation,
    issue_book,
    reserve_book,
    return_book,
)
from apps.library.tasks import expire_stale_reservations
from apps.students.models import Gender, Student


@pytest.mark.django_db
class TestLibraryReservationsAndConcurrency:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(name_en="Sylhet Grammar", name_bn="সিলেট গ্রামার")
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="M1", is_main=True
        )
        self.actor = User.objects.create_user(
            username="lib_staff",
            password="pass",
            institution=self.inst,
            user_type=UserType.STAFF,
        )
        self.students = [
            Student.objects.create(
                institution=self.inst,
                student_id=f"S-{i}",
                name_en=f"Student {i}",
                name_bn=f"শিক্ষার্থী {i}",
                dob=date(2011, 1, i),
                gender=Gender.MALE,
                admission_date=date(2026, 1, 10),
                emergency_contact_name="Guardian",
                emergency_contact_phone=f"+880171100001{i}",
            )
            for i in range(1, 4)
        ]
        self.members = [
            LibraryMember.objects.create(
                institution=self.inst,
                member_type=LibraryMemberType.STUDENT,
                student=s,
                branch=self.branch,
                card_number=f"CARD-{idx}",
            )
            for idx, s in enumerate(self.students, start=1)
        ]
        self.book = Book.objects.create(
            institution=self.inst,
            title="Higher Math",
            authors="Prof. Kabir",
            isbn="978-1111",
        )
        self.last_copy = BookCopy.objects.create(
            institution=self.inst,
            book=self.book,
            branch=self.branch,
            accession_no="LAST-001",
            barcode="BC-LAST-001",
        )

    def test_concurrency_prevent_double_issue_on_last_copy(self) -> None:
        issue1 = issue_book(
            institution=self.inst,
            actor=self.actor,
            member_id=self.members[0].id,
            copy_id=self.last_copy.id,
        )
        assert BookIssue.objects.filter(copy=self.last_copy).count() == 1
        assert issue1.member == self.members[0]

        with pytest.raises(ValidationError, match="unavailable for issue"):
            issue_book(
                institution=self.inst,
                actor=self.actor,
                member_id=self.members[1].id,
                copy_id=self.last_copy.id,
            )

    def test_fifo_reservation_queue_promotion_cancel_and_expiry(self) -> None:
        # Member 1 holds the only copy
        issue1 = issue_book(
            institution=self.inst,
            actor=self.actor,
            member_id=self.members[0].id,
            copy_id=self.last_copy.id,
        )
        # Member 2 and Member 3 reserve in FIFO order
        res2 = reserve_book(institution=self.inst, book=self.book, member=self.members[1])
        res3 = reserve_book(institution=self.inst, book=self.book, member=self.members[2])
        assert res2.queue_position == 1
        assert res3.queue_position == 2

        # Duplicate active reservation rejected
        with pytest.raises(ValidationError, match="already has an active reservation"):
            reserve_book(institution=self.inst, book=self.book, member=self.members[1])

        # Member 1 returns copy -> automatically reserved for Member 2
        return_book(institution=self.inst, actor=self.actor, issue_id=issue1.id)
        self.last_copy.refresh_from_db()
        res2.refresh_from_db()
        res3.refresh_from_db()
        assert self.last_copy.status == BookCopyStatus.RESERVED
        assert res2.status == ReservationStatus.READY_FOR_PICKUP
        assert res2.fulfilled_copy_id == self.last_copy.id
        assert res3.status == ReservationStatus.QUEUED

        # Member 3 cannot steal Member 2's held copy
        with pytest.raises(ValidationError, match="reserved for another member"):
            issue_book(
                institution=self.inst,
                actor=self.actor,
                member_id=self.members[2].id,
                copy_id=self.last_copy.id,
            )

        # Member 2 cancels -> automatically promotes Member 3
        cancel_reservation(institution=self.inst, reservation=res2)
        res3.refresh_from_db()
        assert res3.status == ReservationStatus.READY_FOR_PICKUP

        # Simulate Member 3 hold expiring -> task expires it and frees copy to AVAILABLE
        res3.expires_at = timezone.now() - timedelta(hours=1)
        res3.save(update_fields=["expires_at"])
        result = expire_stale_reservations()
        assert result["expired"] == 1
        res3.refresh_from_db()
        self.last_copy.refresh_from_db()
        assert res3.status == ReservationStatus.EXPIRED
        assert self.last_copy.status == BookCopyStatus.AVAILABLE
