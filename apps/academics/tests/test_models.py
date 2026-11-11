"""Unit tests for academics models and constraints."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Group,
    MediumType,
    Period,
    Room,
    RoutineSlot,
    Section,
    Subject,
    SubjectType,
    SubstituteAssignment,
    Weekday,
)
from apps.accounts.models import User
from apps.institutions.models import AcademicSession, Branch, Institution, Shift


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা মডেল স্কুল",
        name_en="Dhaka Model School",
        eiin="134567",
        weekend_days=["friday", "saturday"],
    )


@pytest.fixture
def other_institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="চিটাগাং স্কুল",
        name_en="Chittagong School",
        eiin="234567",
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
def branch(institution: Institution) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name="Main Campus",
        code="MAIN",
    )


@pytest.fixture
def shift(institution: Institution, branch: Branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="morning",
        start_time=time(7, 30),
        end_time=time(12, 0),
    )


@pytest.fixture
def teacher_user(institution: Institution) -> User:
    return User.objects.create_user(
        username="abdur_teacher",
        phone="+8801711000001",
        full_name="Abdur Rahim",
        institution=institution,
        user_type="teacher",
    )


@pytest.mark.django_db
class TestClassLevelModel:
    def test_create_class_level(self, institution: Institution) -> None:
        cls = ClassLevel.objects.create(
            institution=institution,
            name="Class 9",
            code="c09",
            order=9,
            medium=MediumType.BANGLA,
            has_groups=True,
        )
        assert cls.id is not None
        assert str(cls) == "Class 9 (Bangla Medium)"

    def test_duplicate_code_per_institution_raises_integrity_error(
        self, institution: Institution
    ) -> None:
        ClassLevel.objects.create(
            institution=institution,
            name="Class 9",
            code="c09",
            order=9,
            medium=MediumType.BANGLA,
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            ClassLevel.objects.create(
                institution=institution,
                name="Class 9 Version 2",
                code="c09",
                order=10,
                medium=MediumType.BANGLA,
            )

    def test_duplicate_order_same_medium_raises_integrity_error(
        self, institution: Institution
    ) -> None:
        ClassLevel.objects.create(
            institution=institution,
            name="Class 9 Bangla",
            code="c09b",
            order=9,
            medium=MediumType.BANGLA,
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            ClassLevel.objects.create(
                institution=institution,
                name="Class 9 Bangla Dup",
                code="c09b2",
                order=9,
                medium=MediumType.BANGLA,
            )


@pytest.mark.django_db
class TestSectionModel:
    def test_create_section_and_unique_constraint(
        self, institution: Institution, shift: Shift, session: AcademicSession
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution,
            name="Class 6",
            code="c06",
            order=6,
            medium=MediumType.BANGLA,
        )
        sec1 = Section.objects.create(
            institution=institution,
            class_level=cls,
            shift=shift,
            session=session,
            name="Padma",
            capacity=45,
        )
        assert str(sec1) == "Class 6 - Padma (2026)"

        with pytest.raises(IntegrityError), transaction.atomic():
            Section.objects.create(
                institution=institution,
                class_level=cls,
                shift=shift,
                session=session,
                name="Padma",
            )


@pytest.mark.django_db
class TestSubjectAndClassSubjectModel:
    def test_subject_and_class_offering(
        self, institution: Institution, session: AcademicSession
    ) -> None:
        sub = Subject.objects.create(
            institution=institution,
            code="101",
            name_en="Bangla 1st Paper",
            name_bn="বাংলা ১ম পত্র",
            type=SubjectType.COMPULSORY,
            has_papers=True,
            paper_number=1,
            marks_components_config={
                "creative": {"full": 70, "pass": 23},
                "mcq": {"full": 30, "pass": 10},
            },
        )
        cls = ClassLevel.objects.create(
            institution=institution,
            name="Class 10",
            code="c10",
            order=10,
            has_groups=True,
        )
        grp = Group.objects.create(
            institution=institution,
            name="Science",
            code="SCI",
        )
        class_sub = ClassSubject.objects.create(
            institution=institution,
            class_level=cls,
            group=grp,
            session=session,
            subject=sub,
            full_marks=Decimal("100.00"),
            pass_rule={"aggregate_pass": 33},
        )
        assert class_sub.id is not None
        assert "Class 10 [Science] - Bangla 1st Paper (2026)" in str(class_sub)


@pytest.mark.django_db
class TestRoutineSlotModel:
    def test_routine_slot_and_double_booking_constraints(
        self,
        institution: Institution,
        shift: Shift,
        session: AcademicSession,
        teacher_user: User,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 7", code="c07", order=7
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        sub = Subject.objects.create(
            institution=institution, code="107", name_en="English", name_bn="ইংরেজি"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        room = Room.objects.create(institution=institution, name="Room 101", capacity=50)

        slot1 = RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            weekday=Weekday.SUNDAY,
            period=period,
            subject=sub,
            teacher_user=teacher_user,
            room=room,
        )
        assert slot1.id is not None

        # Double book section in same slot
        with pytest.raises(IntegrityError), transaction.atomic():
            RoutineSlot.objects.create(
                institution=institution,
                section=sec,
                weekday=Weekday.SUNDAY,
                period=period,
                subject=sub,
            )

        # Double book teacher in another section in same period
        sec2 = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="B"
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            RoutineSlot.objects.create(
                institution=institution,
                section=sec2,
                weekday=Weekday.SUNDAY,
                period=period,
                subject=sub,
                teacher_user=teacher_user,
            )


@pytest.mark.django_db
class TestSubstituteAssignmentModel:
    def test_substitute_assignment(
        self,
        institution: Institution,
        shift: Shift,
        session: AcademicSession,
        teacher_user: User,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="Rose"
        )
        sub = Subject.objects.create(
            institution=institution, code="109", name_en="Math", name_bn="গণিত"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="2nd Period",
            start_time=time(8, 50),
            end_time=time(9, 35),
            order=2,
        )
        slot = RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            weekday=Weekday.MONDAY,
            period=period,
            subject=sub,
            teacher_user=teacher_user,
        )
        substitute_user = User.objects.create_user(
            username="kabir_teacher",
            phone="+8801711000002",
            full_name="Kabir Hossain",
            institution=institution,
            user_type="teacher",
        )
        sub_assign = SubstituteAssignment.objects.create(
            institution=institution,
            routine_slot=slot,
            slot_date=date(2026, 3, 2),
            original_teacher=teacher_user,
            substitute_teacher=substitute_user,
            reason="Medical emergency",
        )
        assert sub_assign.id is not None
        assert "Kabir Hossain" in str(sub_assign)

        # Cannot substitute with original teacher
        invalid_sub = SubstituteAssignment(
            institution=institution,
            routine_slot=slot,
            slot_date=date(2026, 3, 3),
            original_teacher=teacher_user,
            substitute_teacher=teacher_user,
        )
        with pytest.raises(ValidationError):
            invalid_sub.clean()
