"""Service tests for Student intake, roll assignment, promotion, and certificates."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel, Section
from apps.admissions.models import AdmissionCircular, Application, ApplicationStatus
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import (
    EnrollmentStatus,
    PromotionAction,
    PromotionBatchStatus,
    Student,
    StudentEnrollment,
    StudentStatus,
)
from apps.students.services import (
    admit_from_application,
    apply_promotion,
    auto_assign_section_rolls,
    issue_or_renew_id_card,
    issue_transfer_certificate,
    preview_promotion,
    rollback_promotion,
)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা মডেল স্কুল",
        name_en="Dhaka Model School",
        eiin="134567",
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
def session_2026(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def session_2027(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2027",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        is_current=False,
    )


@pytest.fixture
def class_nine(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 9",
        code="CLS9",
        order=9,
    )


@pytest.fixture
def class_ten(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 10",
        code="CLS10",
        order=10,
    )


@pytest.fixture
def section_9a(class_nine, session_2026, shift) -> Section:
    return Section.objects.create(
        institution=class_nine.institution,
        class_level=class_nine,
        session=session_2026,
        shift=shift,
        name="Section 9A",
    )


@pytest.fixture
def section_10a(class_ten, session_2027, shift) -> Section:
    return Section.objects.create(
        institution=class_ten.institution,
        class_level=class_ten,
        session=session_2027,
        shift=shift,
        name="Section 10A",
    )


@pytest.fixture
def admitted_application(institution, session_2026, class_nine) -> Application:
    circular = AdmissionCircular.objects.create(
        institution=institution,
        session=session_2026,
        class_level=class_nine,
        title="Class 9 Admission 2026",
        application_fee=Decimal("0.00"),
        seats_available=50,
        form_open_date=date(2026, 1, 1),
        form_close_date=date(2026, 1, 31),
    )
    return Application.objects.create(
        institution=institution,
        circular=circular,
        application_no="ADM-2026-00001",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        dob=date(2010, 5, 20),
        gender="male",
        birth_reg_no="20101234567890123",
        guardian_name="Kabir Ahmed",
        guardian_phone="+8801711223344",
        status=ApplicationStatus.ADMITTED,
    )


@pytest.mark.django_db
class TestStudentServices:
    def test_admit_from_application(self, admitted_application, section_9a):
        student, enrollment = admit_from_application(
            application_id=admitted_application.id,
            section_id=section_9a.id,
            roll_no=1,
        )

        assert student.student_id == "2026090001"
        assert student.name_en == "Tanvir Ahmed"
        assert student.name_bn == "তানভীর আহমেদ"
        assert student.status == StudentStatus.ACTIVE
        assert student.application_id == admitted_application.id

        assert enrollment.section == section_9a
        assert enrollment.roll_no == 1
        assert enrollment.status == EnrollmentStatus.ACTIVE

        # Duplicate conversion fails
        with pytest.raises(ValidationError):
            admit_from_application(
                application_id=admitted_application.id,
                section_id=section_9a.id,
                roll_no=2,
            )

    def test_auto_assign_section_rolls(self, institution, session_2026, class_nine, section_9a):
        # Create students in non-alphabetical order
        names = [
            ("Zahid Hasan", "জাহিদ হাসান"),
            ("Anisur Rahman", "আনিসুর রহমান"),
            ("Kamal Hossain", "কামাল হোসেন"),
        ]
        for idx, (en, bn) in enumerate(names, start=1):
            s = Student.objects.create(
                institution=institution,
                student_id=f"20260900{idx:02d}",
                name_en=en,
                name_bn=bn,
                dob=date(2010, 1, 1),
                gender="male",
                admission_date=date(2026, 1, 1),
            )
            StudentEnrollment.objects.create(
                institution=institution,
                student=s,
                session=session_2026,
                class_level=class_nine,
                section=section_9a,
                roll_no=100 + idx,  # unordered
                enrollment_date=date(2026, 1, 1),
                status=EnrollmentStatus.ACTIVE,
            )

        # Auto assign by English name
        enrollments = auto_assign_section_rolls(
            section_id=section_9a.id,
            session_id=session_2026.id,
            strategy="name_en",
        )

        assert len(enrollments) == 3
        # Anisur -> Roll 1, Kamal -> Roll 2, Zahid -> Roll 3
        assert enrollments[0].student.name_en == "Anisur Rahman"
        assert enrollments[0].roll_no == 1
        assert enrollments[1].student.name_en == "Kamal Hossain"
        assert enrollments[1].roll_no == 2
        assert enrollments[2].student.name_en == "Zahid Hasan"
        assert enrollments[2].roll_no == 3

    def test_promotion_preview_apply_rollback_lifecycle(
        self,
        institution,
        session_2026,
        session_2027,
        class_nine,
        class_ten,
        section_9a,
        section_10a,
    ):
        # Create 2 students in class 9
        s1 = Student.objects.create(
            institution=institution,
            student_id="2026090001",
            name_en="Good Student",
            name_bn="ভালো ছাত্র",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        s2 = Student.objects.create(
            institution=institution,
            student_id="2026090002",
            name_en="Failing Student",
            name_bn="অনুত্তীর্ণ ছাত্র",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        e1 = StudentEnrollment.objects.create(
            institution=institution,
            student=s1,
            session=session_2026,
            class_level=class_nine,
            section=section_9a,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )
        e2 = StudentEnrollment.objects.create(
            institution=institution,
            student=s2,
            session=session_2026,
            class_level=class_nine,
            section=section_9a,
            roll_no=2,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        # 1. Preview
        overrides = [
            {"student_id": str(s1.id), "gpa": "4.50", "action": PromotionAction.PROMOTE},
            {"student_id": str(s2.id), "gpa": "1.50", "action": PromotionAction.REPEAT},
        ]
        batch = preview_promotion(
            institution_id=institution.id,
            from_session_id=session_2026.id,
            to_session_id=session_2027.id,
            from_class_id=class_nine.id,
            to_class_id=class_ten.id,
            default_target_section_id=section_10a.id,
            student_overrides=overrides,
        )

        assert batch.status == PromotionBatchStatus.PREVIEWED
        assert batch.total_students == 2
        assert batch.promoted_count == 1
        assert batch.retained_count == 1

        # 2. Apply
        applied_batch = apply_promotion(batch.id)
        assert applied_batch.status == PromotionBatchStatus.APPLIED

        e1.refresh_from_db()
        e2.refresh_from_db()
        assert e1.status == EnrollmentStatus.PROMOTED
        assert e2.status == EnrollmentStatus.REPEATED

        # Check new active enrollments in session 2027
        new_e1 = StudentEnrollment.objects.get(student=s1, session=session_2027)
        assert new_e1.class_level == class_ten
        assert new_e1.section == section_10a
        assert new_e1.status == EnrollmentStatus.ACTIVE

        new_e2 = StudentEnrollment.objects.get(student=s2, session=session_2027)
        assert new_e2.class_level == class_nine  # repeated in class 9
        assert new_e2.status == EnrollmentStatus.ACTIVE

        # 3. Rollback
        rolled_back = rollback_promotion(batch.id)
        assert rolled_back.status == PromotionBatchStatus.ROLLED_BACK

        e1.refresh_from_db()
        e2.refresh_from_db()
        assert e1.status == EnrollmentStatus.ACTIVE
        assert e2.status == EnrollmentStatus.ACTIVE
        assert not StudentEnrollment.objects.filter(session=session_2027).exists()

    def test_issue_transfer_certificate(self, institution, session_2026, class_nine, section_9a):
        student = Student.objects.create(
            institution=institution,
            student_id="2026090001",
            name_en="Moving Student",
            name_bn="বদলি শিক্ষার্থী",
            dob=date(2010, 1, 1),
            gender="female",
            admission_date=date(2026, 1, 1),
        )
        enrollment = StudentEnrollment.objects.create(
            institution=institution,
            student=student,
            session=session_2026,
            class_level=class_nine,
            section=section_9a,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        tc = issue_transfer_certificate(
            student_id=student.id,
            reason="Family relocation to Chittagong",
            conduct_remarks="Exemplary",
            dues_cleared=True,
        )

        student.refresh_from_db()
        enrollment.refresh_from_db()

        assert tc.tc_number.startswith("TC-2026-")
        assert tc.pdf_file is not None
        assert student.status == StudentStatus.TRANSFERRED
        assert enrollment.status == EnrollmentStatus.TRANSFERRED

    def test_issue_or_renew_id_card(self, institution, session_2026, class_nine, section_9a):
        student = Student.objects.create(
            institution=institution,
            student_id="2026090001",
            name_en="ID Card Student",
            name_bn="আইডি কার্ড শিক্ষার্থী",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        StudentEnrollment.objects.create(
            institution=institution,
            student=student,
            session=session_2026,
            class_level=class_nine,
            section=section_9a,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        card1, pdf1 = issue_or_renew_id_card(student_id=student.id)
        assert card1.is_active is True
        assert card1.card_no.startswith("IDC-2026-")
        assert len(pdf1) > 500

        # Issuing replacement deactivates previous card
        card2, pdf2 = issue_or_renew_id_card(student_id=student.id)
        card1.refresh_from_db()
        assert card1.is_active is False
        assert card2.is_active is True
        assert card2.card_no != card1.card_no
