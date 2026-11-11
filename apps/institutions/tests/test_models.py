"""Model tests for institutions, tenancy, and constraints."""

from datetime import date, time

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.institutions.models import (
    AcademicSession,
    Branch,
    EducationBoard,
    Holiday,
    HolidayType,
    Institution,
    InstitutionType,
    MPOStatus,
    SessionStatus,
    Shift,
    ShiftName,
    Term,
)


@pytest.fixture
def institution_a(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Collegiate School",
        name_bn="ঢাকা কলেজিয়েট স্কুল",
        eiin="100001",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Kotwali",
        phone="+8801711111111",
    )


@pytest.fixture
def institution_b(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Chittagong Collegiate School",
        name_bn="চট্টগ্রাম কলেজিয়েট স্কুল",
        eiin="100002",
        board=EducationBoard.CHITTAGONG,
        type=InstitutionType.SECONDARY,
        division="Chittagong",
        district="Chittagong",
        upazila="Kotwali",
        phone="+8801811111111",
    )


@pytest.mark.django_db
class TestInstitutionModels:
    def test_create_institution_defaults(self, institution_a: Institution) -> None:
        assert institution_a.mpo_status == MPOStatus.NON_MPO
        assert institution_a.timezone == "Asia/Dhaka"
        assert institution_a.currency == "BDT"
        assert institution_a.weekend_days == ["friday", "saturday"]
        assert institution_a.settings["bangla_digits"] is True

    def test_single_current_session_per_institution_constraint(
        self, institution_a: Institution, institution_b: Institution
    ) -> None:
        # Create first current session for institution A
        session_a1 = AcademicSession.objects.create(
            institution=institution_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        assert session_a1.is_current is True

        # Attempting to create second current session for institution A must fail constraint
        with transaction.atomic(), pytest.raises(IntegrityError):
            AcademicSession.objects.create(
                institution=institution_a,
                name="2027",
                start_date=date(2027, 1, 1),
                end_date=date(2027, 12, 31),
                is_current=True,
                status=SessionStatus.PLANNED,
            )

        # Different institution B CAN have its own current session
        session_b1 = AcademicSession.objects.create(
            institution=institution_b,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        assert session_b1.is_current is True

    def test_branch_code_uniqueness_per_institution(
        self, institution_a: Institution, institution_b: Institution
    ) -> None:
        Branch.objects.create(
            institution=institution_a,
            name="Main Branch",
            code="MAIN",
            is_main=True,
        )

        # Duplicate code in same institution should fail
        with transaction.atomic(), pytest.raises(IntegrityError):
            Branch.objects.create(
                institution=institution_a,
                name="Duplicate Main",
                code="MAIN",
            )

        # Same code in different institution is allowed
        branch_b = Branch.objects.create(
            institution=institution_b,
            name="Main Branch B",
            code="MAIN",
            is_main=True,
        )
        assert branch_b.code == "MAIN"

    def test_shift_uniqueness_and_validation(self, institution_a: Institution) -> None:
        branch = Branch.objects.create(
            institution=institution_a,
            name="Main Campus",
            code="CAMPUS-1",
        )
        Shift.objects.create(
            institution=institution_a,
            branch=branch,
            name=ShiftName.MORNING,
            start_time=time(7, 30),
            end_time=time(12, 0),
        )

        # Duplicate shift name for same branch
        with transaction.atomic(), pytest.raises(IntegrityError):
            Shift.objects.create(
                institution=institution_a,
                branch=branch,
                name=ShiftName.MORNING,
                start_time=time(8, 0),
                end_time=time(12, 30),
            )

        # Shift clean validation: start_time >= end_time
        invalid_shift = Shift(
            institution=institution_a,
            branch=branch,
            name=ShiftName.DAY,
            start_time=time(17, 0),
            end_time=time(12, 0),
        )
        with pytest.raises(ValidationError):
            invalid_shift.clean()

    def test_term_ordering_and_date_bounds(self, institution_a: Institution) -> None:
        session = AcademicSession.objects.create(
            institution=institution_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=SessionStatus.ACTIVE,
        )
        Term.objects.create(
            institution=institution_a,
            session=session,
            name="First Term",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 4, 30),
            order=1,
        )

        # Duplicate order in same session fails
        with transaction.atomic(), pytest.raises(IntegrityError):
            Term.objects.create(
                institution=institution_a,
                session=session,
                name="Second Term",
                start_date=date(2026, 5, 1),
                end_date=date(2026, 8, 31),
                order=1,
            )

        # Term outside session range fails clean validation
        out_of_bounds_term = Term(
            institution=institution_a,
            session=session,
            name="Out of bounds",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 4, 30),
            order=2,
        )
        with pytest.raises(ValidationError):
            out_of_bounds_term.clean()

    def test_holiday_validation(self, institution_a: Institution) -> None:
        holiday = Holiday(
            institution=institution_a,
            name="Invalid holiday",
            type=HolidayType.GOVT,
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 5),  # End before start
        )
        with pytest.raises(ValidationError):
            holiday.clean()
