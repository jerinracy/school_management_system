"""Unit tests for admissions models and constraints."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academics.models import ClassLevel
from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTest,
    AdmissionTestResult,
    Application,
    CircularStatus,
    GenderChoices,
    QuotaRule,
    QuotaType,
)
from apps.institutions.models import AcademicSession, Institution


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা রেসিডেন্সিয়াল স্কুল",
        name_en="Dhaka Residential School",
        eiin="134567",
    )


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
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 6",
        code="c06",
        order=6,
    )


@pytest.fixture
def circular(
    institution: Institution, session: AcademicSession, class_level: ClassLevel
) -> AdmissionCircular:
    return AdmissionCircular.objects.create(
        institution=institution,
        session=session,
        class_level=class_level,
        title="Admission 2026 - Class 6",
        seats_available=100,
        application_fee=Decimal("200.00"),
        form_open_date=date(2025, 11, 1),
        form_close_date=date(2025, 12, 15),
        status=CircularStatus.PUBLISHED,
    )


@pytest.mark.django_db
class TestAdmissionCircularModel:
    def test_create_circular(self, circular: AdmissionCircular) -> None:
        assert circular.id is not None
        assert "Admission 2026" in str(circular)

    def test_duplicate_circular_per_session_class_raises_error(
        self,
        institution: Institution,
        session: AcademicSession,
        class_level: ClassLevel,
        circular: AdmissionCircular,
    ) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            AdmissionCircular.objects.create(
                institution=institution,
                session=session,
                class_level=class_level,
                title="Duplicate Circular",
                seats_available=50,
                form_open_date=date(2025, 11, 1),
                form_close_date=date(2025, 12, 15),
            )

    def test_clean_validates_dates(
        self, institution: Institution, session: AcademicSession, class_level: ClassLevel
    ) -> None:
        invalid_circular = AdmissionCircular(
            institution=institution,
            session=session,
            class_level=class_level,
            title="Bad Dates Circular",
            form_open_date=date(2025, 12, 15),
            form_close_date=date(2025, 11, 1),  # close before open
        )
        with pytest.raises(ValidationError):
            invalid_circular.clean()


@pytest.mark.django_db
class TestApplicationModel:
    def test_create_application_and_duplicate_check(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        app1 = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00001",
            name_bn="আরিফুল ইসলাম",
            name_en="Ariful Islam",
            dob=date(2014, 5, 10),
            gender=GenderChoices.MALE,
            birth_reg_no="20141234567890123",
            guardian_name="Rafiqul Islam",
            guardian_phone="+8801711000001",
            present_address="Mirpur, Dhaka",
            permanent_address="Cumilla",
        )
        assert app1.id is not None
        assert "ADM-2026-00001" in str(app1)

        # Duplicate BRN and DOB for same circular must raise IntegrityError
        with pytest.raises(IntegrityError), transaction.atomic():
            Application.objects.create(
                institution=institution,
                circular=circular,
                application_no="ADM-2026-00002",
                name_bn="আরিফুল ইসলাম ২",
                name_en="Ariful Islam 2",
                dob=date(2014, 5, 10),
                gender=GenderChoices.MALE,
                birth_reg_no="20141234567890123",  # Same BRN & DOB
                guardian_name="Rafiqul Islam",
                guardian_phone="+8801711000001",
                present_address="Dhaka",
                permanent_address="Cumilla",
            )


@pytest.mark.django_db
class TestQuotaRuleModel:
    def test_create_quota_rule(self, institution: Institution, circular: AdmissionCircular) -> None:
        quota = QuotaRule.objects.create(
            institution=institution,
            circular=circular,
            quota_type=QuotaType.FREEDOM_FIGHTER,
            name="Freedom Fighter 5%",
            reserved_percentage=Decimal("5.00"),
            priority=1,
        )
        assert quota.id is not None
        assert "Freedom Fighter" in str(quota)

        with pytest.raises(IntegrityError), transaction.atomic():
            QuotaRule.objects.create(
                institution=institution,
                circular=circular,
                quota_type=QuotaType.FREEDOM_FIGHTER,
                name="Duplicate Freedom Fighter",
            )


@pytest.mark.django_db
class TestAdmissionTestAndResultModel:
    def test_admission_test_and_result(
        self, institution: Institution, circular: AdmissionCircular
    ) -> None:
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00010",
            name_bn="হাসান মাহমুদ",
            name_en="Hasan Mahmud",
            dob=date(2014, 2, 14),
            gender=GenderChoices.MALE,
            birth_reg_no="20141234567890199",
            guardian_name="Mahmud Ali",
            guardian_phone="+8801711000002",
            present_address="Dhanmondi, Dhaka",
            permanent_address="Noakhali",
        )
        test = AdmissionTest.objects.create(
            institution=institution,
            circular=circular,
            title="Written Test",
            test_date=timezone.now(),
            venue="Hall 1",
            total_marks=Decimal("100.00"),
            pass_marks=Decimal("40.00"),
        )
        result = AdmissionTestResult.objects.create(
            institution=institution,
            test=test,
            application=app,
            marks_obtained=Decimal("78.50"),
            is_passed=True,
        )
        assert result.id is not None
        assert "78.50" in str(result)
