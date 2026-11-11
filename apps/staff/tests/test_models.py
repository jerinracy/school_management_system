"""Unit tests for Staff, HR, and Leave models and constraints."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.academics.models import ClassLevel, Section, Subject
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import (
    Department,
    Designation,
    LeaveBalance,
    LeaveType,
    Staff,
    StaffStatus,
    StaffType,
    TeacherAssignment,
)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Collegiate School",
        name_bn="ঢাকা কলেজিয়েট স্কুল",
        eiin="112233",
    )


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Chittagong Collegiate School",
        name_bn="চট্টগ্রাম কলেজিয়েট স্কুল",
        eiin="445566",
    )


@pytest.fixture
def session(db, institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="Academic Year 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def branch(db, institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Branch", code="MAIN")


@pytest.fixture
def shift(db, branch) -> Shift:
    return Shift.objects.create(
        institution=branch.institution,
        branch=branch,
        name="morning",
        start_time="08:00",
        end_time="12:00",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="EMP-2026-00001",
        full_name_en="Dr. Anisur Rahman",
        phone="+8801711223344",
        gender="male",
        dob=date(1980, 5, 10),
        joining_date=date(2015, 1, 1),
        staff_type=StaffType.TEACHER,
        status=StaffStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestStaffModels:
    def test_department_and_designation(self, institution):
        dept = Department.objects.create(
            institution=institution,
            name="Science Department",
            code="SCI",
        )
        desig = Designation.objects.create(
            institution=institution,
            title="Senior Teacher",
            title_bn="সিনিয়র শিক্ষক",
            rank_order=2,
            role_category=StaffType.TEACHER,
        )
        assert str(dept) == "Science Department"
        assert "Senior Teacher" in str(desig)

    def test_unique_employee_id_per_institution(self, institution, other_institution, staff):
        # Same employee ID in same institution raises IntegrityError
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Staff.objects.create(
                    institution=institution,
                    employee_id="EMP-2026-00001",
                    full_name_en="Duplicate Staff",
                    phone="+8801799887766",
                    gender="female",
                    dob=date(1985, 3, 1),
                    joining_date=date(2020, 1, 1),
                )

        # Same employee ID in different institution is allowed
        other_staff = Staff.objects.create(
            institution=other_institution,
            employee_id="EMP-2026-00001",
            full_name_en="Other Staff",
            phone="+8801799887766",
            gender="female",
            dob=date(1985, 3, 1),
            joining_date=date(2020, 1, 1),
        )
        assert other_staff.id is not None

    def test_unique_active_staff_phone(self, institution, staff):
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Staff.objects.create(
                    institution=institution,
                    employee_id="EMP-2026-00002",
                    full_name_en="Second Staff",
                    phone="+8801711223344",  # duplicate phone
                    gender="male",
                    dob=date(1982, 1, 1),
                    joining_date=date(2018, 1, 1),
                )

        # Soft deleting allows re-registering phone
        staff.delete()
        new_staff = Staff.objects.create(
            institution=institution,
            employee_id="EMP-2026-00002",
            full_name_en="Second Staff",
            phone="+8801711223344",
            gender="male",
            dob=date(1982, 1, 1),
            joining_date=date(2018, 1, 1),
        )
        assert new_staff.id is not None

    def test_leave_balance_and_remaining_calculation(self, institution, session, staff):
        leave_type = LeaveType.objects.create(
            institution=institution,
            name="Casual Leave",
            code="CL",
            yearly_quota=20,
        )
        balance = LeaveBalance.objects.create(
            institution=institution,
            staff=staff,
            leave_type=leave_type,
            session=session,
            allocated_days=Decimal("20.0"),
            carried_forward_days=Decimal("2.0"),
            used_days=Decimal("5.0"),
            pending_days=Decimal("3.0"),
        )
        # 20 + 2 - 5 - 3 = 14.0
        assert balance.remaining_days == Decimal("14.0")

        # Unique per staff, leave_type, session
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                LeaveBalance.objects.create(
                    institution=institution,
                    staff=staff,
                    leave_type=leave_type,
                    session=session,
                    allocated_days=Decimal("10.0"),
                )

    def test_teacher_assignment_unique_constraint(self, institution, session, staff, shift):
        cls = ClassLevel.objects.create(institution=institution, name="Class 9", order=9)
        sec = Section.objects.create(
            institution=institution,
            session=session,
            class_level=cls,
            shift=shift,
            name="Section A",
        )
        subj = Subject.objects.create(institution=institution, name_en="Physics", code="PHY101")

        assignment = TeacherAssignment.objects.create(
            institution=institution,
            teacher=staff,
            subject=subj,
            section=sec,
            session=session,
            periods_per_week=4,
            is_primary_teacher=True,
        )
        assert "Physics" in str(assignment)

        # Duplicate assignment of same teacher, subject, section, session raises error
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                TeacherAssignment.objects.create(
                    institution=institution,
                    teacher=staff,
                    subject=subj,
                    section=sec,
                    session=session,
                    periods_per_week=2,
                )
