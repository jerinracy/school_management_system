"""Unit tests for routine timetable conflict detection service."""

from datetime import date, time

import pytest

from apps.academics.models import ClassLevel, Period, Room, RoutineSlot, Section, Subject, Weekday
from apps.academics.services.conflicts import (
    validate_routine_slot_conflicts,
    validate_routine_slots_batch,
)
from apps.accounts.models import User
from apps.institutions.models import AcademicSession, Branch, Institution, Shift


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা হাই স্কুল",
        name_en="Dhaka High School",
        eiin="134567",
        weekend_days=["friday", "saturday"],
    )


@pytest.fixture
def branch(institution: Institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Branch", code="MAIN")


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
def shift(institution: Institution, branch: Branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="morning",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )


@pytest.fixture
def teacher(institution: Institution) -> User:
    return User.objects.create_user(
        username="farhana_teacher",
        phone="+8801712000001",
        full_name="Farhana Akter",
        institution=institution,
        user_type="teacher",
    )


@pytest.mark.django_db
class TestConflictService:
    def test_detects_period_is_break(
        self, institution: Institution, shift: Shift, session: AcademicSession
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        tiffin_break = Period.objects.create(
            institution=institution,
            shift=shift,
            name="Tiffin Break",
            start_time=time(10, 30),
            end_time=time(11, 0),
            order=4,
            is_break=True,
        )
        report = validate_routine_slot_conflicts(
            institution_id=institution.id,
            section_id=sec.id,
            weekday=Weekday.SUNDAY,
            period_id=tiffin_break.id,
        )
        assert not report.is_valid
        assert any(c.code == "PERIOD_IS_BREAK" for c in report.conflicts)

    def test_detects_weekend_warning(
        self, institution: Institution, shift: Shift, session: AcademicSession
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        report = validate_routine_slot_conflicts(
            institution_id=institution.id,
            section_id=sec.id,
            weekday=Weekday.FRIDAY,  # Friday is institutional weekend
            period_id=period.id,
        )
        assert report.is_valid
        assert len(report.warnings) > 0
        assert "weekend" in report.warnings[0].lower()

    def test_detects_teacher_and_room_conflicts(
        self,
        institution: Institution,
        shift: Shift,
        session: AcademicSession,
        teacher: User,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 7", code="c07", order=7
        )
        sec_a = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        sec_b = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="B"
        )
        sub = Subject.objects.create(
            institution=institution, code="101", name_en="Bangla", name_bn="বাংলা"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        room = Room.objects.create(institution=institution, name="101", capacity=50)

        # Existing slot: Teacher in Room 101 with Section A
        RoutineSlot.objects.create(
            institution=institution,
            section=sec_a,
            weekday=Weekday.MONDAY,
            period=period,
            subject=sub,
            teacher_user=teacher,
            room=room,
        )

        # Propose Section B with same teacher and same room in same period
        report = validate_routine_slot_conflicts(
            institution_id=institution.id,
            section_id=sec_b.id,
            weekday=Weekday.MONDAY,
            period_id=period.id,
            teacher_user_id=teacher.id,
            room_id=room.id,
        )
        assert not report.is_valid
        codes = [c.code for c in report.conflicts]
        assert "TEACHER_DOUBLE_BOOKED" in codes
        assert "ROOM_CLASH" in codes

    def test_batch_validation_detects_internal_clashes(
        self,
        institution: Institution,
        shift: Shift,
        session: AcademicSession,
        teacher: User,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8
        )
        sec_a = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        sec_b = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="B"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        batch = [
            {
                "section_id": str(sec_a.id),
                "weekday": Weekday.TUESDAY,
                "period_id": str(period.id),
                "teacher_user_id": str(teacher.id),
            },
            {
                "section_id": str(sec_b.id),
                "weekday": Weekday.TUESDAY,
                "period_id": str(period.id),
                "teacher_user_id": str(teacher.id),
            },
        ]
        results = validate_routine_slots_batch(institution_id=institution.id, slots=batch)
        assert len(results) == 2
        assert results[0]["report"]["is_valid"] is True
        assert results[1]["report"]["is_valid"] is False
        assert any(c["code"] == "BATCH_TEACHER_CLASH" for c in results[1]["report"]["conflicts"])
