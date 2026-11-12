"""Tests for GatePass guardian OTP workflow, warden approval, checkout/checkin, and curfew alerts."""

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.communications.models import NotificationEvent
from apps.guardians.models import Guardian, GuardianRelation, StudentGuardian
from apps.hostel.models import GatePass, GatePassStatus, Hostel
from apps.hostel.services import (
    approve_gate_pass,
    confirm_gate_pass_otp,
    request_gate_pass,
)
from apps.hostel.tasks import send_hostel_curfew_alerts
from apps.institutions.models import Branch, Institution
from apps.students.models import Gender, Student


def _grant_hostel_perms(user: User, codenames: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(Hostel)
    role = Role.objects.create(
        institution=user.institution,
        name=f"HRole-{user.username}",
        code=f"h_role_{user.username}",
    )
    for code in codenames:
        short = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short, content_type=ct, defaults={"name": code}
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestGatePassOTPAndCurfewAlerts:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Mirpur Residential",
            name_bn="মিরপুর রেসিডেন্সিয়াল",
            settings={"hostel_enabled": True},
        )
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="M", is_main=True
        )
        self.admin = User.objects.create_user(
            username="admin_h",
            password="pass",
            institution=self.inst,
            phone="+8801711200001",
            user_type=UserType.ADMIN,
        )
        _grant_hostel_perms(self.admin, ["hostel.view", "hostel.manage", "hostel.warden"])

        self.guardian_user = User.objects.create_user(
            username="guard_h",
            password="pass",
            institution=self.inst,
            phone="+8801711200002",
            user_type=UserType.GUARDIAN,
        )
        self.guardian = Guardian.objects.create(
            institution=self.inst,
            user=self.guardian_user,
            name_en="Selim Hossain",
            phone="+8801711200002",
        )
        self.student = Student.objects.create(
            institution=self.inst,
            student_id="HS-99",
            name_en="Tariq Hossain",
            name_bn="তারিক হোসেন",
            dob=date(2010, 5, 5),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        StudentGuardian.objects.create(
            institution=self.inst,
            student=self.student,
            guardian=self.guardian,
            relation=GuardianRelation.FATHER,
            is_primary=True,
        )
        self.hostel = Hostel.objects.create(
            institution=self.inst, branch=self.branch, name="Padma Hall", code="PH-1"
        )

    def test_gatepass_otp_approval_checkout_and_curfew_alert(self) -> None:
        now = timezone.now()
        gp, raw_otp = request_gate_pass(
            institution=self.inst,
            student=self.student,
            hostel=self.hostel,
            reason="Family event",
            destination="Dhanmondi",
            expected_out_at=now,
            expected_return_at=now + timedelta(hours=4),
        )
        assert gp.status == GatePassStatus.PENDING_GUARDIAN_OTP
        assert (
            NotificationEvent.objects.filter(
                institution=self.inst, event_type="hostel_gatepass_otp"
            ).count()
            == 1
        )

        # Cannot approve before guardian OTP confirmation
        with pytest.raises(ValidationError, match="confirmed by guardian OTP"):
            approve_gate_pass(institution=self.inst, gate_pass=gp, actor=self.admin)

        # Wrong OTP rejected
        with pytest.raises(ValidationError, match="Invalid guardian OTP"):
            confirm_gate_pass_otp(institution=self.inst, gate_pass=gp, otp="000000")

        # Guardian confirms OTP via API
        g_client = APIClient()
        g_client.force_authenticate(user=self.guardian_user)
        confirm_resp = g_client.post(
            reverse("v1_hostel:gate-pass-confirm-otp", kwargs={"pk": str(gp.id)}),
            {"otp": raw_otp},
            format="json",
        )
        assert confirm_resp.status_code == status.HTTP_200_OK
        assert confirm_resp.data["status"] == GatePassStatus.GUARDIAN_CONFIRMED

        # Warden approves and checks out via API
        w_client = APIClient()
        w_client.force_authenticate(user=self.admin)
        approve_resp = w_client.post(
            reverse("v1_hostel:gate-pass-approve", kwargs={"pk": str(gp.id)}),
            format="json",
        )
        assert approve_resp.status_code == status.HTTP_200_OK
        assert approve_resp.data["status"] == GatePassStatus.APPROVED

        out_resp = w_client.post(
            reverse("v1_hostel:gate-pass-checkout", kwargs={"pk": str(gp.id)}),
            format="json",
        )
        assert out_resp.status_code == status.HTTP_200_OK
        assert out_resp.data["status"] == GatePassStatus.CHECKED_OUT

        # Simulate overdue return -> curfew alert task marks OVERDUE & notifies
        GatePass.objects.filter(id=gp.id).update(expected_return_at=now - timedelta(minutes=30))
        alert_res = send_hostel_curfew_alerts()
        assert alert_res["curfew_alerts"] == 1
        gp.refresh_from_db()
        assert gp.status == GatePassStatus.OVERDUE
        assert gp.curfew_alert_sent is True
        assert (
            NotificationEvent.objects.filter(
                institution=self.inst, event_type="hostel_curfew_overdue"
            ).count()
            >= 1
        )
