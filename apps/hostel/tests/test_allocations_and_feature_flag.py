"""Tests for Hostel per-institution feature flag, bed allocation conflicts, and vacate history."""

from datetime import date

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.hostel.models import Bed, BedStatus, Hostel, HostelAllocation, Room
from apps.hostel.services import allocate_bed, vacate_allocation
from apps.institutions.models import AcademicSession, Branch, Institution
from apps.students.models import Gender, Student


def _grant_hostel_perms(user: User, codenames: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(Hostel)
    role = Role.objects.create(
        institution=user.institution,
        name=f"HostelRole-{user.username}",
        code=f"hostel_role_{user.username}",
    )
    for code in codenames:
        short = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short, content_type=ct, defaults={"name": code}
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestHostelFeatureFlagAndAllocations:
    def setup_method(self) -> None:
        self.inst_enabled = Institution.objects.create(
            name_en="Cadet Academy",
            name_bn="ক্যাডেট একাডেমি",
            settings={"hostel_enabled": True},
        )
        self.inst_disabled = Institution.objects.create(
            name_en="Day School",
            name_bn="ডে স্কুল",
            settings={"hostel_enabled": False},
        )
        self.branch = Branch.objects.create(
            institution=self.inst_enabled, name="Main", code="M", is_main=True
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst_enabled,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.warden_enabled = User.objects.create_user(
            username="warden_on",
            password="pass",
            institution=self.inst_enabled,
            phone="+8801711100001",
            user_type=UserType.STAFF,
        )
        _grant_hostel_perms(self.warden_enabled, ["hostel.view", "hostel.manage", "hostel.warden"])
        self.warden_disabled = User.objects.create_user(
            username="warden_off",
            password="pass",
            institution=self.inst_disabled,
            phone="+8801711100002",
            user_type=UserType.STAFF,
        )
        _grant_hostel_perms(self.warden_disabled, ["hostel.view", "hostel.manage", "hostel.warden"])

        self.hostel = Hostel.objects.create(
            institution=self.inst_enabled, branch=self.branch, name="Surma Hall", code="SH-1"
        )
        self.room = Room.objects.create(
            institution=self.inst_enabled, hostel=self.hostel, room_number="101", capacity=2
        )
        self.bed1 = Bed.objects.create(
            institution=self.inst_enabled, room=self.room, bed_number="B1"
        )
        self.bed2 = Bed.objects.create(
            institution=self.inst_enabled, room=self.room, bed_number="B2"
        )
        self.student1 = Student.objects.create(
            institution=self.inst_enabled,
            student_id="HS-1",
            name_en="Fahim Ahmed",
            name_bn="ফাহিম আহমেদ",
            dob=date(2011, 1, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )
        self.student2 = Student.objects.create(
            institution=self.inst_enabled,
            student_id="HS-2",
            name_en="Nabil Islam",
            name_bn="নাবিল ইসলাম",
            dob=date(2011, 2, 1),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 1),
        )

    def test_feature_flag_off_returns_403(self) -> None:
        off_client = APIClient()
        off_client.force_authenticate(user=self.warden_disabled)
        resp = off_client.get(reverse("v1_hostel:hostel-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        on_client = APIClient()
        on_client.force_authenticate(user=self.warden_enabled)
        resp_on = on_client.get(reverse("v1_hostel:hostel-list"))
        assert resp_on.status_code == status.HTTP_200_OK
        assert resp_on.data["count"] == 1

    def test_bed_uniqueness_allocation_conflicts_and_vacate_history(self) -> None:
        alloc1 = allocate_bed(
            institution=self.inst_enabled,
            session=self.session,
            student=self.student1,
            bed=self.bed1,
        )
        self.bed1.refresh_from_db()
        assert self.bed1.status == BedStatus.OCCUPIED

        # Same bed cannot be allocated to student2
        with pytest.raises(ValidationError, match="cannot be allocated"):
            allocate_bed(
                institution=self.inst_enabled,
                session=self.session,
                student=self.student2,
                bed=self.bed1,
            )

        # Same student cannot be allocated a second bed in the same session
        with pytest.raises(ValidationError, match="already has an active hostel allocation"):
            allocate_bed(
                institution=self.inst_enabled,
                session=self.session,
                student=self.student1,
                bed=self.bed2,
            )

        # Vacating frees bed1 while preserving historical allocation record
        vacate_allocation(institution=self.inst_enabled, allocation=alloc1)
        self.bed1.refresh_from_db()
        alloc1.refresh_from_db()
        assert self.bed1.status == BedStatus.AVAILABLE
        assert alloc1.is_active is False
        assert alloc1.vacated_date is not None
        assert HostelAllocation.objects.count() == 1

        # Now student2 can take bed1
        alloc2 = allocate_bed(
            institution=self.inst_enabled,
            session=self.session,
            student=self.student2,
            bed=self.bed1,
        )
        assert alloc2.is_active is True
        assert HostelAllocation.objects.count() == 2
