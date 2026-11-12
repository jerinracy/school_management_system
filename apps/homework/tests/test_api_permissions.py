"""API permission matrix, section scoping, quiz answer hiding & tenant isolation tests."""

from datetime import date, time, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import Role, User, UserRole, UserType
from apps.guardians.models import Guardian, StudentGuardian
from apps.homework.models import (
    Homework,
    HomeworkAttachment,
    HomeworkStatus,
    HomeworkSubmission,
    Quiz,
    QuizOption,
    QuizQuestion,
    SubmissionAttachment,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import EnrollmentStatus, Gender, Student, StudentEnrollment


def _grant_homework_perms(user: User, codenames: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(Homework)
    role = Role.objects.create(
        institution=user.institution,
        name=f"Role-{user.username}",
        code=f"role_{user.username}",
    )
    for code in codenames:
        short = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short, content_type=ct, defaults={"name": code}
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestHomeworkAPIPermissionsAndIsolation:
    def setup_method(self) -> None:
        self.inst_a = Institution.objects.create(name_en="School A", name_bn="স্কুল ক")
        self.inst_b = Institution.objects.create(name_en="School B", name_bn="স্কুল খ")

        branch_a = Branch.objects.create(
            institution=self.inst_a, name="Main", code="M", is_main=True
        )
        shift_a = Shift.objects.create(
            institution=self.inst_a,
            branch=branch_a,
            name="morning",
            start_time=time(8, 0),
            end_time=time(13, 0),
        )
        self.session_a = AcademicSession.objects.create(
            institution=self.inst_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.class_9 = ClassLevel.objects.create(
            institution=self.inst_a, name="Class 9", code="C09", order=9
        )
        self.sec_a = Section.objects.create(
            institution=self.inst_a,
            class_level=self.class_9,
            shift=shift_a,
            session=self.session_a,
            name="Padma",
        )
        self.sec_b = Section.objects.create(
            institution=self.inst_a,
            class_level=self.class_9,
            shift=shift_a,
            session=self.session_a,
            name="Meghna",
        )
        self.subj = Subject.objects.create(
            institution=self.inst_a, code="101", name_en="Bangla", name_bn="বাংলা"
        )

        self.teacher = User.objects.create_user(
            username="teacher_a",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801733333301",
            user_type=UserType.TEACHER,
        )
        _grant_homework_perms(self.teacher, ["homework.view", "homework.manage"])

        self.accountant = User.objects.create_user(
            username="acct_a",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801733333302",
            user_type=UserType.ACCOUNTANT,
        )
        self.student_user_1 = User.objects.create_user(
            username="STU-A1",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801733333303",
            user_type=UserType.STUDENT,
        )
        self.student_user_2 = User.objects.create_user(
            username="STU-A2",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801733333304",
            user_type=UserType.STUDENT,
        )
        self.guardian_user = User.objects.create_user(
            username="GUARD-A1",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801733333305",
            user_type=UserType.GUARDIAN,
        )
        self.mgr_b = User.objects.create_user(
            username="mgr_b",
            password="Password123!",
            institution=self.inst_b,
            phone="+8801733333399",
            user_type=UserType.TEACHER,
        )
        _grant_homework_perms(self.mgr_b, ["homework.view", "homework.manage"])

        self.stu1 = Student.objects.create(
            institution=self.inst_a,
            student_id="STU-A1",
            name_en="Student One",
            name_bn="শিক্ষার্থী ১",
            dob=date(2011, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        self.stu2 = Student.objects.create(
            institution=self.inst_a,
            student_id="STU-A2",
            name_en="Student Two",
            name_bn="শিক্ষার্থী ২",
            dob=date(2011, 2, 1),
            gender=Gender.FEMALE,
            admission_date=date(2026, 1, 1),
        )
        StudentEnrollment.objects.create(
            institution=self.inst_a,
            student=self.stu1,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_a,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )
        StudentEnrollment.objects.create(
            institution=self.inst_a,
            student=self.stu2,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_b,
            roll_no=2,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )
        guardian = Guardian.objects.create(
            institution=self.inst_a,
            user=self.guardian_user,
            name_en="Guardian One",
            phone="+8801733333305",
        )
        StudentGuardian.objects.create(
            institution=self.inst_a, student=self.stu1, guardian=guardian, is_primary=True
        )

        now = timezone.now()
        self.hw_pub_padma = Homework.objects.create(
            institution=self.inst_a,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_a,
            subject=self.subj,
            title="Padma Published HW",
            due_at=now + timedelta(days=2),
            status=HomeworkStatus.PUBLISHED,
        )
        self.hw_pub_meghna = Homework.objects.create(
            institution=self.inst_a,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_b,
            subject=self.subj,
            title="Meghna Published HW",
            due_at=now + timedelta(days=2),
            status=HomeworkStatus.PUBLISHED,
        )
        self.hw_draft = Homework.objects.create(
            institution=self.inst_a,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_a,
            subject=self.subj,
            title="Padma Draft HW",
            due_at=now + timedelta(days=3),
            status=HomeworkStatus.DRAFT,
        )

    def test_role_visibility_quiz_answer_hiding_and_signed_download(
        self, settings, tmp_path
    ) -> None:
        settings.MEDIA_ROOT = tmp_path
        client = APIClient()

        # 1. Unauthenticated -> 401; Unauthorized staff without homework role -> 403
        assert (
            client.get(reverse("v1_homework:assignment-list")).status_code
            == status.HTTP_401_UNAUTHORIZED
        )
        client.force_authenticate(user=self.accountant)
        assert (
            client.get(reverse("v1_homework:assignment-list")).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # 2. Student 1 (Padma) sees ONLY Padma published HW (not Draft, not Meghna)
        client.force_authenticate(user=self.student_user_1)
        list_resp = client.get(reverse("v1_homework:assignment-list"))
        assert list_resp.status_code == status.HTTP_200_OK
        titles = [item["title"] for item in list_resp.data["results"]]
        assert titles == ["Padma Published HW"]

        # Student cannot create or publish homework
        assert (
            client.post(
                reverse("v1_homework:assignment-publish", kwargs={"pk": self.hw_pub_padma.id})
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # Student 1 submits file attachment and gets signed download URL
        pdf_file = SimpleUploadedFile(
            "my_work.pdf", b"%PDF-1.4\nhello", content_type="application/pdf"
        )
        sub_resp = client.post(
            reverse("v1_homework:assignment-submit", kwargs={"pk": self.hw_pub_padma.id}),
            {"text_response": "Done!", "files": pdf_file},
            format="multipart",
        )
        assert sub_resp.status_code == status.HTTP_200_OK
        signed_url = sub_resp.data["attachments"][0]["download_url"]
        assert "/api/v1/homework/download/?token=" in signed_url

        # Guardian of Student 1 can read ward's homework & download ward's submission, but CANNOT submit
        client.force_authenticate(user=self.guardian_user)
        g_list = client.get(reverse("v1_homework:assignment-list"))
        assert [i["title"] for i in g_list.data["results"]] == ["Padma Published HW"]
        assert (
            client.post(
                reverse("v1_homework:assignment-submit", kwargs={"pk": self.hw_pub_padma.id}),
                {"text_response": "Parent submit"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # Student 2 (Meghna) CANNOT download Student 1's submission attachment even with signed URL
        client.force_authenticate(user=self.student_user_2)
        tok = signed_url.split("token=")[1]
        dl_denied = client.get(reverse("v1_homework:signed-download"), {"token": tok})
        assert dl_denied.status_code == status.HTTP_403_FORBIDDEN

        # Teacher CAN download it and see Content-Disposition attachment
        client.force_authenticate(user=self.teacher)
        dl_ok = client.get(reverse("v1_homework:signed-download"), {"token": tok})
        assert dl_ok.status_code == status.HTTP_200_OK
        assert "attachment" in dl_ok["Content-Disposition"]

        # 3. Quiz hides `is_correct` from students
        now = timezone.now()
        quiz = Quiz.objects.create(
            institution=self.inst_a,
            session=self.session_a,
            class_level=self.class_9,
            section=self.sec_a,
            subject=self.subj,
            title="MCQ Test",
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
            is_published=True,
        )
        q = QuizQuestion.objects.create(institution=self.inst_a, quiz=quiz, question_text="2+2=?")
        QuizOption.objects.create(
            institution=self.inst_a, question=q, option_text="4", is_correct=True
        )

        client.force_authenticate(user=self.student_user_1)
        q_resp = client.get(reverse("v1_homework:quiz-detail", kwargs={"pk": quiz.id}))
        assert q_resp.status_code == status.HTTP_200_OK
        assert "is_correct" not in q_resp.data["questions"][0]["options"][0]

        # 4. Cross-tenant isolation: Tenant B manager sees 0 assignments & gets 400 injecting Tenant A FKs
        client.force_authenticate(user=self.mgr_b)
        assert client.get(reverse("v1_homework:assignment-list")).data["count"] == 0
        cross = client.post(
            reverse("v1_homework:assignment-list"),
            {
                "session": str(self.session_a.id),
                "class_level": str(self.class_9.id),
                "subject": str(self.subj.id),
                "title": "Cross Tenant",
                "due_at": (now + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        assert cross.status_code == status.HTTP_400_BAD_REQUEST

        # Clean unused model references verify
        assert HomeworkAttachment.objects.count() == 0
        assert HomeworkSubmission.objects.count() == 1
        assert SubmissionAttachment.objects.count() == 1

    def test_quiz_material_and_syllabus_api_flows(self, settings, tmp_path) -> None:
        settings.MEDIA_ROOT = tmp_path
        now = timezone.now()
        client = APIClient()

        # Teacher creates Quiz, Question, Options, SyllabusTopic, and StudyMaterial
        client.force_authenticate(user=self.teacher)
        q_resp = client.post(
            reverse("v1_homework:quiz-list"),
            {
                "session": str(self.session_a.id),
                "class_level": str(self.class_9.id),
                "section": str(self.sec_a.id),
                "subject": str(self.subj.id),
                "title": "Bangla Quiz 1",
                "starts_at": (now - timedelta(minutes=10)).isoformat(),
                "ends_at": (now + timedelta(hours=1)).isoformat(),
                "is_published": True,
            },
            format="json",
        )
        assert q_resp.status_code == status.HTTP_201_CREATED
        quiz_id = q_resp.data["id"]

        qn_resp = client.post(
            reverse("v1_homework:quiz-question-list"),
            {"quiz": quiz_id, "question_text": "Capital of BD?", "marks": "5.00", "order": 1},
            format="json",
        )
        assert qn_resp.status_code == status.HTTP_201_CREATED
        qn_id = qn_resp.data["id"]

        opt_ok = client.post(
            reverse("v1_homework:quiz-option-list"),
            {"question": qn_id, "option_text": "Dhaka", "is_correct": True, "order": 1},
            format="json",
        )
        assert opt_ok.status_code == status.HTTP_201_CREATED
        opt_id = opt_ok.data["id"]

        topic_resp = client.post(
            reverse("v1_homework:syllabus-topic-list"),
            {
                "session": str(self.session_a.id),
                "class_level": str(self.class_9.id),
                "subject": str(self.subj.id),
                "title": "Chapter 1",
                "order": 1,
            },
            format="json",
        )
        assert topic_resp.status_code == status.HTTP_201_CREATED
        prog_resp = client.post(
            reverse(
                "v1_homework:syllabus-topic-update-progress", kwargs={"pk": topic_resp.data["id"]}
            ),
            {"completion_percentage": 100},
            format="json",
        )
        assert prog_resp.status_code == status.HTTP_200_OK
        assert prog_resp.data["status"] == "completed"

        mat_file = SimpleUploadedFile(
            "notes.pdf", b"%PDF-1.4\nnotes", content_type="application/pdf"
        )
        mat_resp = client.post(
            reverse("v1_homework:material-list"),
            {
                "session": str(self.session_a.id),
                "class_level": str(self.class_9.id),
                "section": str(self.sec_a.id),
                "subject": str(self.subj.id),
                "title": "Lecture 1 Notes",
                "file": mat_file,
            },
            format="multipart",
        )
        assert mat_resp.status_code == status.HTTP_201_CREATED
        assert "/api/v1/homework/download/?token=" in mat_resp.data["download_url"]

        # Student 1 starts & submits quiz attempt -> auto-graded 5.00
        client.force_authenticate(user=self.student_user_1)
        start_resp = client.post(reverse("v1_homework:quiz-start-attempt", kwargs={"pk": quiz_id}))
        assert start_resp.status_code == status.HTTP_200_OK
        attempt_id = start_resp.data["id"]

        submit_resp = client.post(
            reverse("v1_homework:quiz-submit-attempt", kwargs={"pk": quiz_id}),
            {"attempt_id": attempt_id, "answers": {qn_id: opt_id}},
            format="json",
        )
        assert submit_resp.status_code == status.HTTP_200_OK
        assert submit_resp.data["score"] == "5.00"
        assert submit_resp.data["status"] == "graded"

        # Student 2 (Meghna) cannot see Padma-only material
        client.force_authenticate(user=self.student_user_2)
        assert client.get(reverse("v1_homework:material-list")).data["count"] == 0
