"""Tests for library borrowing limits, renewals, fine calculation, payments/waivers, and dues blocking."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.fees.models import Invoice, InvoiceStatus, InvoiceType
from apps.institutions.models import AcademicSession, Branch, Institution
from apps.library.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookIssueStatus,
    LibraryFine,
    LibraryFineStatus,
    LibraryMember,
    LibraryMemberType,
    LibraryPolicy,
)
from apps.library.services import (
    issue_book,
    record_fine_payment,
    renew_book,
    reserve_book,
    return_book,
    waive_fine,
)
from apps.staff.models import Staff
from apps.students.models import Gender, Student


@pytest.mark.django_db
class TestLibraryCirculationAndFines:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Dhaka Model School", name_bn="ঢাকা মডেল স্কুল"
        )
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="MAIN", is_main=True
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.librarian = User.objects.create_user(
            username="librarian",
            password="pass",
            institution=self.inst,
            user_type=UserType.STAFF,
        )
        self.student = Student.objects.create(
            institution=self.inst,
            student_id="STU-001",
            name_en="Nusrat Jahan",
            name_bn="নুসরাত জাহান",
            dob=date(2012, 4, 15),
            gender=Gender.FEMALE,
            admission_date=date(2026, 1, 10),
            emergency_contact_name="Abdul Karim",
            emergency_contact_phone="+8801711000001",
        )
        self.staff = Staff.objects.create(
            institution=self.inst,
            employee_id="TCH-001",
            full_name_en="Kamrul Hasan",
            phone="+8801711000002",
            dob=date(1985, 6, 10),
            joining_date=date(2018, 1, 1),
        )
        self.student_member = LibraryMember.objects.create(
            institution=self.inst,
            member_type=LibraryMemberType.STUDENT,
            student=self.student,
            branch=self.branch,
            card_number="LIB-S-001",
        )
        self.teacher_member = LibraryMember.objects.create(
            institution=self.inst,
            member_type=LibraryMemberType.TEACHER,
            staff=self.staff,
            branch=self.branch,
            card_number="LIB-T-001",
        )
        LibraryPolicy.objects.create(
            institution=self.inst,
            member_type=LibraryMemberType.STUDENT,
            max_books=2,
            loan_days=7,
            max_renewals=1,
            renewal_days=5,
            fine_per_day=Decimal("10.00"),
            grace_days=1,
            block_issue_on_library_fines=True,
            block_issue_on_fee_dues=True,
        )
        LibraryPolicy.objects.create(
            institution=self.inst,
            member_type=LibraryMemberType.TEACHER,
            max_books=5,
            loan_days=30,
            max_renewals=2,
            renewal_days=14,
            fine_per_day=Decimal("0.00"),
            block_issue_on_library_fines=False,
        )
        self.book1 = Book.objects.create(
            institution=self.inst, title="Physics 101", authors="Dr. Ali", isbn="978-0001"
        )
        self.book2 = Book.objects.create(
            institution=self.inst, title="Chemistry 101", authors="Dr. Rahman", isbn="978-0002"
        )
        self.book3 = Book.objects.create(
            institution=self.inst, title="Bangla Sahitya", authors="Prof. Sen", isbn="978-0003"
        )
        self.ref_book = Book.objects.create(
            institution=self.inst,
            title="Banglapedia Vol 1",
            authors="Asiatic Society",
            is_reference_only=True,
        )
        self.copy1 = BookCopy.objects.create(
            institution=self.inst,
            book=self.book1,
            branch=self.branch,
            accession_no="ACC-1",
            barcode="BC-1",
        )
        self.copy2 = BookCopy.objects.create(
            institution=self.inst,
            book=self.book2,
            branch=self.branch,
            accession_no="ACC-2",
            barcode="BC-2",
        )
        self.copy3 = BookCopy.objects.create(
            institution=self.inst,
            book=self.book3,
            branch=self.branch,
            accession_no="ACC-3",
            barcode="BC-3",
        )
        self.ref_copy = BookCopy.objects.create(
            institution=self.inst, book=self.ref_book, branch=self.branch, accession_no="ACC-REF"
        )

    def test_loan_limit_and_reference_only_enforcement(self) -> None:
        with pytest.raises(ValidationError, match="Reference-only"):
            issue_book(
                institution=self.inst,
                actor=self.librarian,
                member_id=self.student_member.id,
                copy_id=self.ref_copy.id,
            )

        issue_book(
            institution=self.inst, actor=self.librarian, card_number="LIB-S-001", barcode="BC-1"
        )
        issue_book(
            institution=self.inst, actor=self.librarian, card_number="LIB-S-001", barcode="BC-2"
        )

        with pytest.raises(ValidationError, match="Borrowing limit reached"):
            issue_book(
                institution=self.inst, actor=self.librarian, card_number="LIB-S-001", barcode="BC-3"
            )

    def test_renewal_limits_and_reservation_block(self) -> None:
        issue = issue_book(
            institution=self.inst,
            actor=self.librarian,
            member_id=self.student_member.id,
            copy_id=self.copy1.id,
        )
        original_due = issue.due_date
        renewed = renew_book(institution=self.inst, issue_id=issue.id)
        assert renewed.renewal_count == 1
        assert renewed.due_date == original_due + timedelta(days=5)

        with pytest.raises(ValidationError, match="Renewal limit reached"):
            renew_book(institution=self.inst, issue_id=issue.id)

        # Teacher policy allows 2 renewals, but a queued reservation blocks renewal
        t_issue = issue_book(
            institution=self.inst,
            actor=self.librarian,
            member_id=self.teacher_member.id,
            copy_id=self.copy2.id,
        )
        reserve_book(institution=self.inst, book=self.book2, member=self.student_member)
        with pytest.raises(ValidationError, match="reserved this book"):
            renew_book(institution=self.inst, issue_id=t_issue.id)

    def test_overdue_fine_calculation_block_and_payment_waiver(self) -> None:
        today = timezone.localdate()
        issue = issue_book(
            institution=self.inst,
            actor=self.librarian,
            member_id=self.student_member.id,
            copy_id=self.copy1.id,
        )
        # Return 4 days after due_date -> with grace_days=1 => 3 chargeable days * 10.00 = 30.00
        returned = return_book(
            institution=self.inst,
            actor=self.librarian,
            issue_id=issue.id,
            return_date=issue.due_date + timedelta(days=4),
        )
        assert returned.status == BookIssueStatus.RETURNED
        self.copy1.refresh_from_db()
        assert self.copy1.status == BookCopyStatus.AVAILABLE

        fine = LibraryFine.objects.get(issue=returned)
        assert fine.overdue_days == 3
        assert fine.amount == Decimal("30.00")
        assert fine.status == LibraryFineStatus.UNPAID

        # Unpaid fine blocks next issue
        with pytest.raises(ValidationError, match="unpaid library fines"):
            issue_book(
                institution=self.inst,
                actor=self.librarian,
                member_id=self.student_member.id,
                copy_id=self.copy2.id,
            )

        # Partial payment still blocks, full payment unblocks
        record_fine_payment(fine=fine, amount=Decimal("10.00"), payment_reference="RCPT-1")
        fine.refresh_from_db()
        assert fine.status == LibraryFineStatus.PARTIALLY_PAID
        with pytest.raises(ValidationError, match="unpaid library fines"):
            issue_book(
                institution=self.inst,
                actor=self.librarian,
                member_id=self.student_member.id,
                copy_id=self.copy2.id,
            )

        record_fine_payment(fine=fine, amount=Decimal("20.00"), payment_reference="RCPT-2")
        fine.refresh_from_db()
        assert fine.status == LibraryFineStatus.PAID

        # Now issuing succeeds (unless school fee dues exist)
        issue2 = issue_book(
            institution=self.inst,
            actor=self.librarian,
            member_id=self.student_member.id,
            copy_id=self.copy2.id,
        )
        assert issue2.status == BookIssueStatus.ISSUED

        # Test waiver on a lost book fine
        returned_lost = return_book(
            institution=self.inst, actor=self.librarian, issue_id=issue2.id, mark_lost=True
        )
        assert returned_lost.status == BookIssueStatus.LOST
        self.copy3.price = Decimal("500.00")
        self.copy3.save(update_fields=["price"])
        issue3 = issue_book(
            institution=self.inst,
            actor=self.librarian,
            member_id=self.student_member.id,
            copy_id=self.copy3.id,
        )
        return_book(institution=self.inst, actor=self.librarian, issue_id=issue3.id, mark_lost=True)
        lost_fine = LibraryFine.objects.get(issue=issue3)
        assert lost_fine.amount == Decimal("500.00")
        waive_fine(fine=lost_fine, actor=self.librarian, waive_reason="Replaced by student")
        lost_fine.refresh_from_db()
        assert lost_fine.status == LibraryFineStatus.WAIVED

        # Unpaid fee invoice blocks issue when block_issue_on_fee_dues=True
        Invoice.objects.create(
            institution=self.inst,
            invoice_number="INV-LIB-1",
            student=self.student,
            session=self.session,
            invoice_type=InvoiceType.MONTHLY,
            issue_date=today,
            due_date=today + timedelta(days=5),
            total_payable=Decimal("1000.00"),
            due_amount=Decimal("1000.00"),
            status=InvoiceStatus.ISSUED,
        )
        with pytest.raises(ValidationError, match="unpaid school fee dues"):
            issue_book(
                institution=self.inst,
                actor=self.librarian,
                member_id=self.student_member.id,
                copy_id=self.copy1.id,
            )
