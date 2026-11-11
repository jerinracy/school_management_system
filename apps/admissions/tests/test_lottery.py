"""Unit tests for deterministic lottery draw engine."""

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
from apps.admissions.services.lottery import conduct_lottery_draw
from apps.institutions.models import AcademicSession, Institution


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(name_bn="লটারি স্কুল", name_en="Lottery School", eiin="554433")


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
    return ClassLevel.objects.create(institution=institution, name="Class 1", code="c01", order=1)


@pytest.fixture
def circular(
    institution: Institution, session: AcademicSession, class_level: ClassLevel
) -> AdmissionCircular:
    return AdmissionCircular.objects.create(
        institution=institution,
        session=session,
        class_level=class_level,
        title="Class 1 Lottery 2026",
        seats_available=5,
        application_fee=Decimal("100.00"),
        form_open_date=date(2025, 1, 1),
        form_close_date=date(2027, 12, 31),
        status=CircularStatus.PUBLISHED,
    )


@pytest.fixture
def paid_applications(institution: Institution, circular: AdmissionCircular) -> list[Application]:
    apps: list[Application] = []
    for i in range(1, 11):
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no=f"ADM-2026-{i:05d}",
            name_bn=f"শিক্ষার্থী {i}",
            name_en=f"Candidate {i}",
            dob=date(2019, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no=f"201900000000{i:05d}",
            guardian_name="Guardian",
            guardian_phone=f"+880171100{i:04d}",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.PAID,
        )
        apps.append(app)
    return apps


@pytest.mark.django_db
class TestLotteryDrawService:
    def test_lottery_reproducibility_with_same_seed(
        self, circular: AdmissionCircular, paid_applications: list[Application]
    ) -> None:
        seed = 424242

        draw1 = conduct_lottery_draw(
            circular_id=circular.id,
            total_to_select=5,
            seed=seed,
        )
        draw2 = conduct_lottery_draw(
            circular_id=circular.id,
            total_to_select=5,
            seed=seed,
        )

        assert draw1.total_candidates == 10
        assert draw1.selected_candidates_count == 5
        # Exact same seed MUST yield exact same drawn order
        assert draw1.drawn_order == draw2.drawn_order

    def test_lottery_different_seed_yields_different_order(
        self, circular: AdmissionCircular, paid_applications: list[Application]
    ) -> None:
        draw1 = conduct_lottery_draw(circular_id=circular.id, total_to_select=5, seed=11111)
        draw2 = conduct_lottery_draw(circular_id=circular.id, total_to_select=5, seed=99999)

        assert draw1.drawn_order != draw2.drawn_order

    def test_lottery_fails_with_no_candidates(self, circular: AdmissionCircular) -> None:
        # No applications created yet
        with pytest.raises(ValidationError):
            conduct_lottery_draw(circular_id=circular.id, total_to_select=5)
