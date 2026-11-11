"""Model constraint and lifecycle tests for Student models."""

from datetime import date

import pytest
from django.db import IntegrityError

from apps.academics.models import ClassLevel, Section
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import (
    EnrollmentStatus,
    Gender,
    Student,
    StudentEnrollment,
)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা মডেল স্কুল",
        name_en="Dhaka Model School",
        eiin="134567",
    )


@pytest.fixture
def session(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def branch(institution) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name="Main Campus",
        code="MAIN",
    )


@pytest.fixture
def shift(branch) -> Shift:
    return Shift.objects.create(
        institution=branch.institution,
        branch=branch,
        name="morning",
        start_time="08:00",
        end_time="12:00",
    )


@pytest.fixture
def class_level(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 10",
        code="CLS10",
        order=10,
    )


@pytest.fixture
def section(class_level, session, shift) -> Section:
    return Section.objects.create(
        institution=class_level.institution,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )


@pytest.mark.django_db
class TestStudentModelConstraints:
    def test_unique_student_id_per_institution(self, institution):
        Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Rahim Uddin",
            name_bn="রহিম উদ্দিন",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )

        with pytest.raises(IntegrityError):
            Student.objects.create(
                institution=institution,
                student_id="2026100001",
                name_en="Karim Uddin",
                name_bn="করিম উদ্দিন",
                dob=date(2010, 2, 1),
                gender=Gender.MALE,
                admission_date=date(2026, 1, 1),
            )

    def test_unique_roll_per_section_session(self, institution, session, class_level, section):
        s1 = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Student 1",
            name_bn="ছাত্র ১",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        s2 = Student.objects.create(
            institution=institution,
            student_id="2026100002",
            name_en="Student 2",
            name_bn="ছাত্র ২",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )

        StudentEnrollment.objects.create(
            institution=institution,
            student=s1,
            session=session,
            class_level=class_level,
            section=section,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        # Same roll in same section & session must fail
        with pytest.raises(IntegrityError):
            StudentEnrollment.objects.create(
                institution=institution,
                student=s2,
                session=session,
                class_level=class_level,
                section=section,
                roll_no=1,
                enrollment_date=date(2026, 1, 1),
                status=EnrollmentStatus.ACTIVE,
            )

    def test_unique_active_enrollment_per_session(self, institution, session, class_level, section):
        s1 = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Student 1",
            name_bn="ছাত্র ১",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        StudentEnrollment.objects.create(
            institution=institution,
            student=s1,
            session=session,
            class_level=class_level,
            section=section,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        # Second active enrollment in same session for same student must fail
        sec_b = Section.objects.create(
            institution=institution,
            class_level=class_level,
            session=session,
            shift=section.shift,
            name="Section B",
        )
        with pytest.raises(IntegrityError):
            StudentEnrollment.objects.create(
                institution=institution,
                student=s1,
                session=session,
                class_level=class_level,
                section=sec_b,
                roll_no=1,
                enrollment_date=date(2026, 1, 1),
                status=EnrollmentStatus.ACTIVE,
            )

    def test_soft_delete_preserves_uniqueness(self, institution):
        s1 = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Student 1",
            name_bn="ছাত্র ১",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        s1.delete()
        assert s1.is_deleted is True

        # Now creating another with same ID is allowed because unique constraint filters condition=Q(is_deleted=False)
        s2 = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Student 1 New",
            name_bn="ছাত্র ১ নতুন",
            dob=date(2010, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        assert s2.id != s1.id
