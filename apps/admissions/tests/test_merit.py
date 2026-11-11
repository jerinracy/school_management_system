"""Unit tests for merit calculation and quota seat allocation."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.academics.models import ClassLevel
from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTest,
    AdmissionTestResult,
    Application,
    ApplicationStatus,
    CircularStatus,
    GenderChoices,
    MeritType,
    QuotaRule,
    QuotaType,
)
from apps.admissions.services.merit_calculator import generate_merit_list
from apps.institutions.models import AcademicSession, Institution


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(name_bn="মেধা স্কুল", name_en="Merit School", eiin="998877")


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
    return ClassLevel.objects.create(institution=institution, name="Class 9", code="c09", order=9)


@pytest.fixture
def circular(
    institution: Institution, session: AcademicSession, class_level: ClassLevel
) -> AdmissionCircular:
    return AdmissionCircular.objects.create(
        institution=institution,
        session=session,
        class_level=class_level,
        title="Class 9 Merit Admission",
        seats_available=2,  # Only 2 seats: 1 Quota + 1 General Merit
        application_fee=Decimal("150.00"),
        form_open_date=date(2025, 1, 1),
        form_close_date=date(2027, 12, 31),
        status=CircularStatus.PUBLISHED,
    )


@pytest.mark.django_db
class TestMeritCalculator:
    def test_merit_list_with_test_scores_and_quota(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        # Create quota rule: 1 seat for Freedom Fighter
        QuotaRule.objects.create(
            institution=institution,
            circular=circular,
            quota_type=QuotaType.FREEDOM_FIGHTER,
            name="FF Quota",
            reserved_seats=1,
            priority=1,
        )

        test = AdmissionTest.objects.create(
            institution=institution,
            circular=circular,
            title="Entrance Exam",
            test_date=timezone.now(),
            venue="Exam Hall",
            total_marks=Decimal("100.00"),
            pass_marks=Decimal("40.00"),
        )

        # Candidate 1: General Merit, Score 95
        app1 = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00001",
            name_bn="সাধারণ ১",
            name_en="General High",
            dob=date(2011, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no="20110000000000001",
            guardian_name="Guardian 1",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.PAID,
            quota_type=QuotaType.GENERAL,
        )
        AdmissionTestResult.objects.create(
            institution=institution,
            test=test,
            application=app1,
            marks_obtained=Decimal("95.00"),
            is_passed=True,
        )

        # Candidate 2: General Merit, Score 90
        app2 = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00002",
            name_bn="সাধারণ ২",
            name_en="General Med",
            dob=date(2011, 1, 2),
            gender=GenderChoices.MALE,
            birth_reg_no="20110000000000002",
            guardian_name="Guardian 2",
            guardian_phone="+8801711000002",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.PAID,
            quota_type=QuotaType.GENERAL,
        )
        AdmissionTestResult.objects.create(
            institution=institution,
            test=test,
            application=app2,
            marks_obtained=Decimal("90.00"),
            is_passed=True,
        )

        # Candidate 3: Freedom Fighter Quota, Score 75
        app3 = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00003",
            name_bn="মুক্তিযোদ্ধা",
            name_en="Freedom Fighter Candidate",
            dob=date(2011, 1, 3),
            gender=GenderChoices.MALE,
            birth_reg_no="20110000000000003",
            guardian_name="Guardian 3",
            guardian_phone="+8801711000003",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.PAID,
            quota_type=QuotaType.FREEDOM_FIGHTER,
        )
        AdmissionTestResult.objects.create(
            institution=institution,
            test=test,
            application=app3,
            marks_obtained=Decimal("75.00"),
            is_passed=True,
        )

        merit_list = generate_merit_list(
            circular_id=circular.id,
            selection_criteria="test_score",
            title="Class 9 1st Merit List",
        )

        assert merit_list.entries.count() == 3
        selected_entries = list(merit_list.entries.filter(is_selected=True))
        assert len(selected_entries) == 2  # Exactly total_seats (2)

        selected_app_ids = [e.application_id for e in selected_entries]
        # Candidate 3 must be selected via Quota
        assert app3.id in selected_app_ids
        # Candidate 1 must be selected via General Merit (highest score)
        assert app1.id in selected_app_ids
        # Candidate 2 must be on Waiting list
        waiting_entry = merit_list.entries.get(is_selected=False)
        assert waiting_entry.application_id == app2.id
        assert waiting_entry.merit_type == MeritType.WAITING
