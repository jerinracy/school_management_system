"""Unit tests for admission application state machine and eligibility validation."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel
from apps.admissions.models import (
    AdmissionCircular,
    Application,
    ApplicationStatus,
    CircularStatus,
    GenderChoices,
)
from apps.admissions.services.application_workflow import (
    generate_application_number,
    submit_application,
    transition_application_status,
    validate_applicant_eligibility,
)
from apps.institutions.models import AcademicSession, Institution


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(name_bn="ঢাকা স্কুল", name_en="Dhaka School", eiin="112233")


@pytest.fixture
def session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def class_level(institution: Institution) -> ClassLevel:
    return ClassLevel.objects.create(institution=institution, name="Class 6", code="c06", order=6)


@pytest.fixture
def circular(
    institution: Institution, session: AcademicSession, class_level: ClassLevel
) -> AdmissionCircular:
    return AdmissionCircular.objects.create(
        institution=institution,
        session=session,
        class_level=class_level,
        title="Admission 2026",
        seats_available=50,
        application_fee=Decimal("150.00"),
        form_open_date=date(2025, 1, 1),
        form_close_date=date(2027, 12, 31),
        eligibility_criteria={"min_age_years": 10, "max_age_years": 12, "min_gpa": 3.00},
        status=CircularStatus.PUBLISHED,
    )


@pytest.mark.django_db
class TestApplicationWorkflow:
    def test_generate_application_number_increments_sequence(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        num1 = generate_application_number(circular)
        assert num1 == "ADM-2026-00001"

        Application.objects.create(
            institution=institution,
            circular=circular,
            application_no=num1,
            name_bn="নাম ১",
            name_en="Name 1",
            dob=date(2015, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no="20150000000000001",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
        )
        num2 = generate_application_number(circular)
        assert num2 == "ADM-2026-00002"

    def test_validate_applicant_eligibility(self, circular: AdmissionCircular) -> None:
        # Valid: age approx 11, GPA 4.0
        validate_applicant_eligibility(
            circular=circular,
            dob=date(2015, 6, 1),
            previous_gpa=Decimal("4.00"),
        )

        # Invalid: age 5 (too young)
        with pytest.raises(ValidationError):
            validate_applicant_eligibility(
                circular=circular,
                dob=date(2021, 1, 1),
                previous_gpa=Decimal("4.00"),
            )

        # Invalid: low GPA
        with pytest.raises(ValidationError):
            validate_applicant_eligibility(
                circular=circular,
                dob=date(2015, 6, 1),
                previous_gpa=Decimal("2.50"),
            )

    def test_state_machine_valid_transitions(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00011",
            name_bn="আবেদনকারী",
            name_en="Applicant",
            dob=date(2015, 1, 1),
            gender=GenderChoices.FEMALE,
            birth_reg_no="20150000000000011",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.DRAFT,
        )

        # DRAFT -> SUBMITTED
        transition_application_status(application=app, new_status=ApplicationStatus.SUBMITTED)
        assert app.status == ApplicationStatus.SUBMITTED
        assert app.submitted_at is not None

        # SUBMITTED -> PAID
        transition_application_status(application=app, new_status=ApplicationStatus.PAID)
        assert app.status == ApplicationStatus.PAID

        # PAID -> SHORTLISTED
        transition_application_status(application=app, new_status=ApplicationStatus.SHORTLISTED)
        assert app.status == ApplicationStatus.SHORTLISTED

        # SHORTLISTED -> ADMITTED
        transition_application_status(application=app, new_status=ApplicationStatus.ADMITTED)
        assert app.status == ApplicationStatus.ADMITTED

    def test_state_machine_disallows_illegal_transitions(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00012",
            name_bn="আবেদনকারী",
            name_en="Applicant",
            dob=date(2015, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no="20150000000000012",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.DRAFT,
        )
        # Cannot jump DRAFT -> ADMITTED directly
        with pytest.raises(ValidationError):
            transition_application_status(application=app, new_status=ApplicationStatus.ADMITTED)

    def test_submit_application_with_zero_fee_auto_pays(
        self, institution: Institution, session: AcademicSession, class_level: ClassLevel
    ) -> None:
        free_circular = AdmissionCircular.objects.create(
            institution=institution,
            session=session,
            class_level=class_level,
            title="Free Admission 2026",
            seats_available=20,
            application_fee=Decimal("0.00"),
            form_open_date=date(2025, 1, 1),
            form_close_date=date(2027, 12, 31),
            status=CircularStatus.PUBLISHED,
        )
        app = Application.objects.create(
            institution=institution,
            circular=free_circular,
            application_no="ADM-2026-00099",
            name_bn="ফ্রি শিক্ষার্থী",
            name_en="Free Student",
            dob=date(2015, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no="20150000000000099",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.DRAFT,
        )
        submitted = submit_application(app.id)
        # Since fee is 0, auto-advances from SUBMITTED to PAID
        assert submitted.status == ApplicationStatus.PAID
