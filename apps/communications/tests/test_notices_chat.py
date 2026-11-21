"""Tests for Notice Board, Teacher-Guardian Chat, and Emergency Alerts."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel
from apps.accounts.models import User
from apps.communications.models import (
    NoticeAudience,
)
from apps.communications.services.chat_service import get_or_create_chat_thread, send_chat_message
from apps.communications.services.notice_service import create_notice, get_visible_notices_for_user
from apps.guardians.models import Guardian
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import Student, StudentEnrollment


@pytest.mark.django_db
class TestNotices:
    """Test notice creation, audience targeting, and pinning."""

    @pytest.fixture
    def setup_school(self):
        from datetime import date, time

        from apps.academics.models import Section
        from apps.institutions.models import AcademicSession, Branch, Shift

        inst = Institution.objects.create(name_en="Sylhet Govt Pilot", name_bn="সিলেট সরকারি পাইলট")
        branch = Branch.objects.create(
            institution=inst, name="Main Campus", code="MAIN", is_main=True
        )
        shift = Shift.objects.create(
            institution=inst,
            branch=branch,
            name="Morning",
            start_time=time(8, 0),
            end_time=time(13, 0),
        )
        session = AcademicSession.objects.create(
            institution=inst,
            name="2026",
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_current=True,
        )

        cls_six = ClassLevel.objects.create(institution=inst, name="Class 6", code="c06", order=6)
        cls_seven = ClassLevel.objects.create(institution=inst, name="Class 7", code="c07", order=7)
        sec_six = Section.objects.create(
            institution=inst,
            class_level=cls_six,
            shift=shift,
            session=session,
            name="A",
        )

        student_user = User.objects.create_user(
            username="student_karim",
            phone="+8801722334455",
            password="password123",
            institution=inst,
        )
        student = Student.objects.create(
            institution=inst,
            student_id="20260001",
            name_en="Karim Rahman",
            name_bn="করিম রহমান",
            dob=date(2012, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        student_user.student_profile = student
        student_user.save()

        # Enroll Karim in Class 6
        StudentEnrollment.objects.create(
            institution=inst,
            student=student,
            session=session,
            class_level=cls_six,
            section=sec_six,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status="active",
        )

        return inst, cls_six, cls_seven, student_user

    def test_notice_audience_filtering(self, setup_school):
        inst, cls_six, cls_seven, student_user = setup_school

        # Notice for all
        n_all = create_notice(
            institution=inst,
            created_by=None,
            title_en="Sports Day Announcement",
            content_en="All students participate",
            target_audience=NoticeAudience.ALL,
        )

        # Notice specifically for Class 7
        n_seven = create_notice(
            institution=inst,
            created_by=None,
            title_en="Class 7 Science Project",
            content_en="Bring lab coats",
            target_audience=NoticeAudience.SPECIFIC_CLASS,
            target_class_level=cls_seven,
        )

        # Notice specifically for Class 6
        n_six = create_notice(
            institution=inst,
            created_by=None,
            title_en="Class 6 Math Test",
            content_en="Chapters 1-3",
            target_audience=NoticeAudience.SPECIFIC_CLASS,
            target_class_level=cls_six,
        )

        visible = get_visible_notices_for_user(inst, student_user)
        visible_ids = set(visible.values_list("id", flat=True))

        assert n_all.id in visible_ids
        assert n_six.id in visible_ids
        assert n_seven.id not in visible_ids


@pytest.mark.django_db
class TestTeacherGuardianChat:
    """Test 1-on-1 dialogue between teachers and student guardians."""

    @pytest.fixture
    def chat_setup(self):
        from datetime import date

        inst = Institution.objects.create(name_en="Khulna Model School", name_bn="খুলনা মডেল স্কুল")

        teacher_user = User.objects.create_user(
            username="teacher_salma", phone="+8801911223344", password="pwd", institution=inst
        )
        teacher_staff = Staff.objects.create(
            institution=inst,
            user=teacher_user,
            employee_id="T-101",
            full_name_en="Mrs. Salma",
            gender="female",
            dob=date(1990, 1, 1),
            phone="+8801911223344",
            joining_date=date(2020, 1, 1),
        )

        guardian_user = User.objects.create_user(
            username="guardian_kamal", phone="+8801922334455", password="pwd", institution=inst
        )
        guardian = Guardian.objects.create(
            institution=inst,
            user=guardian_user,
            name_en="Mr. Kamal",
            phone="+8801922334455",
        )

        return inst, teacher_staff, guardian, teacher_user, guardian_user

    def test_chat_thread_and_messages(self, chat_setup):
        inst, teacher_staff, guardian, teacher_user, guardian_user = chat_setup

        thread, created = get_or_create_chat_thread(
            institution=inst,
            teacher=teacher_staff,
            guardian=guardian,
            subject="Student Progress Query",
        )
        assert created
        assert not thread.is_closed

        # Guardian sends message
        msg1 = send_chat_message(thread, guardian_user, "Hello Teacher, how is my child doing?")
        assert msg1.sender == guardian_user
        assert not msg1.is_read

        # Teacher replies
        msg2 = send_chat_message(thread, teacher_user, "He is doing very well in mathematics!")
        assert msg2.sender == teacher_user
        assert thread.messages.count() == 2

    def test_chat_api_endpoints(self, chat_setup):
        inst, teacher_staff, guardian, teacher_user, guardian_user = chat_setup
        thread, _ = get_or_create_chat_thread(
            institution=inst,
            teacher=teacher_staff,
            guardian=guardian,
            subject="Discussion",
        )

        client = APIClient()
        client.force_authenticate(user=guardian_user)

        # Post a message via API
        resp = client.post(
            f"/api/v1/communications/chat/threads/{thread.id}/messages/",
            {"content": "Thank you for the update."},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["content"] == "Thank you for the update."

        # Fetch messages
        list_resp = client.get(f"/api/v1/communications/chat/threads/{thread.id}/messages/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data) == 1

    def test_chat_thread_creation_idempotency_and_metadata(self, chat_setup):
        inst, teacher_staff, guardian, teacher_user, guardian_user = chat_setup
        from apps.staff.models import Designation

        desig = Designation.objects.create(
            institution=inst,
            title="Senior Teacher",
            title_bn="সিনিয়র শিক্ষক",
            code="ST",
        )
        teacher_staff.designation = desig
        teacher_staff.full_name_bn = "রাশিদা বেগম"
        teacher_staff.save()

        client = APIClient()
        client.force_authenticate(user=guardian_user)

        # 1st creation call -> 201 Created
        resp1 = client.post(
            "/api/v1/communications/chat/threads/",
            {"teacher": str(teacher_staff.id), "subject": "Math Query"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_201_CREATED
        thread_id = resp1.data["id"]
        assert resp1.data["teacher_name_bn"] == "রাশিদা বেগম"
        assert resp1.data["teacher_designation"] == "Senior Teacher"

        # 2nd creation call with same teacher -> 200 OK (idempotent, returns existing thread)
        resp2 = client.post(
            "/api/v1/communications/chat/threads/",
            {"teacher": str(teacher_staff.id), "subject": "Math Query"},
            format="json",
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["id"] == thread_id


@pytest.mark.django_db
class TestEmergencyAlerts:
    """Test emergency broadcasting."""

    def test_emergency_alert_creation_and_broadcast(self):
        inst = Institution.objects.create(
            name_en="Rangpur Public School", name_bn="রংপুর পাবলিক স্কুল"
        )
        admin_user = User.objects.create_superuser(
            username="admin_rps",
            phone="+8801700998877",
            password="adminpassword",
            institution=inst,
        )
        User.objects.create_user(
            username="user1_rps", phone="+8801711223344", password="pwd", institution=inst
        )
        User.objects.create_user(
            username="user2_rps", phone="+8801722334455", password="pwd", institution=inst
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(
            "/api/v1/communications/emergency-alerts/",
            {
                "title": "Severe Cyclone Warning",
                "message_bn": "ঘূর্ণিঝড়ের কারণে আগামীকাল স্কুল বন্ধ থাকবে।",
                "message_en": "School closed tomorrow due to cyclone.",
                "severity": "critical",
                "channels": ["sms", "in_app"],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["total_recipients"] >= 3
        assert resp.data["successful_deliveries"] >= 3
