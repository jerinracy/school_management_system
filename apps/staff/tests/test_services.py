"""Service tests for staff onboarding, leave lifecycle, and teacher assignments."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import UserType
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import (
    GenderRestriction,
    LeaveBalance,
    LeaveRequestStatus,
    LeaveType,
    Staff,
    StaffType,
)
from apps.staff.selectors import get_teacher_workload_summary
from apps.staff.services import (
    apply_for_leave,
    approve_leave,
    assign_teacher_to_subject,
    cancel_leave,
    create_portal_user_for_staff,
    create_staff,
    generate_employee_id,
    initialize_leave_balances_for_session,
    recommend_leave,
    reject_leave,
    sync_academics_section_class_teacher,
    validate_no_leave_overlap,
)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Collegiate School",
        name_bn="ঢাকা কলেজিয়েট স্কুল",
        eiin="112233",
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
def teachers(db, institution) -> tuple[Staff, Staff]:
    t1 = create_staff(
        institution=institution,
        full_name_en="Mohammad Rafiq",
        phone="01711001122",
        gender="male",
        dob=date(1982, 6, 15),
        joining_date=date(2016, 2, 1),
        staff_type=StaffType.TEACHER,
    )
    t2 = create_staff(
        institution=institution,
        full_name_en="Farzana Yesmin",
        phone="01711334455",
        gender="female",
        dob=date(1988, 9, 20),
        joining_date=date(2019, 3, 1),
        staff_type=StaffType.TEACHER,
    )
    return t1, t2


@pytest.mark.django_db
class TestStaffServices:
    def test_employee_id_generation_and_staff_creation(self, institution):
        emp_id = generate_employee_id(institution)
        assert emp_id.startswith("EMP-")

        staff = create_staff(
            institution=institution,
            full_name_en="Nasir Uddin",
            phone="01819001122",  # Local format
            gender="male",
            dob=date(1985, 4, 1),
            joining_date=date(2018, 5, 1),
            is_mpo=True,
            mpo_index_number="MPO-987654",
        )
        assert staff.phone == "+8801819001122"
        assert staff.employee_id == emp_id
        assert staff.mpo_index_number == "MPO-987654"

    def test_create_portal_user_for_staff(self, institution, teachers):
        t1, _ = teachers
        user, temp_pw = create_portal_user_for_staff(t1)

        assert user.user_type == UserType.TEACHER
        assert user.phone == t1.phone
        assert user.check_password(temp_pw)
        t1.refresh_from_db()
        assert t1.user == user

    def test_initialize_leave_balances_gender_restriction(self, institution, session, teachers):
        t1, t2 = teachers  # t1 is male, t2 is female

        LeaveType.objects.create(
            institution=institution, name="Casual Leave", code="CL", yearly_quota=20
        )
        mat = LeaveType.objects.create(
            institution=institution,
            name="Maternity Leave",
            code="MAT",
            yearly_quota=180,
            gender_restriction=GenderRestriction.FEMALE,
        )

        created_count = initialize_leave_balances_for_session(institution, session)
        # t1 gets CL (1), t2 gets CL and MAT (2) -> total 3
        assert created_count == 3
        assert LeaveBalance.objects.filter(staff=t1, leave_type=mat).count() == 0
        assert LeaveBalance.objects.filter(staff=t2, leave_type=mat).count() == 1

    def test_leave_application_and_approval_flow(self, institution, session, teachers):
        t1, _ = teachers
        cl = LeaveType.objects.create(
            institution=institution, name="Casual Leave", code="CL", yearly_quota=20
        )
        initialize_leave_balances_for_session(institution, session)

        # 1. Apply for leave (3 days: Jan 10 to Jan 12)
        req = apply_for_leave(
            staff=t1,
            leave_type=cl,
            session=session,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 12),
            reason="Family emergency",
        )
        assert req.days_count == Decimal("3.0")
        assert req.status == LeaveRequestStatus.PENDING

        balance = LeaveBalance.objects.get(staff=t1, leave_type=cl, session=session)
        assert balance.pending_days == Decimal("3.0")
        assert balance.used_days == Decimal("0.0")
        assert balance.remaining_days == Decimal("17.0")

        # 2. Overlap validation prevents overlapping application
        with pytest.raises(ValidationError):
            validate_no_leave_overlap(t1, date(2026, 1, 11), date(2026, 1, 15))

        # 3. Recommend leave
        recommender = teachers[1]
        recommend_leave(req, recommender)
        req.refresh_from_db()
        assert req.status == LeaveRequestStatus.RECOMMENDED

        # 4. Approve leave
        approver = recommender
        approve_leave(req, approver)
        req.refresh_from_db()
        assert req.status == LeaveRequestStatus.APPROVED

        balance.refresh_from_db()
        assert balance.pending_days == Decimal("0.0")
        assert balance.used_days == Decimal("3.0")
        assert balance.remaining_days == Decimal("17.0")

        # 5. Cancel approved leave restores balance
        cancel_leave(req)
        req.refresh_from_db()
        assert req.status == LeaveRequestStatus.CANCELLED
        balance.refresh_from_db()
        assert balance.used_days == Decimal("0.0")
        assert balance.remaining_days == Decimal("20.0")

    def test_leave_rejection_restores_pending(self, institution, session, teachers):
        t1, t2 = teachers
        cl = LeaveType.objects.create(
            institution=institution, name="Casual Leave", code="CL", yearly_quota=10
        )
        initialize_leave_balances_for_session(institution, session)

        req = apply_for_leave(
            staff=t1,
            leave_type=cl,
            session=session,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 2),
            reason="Short trip",
        )
        balance = LeaveBalance.objects.get(staff=t1, leave_type=cl, session=session)
        assert balance.pending_days == Decimal("2.0")

        reject_leave(req, decider=t2, reason="Staff shortage on those dates")
        req.refresh_from_db()
        assert req.status == LeaveRequestStatus.REJECTED
        assert req.rejection_reason == "Staff shortage on those dates"

        balance.refresh_from_db()
        assert balance.pending_days == Decimal("0.0")
        assert balance.remaining_days == Decimal("10.0")

    def test_assignment_and_workload_summary(self, institution, session, teachers, shift):
        t1, _ = teachers
        cls = ClassLevel.objects.create(institution=institution, name="Class 10", order=10)
        sec = Section.objects.create(
            institution=institution, session=session, class_level=cls, shift=shift, name="Section B"
        )
        math = Subject.objects.create(
            institution=institution, name_en="Higher Mathematics", code="HMATH"
        )

        assign_teacher_to_subject(
            institution=institution,
            teacher=t1,
            subject=math,
            section=sec,
            session=session,
            periods_per_week=5,
            is_primary_teacher=True,
        )

        sync_academics_section_class_teacher(sec, t1)
        sec.refresh_from_db()
        assert sec.teacher_staff == t1

        summary = get_teacher_workload_summary(t1, session)
        assert summary["total_assigned_periods"] == 5
        assert summary["unique_subjects_count"] == 1
        assert summary["unique_sections_count"] == 1
