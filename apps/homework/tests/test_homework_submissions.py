"""Tests for Homework publishing, submissions, late rules, upload security, signed URLs & notifications."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import User, UserType
from apps.communications.models import NotificationEvent
from apps.guardians.models import Guardian, StudentGuardian
from apps.homework.models import Homework, HomeworkStatus, SubmissionStatus
from apps.homework.services import (
    generate_signed_download_token,
    grade_submission,
    publish_homework,
    send_due_soon_reminders,
    submit_homework,
    verify_signed_download_token,
)
from apps.homework.services.storage_service import EICAR_TEST_SIGNATURE
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import Staff
from apps.students.models import EnrollmentStatus, Gender, Student, StudentEnrollment


@pytest.mark.django_db
class TestHomeworkSubmissionsAndSecurity:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Sylhet Govt Pilot School",
            name_bn="সিলেট সরকারি পাইলট স্কুল",
        )
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="MAIN", is_main=True
        )
        self.shift = Shift.objects.create(
            institution=self.inst,
            branch=self.branch,
            name="morning",
            start_time=time(8, 0),
            end_time=time(13, 0),
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.class_9 = ClassLevel.objects.create(
            institution=self.inst, name="Class 9", code="C09", order=9
        )
        self.sec_a = Section.objects.create(
            institution=self.inst,
            class_level=self.class_9,
            shift=self.shift,
            session=self.session,
            name="Padma",
        )
        self.subject = Subject.objects.create(
            institution=self.inst, code="109", name_en="Mathematics", name_bn="গণিত"
        )
        self.teacher = Staff.objects.create(
            institution=self.inst,
            employee_id="TCH-01",
            full_name_en="Salma Khatun",
            phone="+8801711000001",
            dob=date(1988, 1, 1),
            joining_date=date(2018, 1, 1),
        )
        self.student_user = User.objects.create_user(
            username="202609001",
            password="Password123!",
            institution=self.inst,
            phone="+8801711000002",
            user_type=UserType.STUDENT,
        )
        self.guardian_user = User.objects.create_user(
            username="guard_001",
            password="Password123!",
            institution=self.inst,
            phone="+8801711000003",
            user_type=UserType.GUARDIAN,
        )
        self.student = Student.objects.create(
            institution=self.inst,
            student_id="202609001",
            name_en="Nafis Ahmed",
            name_bn="নাফিস আহমেদ",
            dob=date(2011, 5, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 10),
        )
        StudentEnrollment.objects.create(
            institution=self.inst,
            student=self.student,
            session=self.session,
            class_level=self.class_9,
            section=self.sec_a,
            roll_no=1,
            enrollment_date=date(2026, 1, 10),
            status=EnrollmentStatus.ACTIVE,
        )
        guardian = Guardian.objects.create(
            institution=self.inst,
            user=self.guardian_user,
            name_en="Tariq Ahmed",
            phone="+8801711000003",
        )
        StudentGuardian.objects.create(
            institution=self.inst,
            student=self.student,
            guardian=guardian,
            is_primary=True,
        )

    def test_publish_and_due_soon_notifications_trigger(self) -> None:
        now = timezone.now()
        hw = Homework.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_9,
            section=self.sec_a,
            subject=self.subject,
            teacher=self.teacher,
            title="Algebra Exercise 3.1",
            due_at=now + timedelta(hours=12),
            max_marks=Decimal("20.00"),
        )
        publish_homework(hw)
        hw.refresh_from_db()
        assert hw.status == HomeworkStatus.PUBLISHED
        assert NotificationEvent.objects.filter(
            institution=self.inst, event_type="homework_assigned", reference_id=hw.id
        ).exists()

        # Due-soon reminder runs once and stays idempotent
        assert send_due_soon_reminders(institution=self.inst, hours_ahead=24) == 1
        assert send_due_soon_reminders(institution=self.inst, hours_ahead=24) == 0
        assert NotificationEvent.objects.filter(
            institution=self.inst, event_type="homework_due_soon", reference_id=hw.id
        ).exists()

    def test_submission_due_date_late_cutoff_and_grading(self, settings, tmp_path) -> None:
        settings.MEDIA_ROOT = tmp_path
        now = timezone.now()
        hw = Homework.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_9,
            section=self.sec_a,
            subject=self.subject,
            teacher=self.teacher,
            title="Geometry Proofs",
            due_at=now - timedelta(hours=2),
            allow_late_submission=True,
            late_submission_cutoff_at=now + timedelta(hours=6),
            max_marks=Decimal("10.00"),
            status=HomeworkStatus.PUBLISHED,
        )

        clean_pdf = SimpleUploadedFile(
            "solution.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", content_type="application/pdf"
        )
        sub = submit_homework(
            homework=hw,
            student=self.student,
            text_response="Completed problems 1-5.",
            files=[clean_pdf],
            uploaded_by=self.student_user,
            now=now,
        )
        assert sub.is_late is True
        assert sub.status == SubmissionStatus.LATE
        assert sub.attachments.count() == 1

        # Grade submission & notify
        graded = grade_submission(
            submission=sub,
            marks_obtained=Decimal("8.50"),
            feedback="Good work, check Q4.",
        )
        assert graded.status == SubmissionStatus.GRADED
        assert graded.marks_obtained == Decimal("8.50")

        # Cannot modify after graded
        with pytest.raises(ValidationError):
            submit_homework(homework=hw, student=self.student, text_response="Edit", now=now)

        # Past cutoff rejected
        hw_strict = Homework.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_9,
            subject=self.subject,
            title="Strict Deadline",
            due_at=now - timedelta(minutes=10),
            allow_late_submission=False,
            status=HomeworkStatus.PUBLISHED,
        )
        with pytest.raises(ValidationError):
            submit_homework(homework=hw_strict, student=self.student, text_response="Late", now=now)

    def test_upload_validation_av_scan_and_signed_tokens(self, settings, tmp_path) -> None:
        settings.MEDIA_ROOT = tmp_path
        settings.HOMEWORK_MAX_FILE_SIZE_MB = 1
        now = timezone.now()
        hw = Homework.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_9,
            subject=self.subject,
            title="Science Lab",
            due_at=now + timedelta(days=2),
            status=HomeworkStatus.PUBLISHED,
        )

        # Disallowed file extension rejected
        bad_exe = SimpleUploadedFile(
            "payload.exe", b"MZ...", content_type="application/octet-stream"
        )
        with pytest.raises(ValidationError, match="Unsupported file type"):
            submit_homework(homework=hw, student=self.student, files=[bad_exe], now=now)

        # Oversized file rejected (> 1 MB)
        oversized = SimpleUploadedFile(
            "huge.pdf", b"0" * (1024 * 1024 + 10), content_type="application/pdf"
        )
        with pytest.raises(ValidationError, match="maximum allowed size"):
            submit_homework(homework=hw, student=self.student, files=[oversized], now=now)

        # EICAR malware signature rejected by AV hook
        eicar = SimpleUploadedFile("eicar.txt", EICAR_TEST_SIGNATURE, content_type="text/plain")
        with pytest.raises(ValidationError, match="antivirus"):
            submit_homework(homework=hw, student=self.student, files=[eicar], now=now)

        # Signed download token roundtrip and tamper rejection
        tok = generate_signed_download_token("homework", "att-123", str(self.inst.id))
        parsed = verify_signed_download_token(tok, max_age=60)
        assert parsed["kind"] == "homework"
        assert parsed["id"] == "att-123"
        with pytest.raises(ValidationError):
            verify_signed_download_token(tok + "tamper", max_age=60)
