"""Service layer tests for academic session lifecycle and settings validation."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.institutions.models import (
    AcademicSession,
    EducationBoard,
    Institution,
    InstitutionType,
    SessionStatus,
)
from apps.institutions.services import (
    activate_academic_session,
    close_academic_session,
    validate_institution_settings,
)


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Rajshahi Collegiate School",
        name_bn="রাজশাহী কলেজিয়েট স্কুল",
        eiin="100003",
        board=EducationBoard.RAJSHAHI,
        type=InstitutionType.SECONDARY,
        division="Rajshahi",
        district="Rajshahi",
        upazila="Boalia",
        phone="+8801722222222",
    )


@pytest.mark.django_db
class TestAcademicSessionServices:
    def test_activate_academic_session_switching(self, institution: Institution) -> None:
        session_2025 = AcademicSession.objects.create(
            institution=institution,
            name="2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        session_2026 = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=False,
            status=SessionStatus.PLANNED,
        )

        # Activate 2026
        activated = activate_academic_session(
            session_id=session_2026.id,
            institution_id=institution.id,
        )

        session_2025.refresh_from_db()
        session_2026.refresh_from_db()

        assert activated.id == session_2026.id
        assert session_2026.is_current is True
        assert session_2026.status == SessionStatus.ACTIVE
        assert session_2025.is_current is False

    def test_activate_closed_session_fails(self, institution: Institution) -> None:
        session_closed = AcademicSession.objects.create(
            institution=institution,
            name="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_current=False,
            status=SessionStatus.CLOSED,
        )

        with pytest.raises(ValidationError, match="Cannot activate a closed academic session"):
            activate_academic_session(
                session_id=session_closed.id,
                institution_id=institution.id,
            )

    def test_close_academic_session_without_confirm_fails(self, institution: Institution) -> None:
        session = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )

        with pytest.raises(ValidationError, match="confirm=True"):
            close_academic_session(
                session_id=session.id,
                institution_id=institution.id,
                confirm=False,
            )

    def test_close_academic_session_success(self, institution: Institution) -> None:
        session = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )

        closed = close_academic_session(
            session_id=session.id,
            institution_id=institution.id,
            confirm=True,
        )
        assert closed.status == SessionStatus.CLOSED
        assert closed.is_current is False


class TestSettingsValidation:
    def test_valid_settings(self) -> None:
        data = {
            "grading_profile_id": None,
            "attendance_defaults": {
                "late_tolerance_minutes": 10,
                "half_day_minimum_minutes": 150,
            },
            "sms_sender_id": "SCHOOL1",
            "fee_receipt_prefix": "REC2026-",
            "bangla_digits": False,
        }
        validated = validate_institution_settings(data)
        assert validated["sms_sender_id"] == "SCHOOL1"
        assert validated["bangla_digits"] is False

    def test_invalid_sms_sender_id_length(self) -> None:
        data = {"sms_sender_id": "TOOLONGSENDERNAME"}  # > 11 chars
        with pytest.raises(ValidationError, match="sms_sender_id"):
            validate_institution_settings(data)

    def test_invalid_attendance_tolerance(self) -> None:
        data = {"attendance_defaults": {"late_tolerance_minutes": 200}}  # > 120
        with pytest.raises(ValidationError, match="late_tolerance_minutes"):
            validate_institution_settings(data)
