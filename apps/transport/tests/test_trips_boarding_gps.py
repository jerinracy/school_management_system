"""Tests for driver permissions, boarding scan idempotency, guardian alerts, and GPS device auth."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.communications.models import NotificationEvent
from apps.guardians.models import Guardian, GuardianRelation, StudentGuardian
from apps.institutions.models import AcademicSession, Branch, Institution
from apps.staff.models import Staff
from apps.students.models import Gender, Student
from apps.transport.models import (
    BoardingEvent,
    BoardingEventType,
    BoardingMethod,
    Driver,
    Route,
    RouteStop,
    TripDirection,
    Vehicle,
)
from apps.transport.services import assign_transport, rotate_vehicle_gps_token


def _grant_transport_perms(user: User, codenames: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(Vehicle)
    role = Role.objects.create(
        institution=user.institution,
        name=f"TrRole-{user.username}",
        code=f"tr_role_{user.username}",
    )
    for code in codenames:
        short = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short, content_type=ct, defaults={"name": code}
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestTransportTripsBoardingAndGPS:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(name_en="Banani Academy", name_bn="বনানী একাডেমি")
        self.inst_b = Institution.objects.create(name_en="Other School", name_bn="অন্য স্কুল")
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="MB", is_main=True
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.driver_user = User.objects.create_user(
            username="driver_1",
            password="pass",
            institution=self.inst,
            user_type=UserType.STAFF,
        )
        self.other_driver_user = User.objects.create_user(
            username="driver_2",
            password="pass",
            institution=self.inst,
            user_type=UserType.STAFF,
        )
        self.driver_staff = Staff.objects.create(
            institution=self.inst,
            user=self.driver_user,
            employee_id="DRV-1",
            full_name_en="Jalal Uddin",
            phone="+8801711001100",
            dob=date(1980, 1, 1),
            joining_date=date(2019, 1, 1),
        )
        self.other_driver_staff = Staff.objects.create(
            institution=self.inst,
            user=self.other_driver_user,
            employee_id="DRV-2",
            full_name_en="Mizan Mia",
            phone="+8801711001101",
            dob=date(1981, 1, 1),
            joining_date=date(2020, 1, 1),
        )
        self.driver = Driver.objects.create(
            institution=self.inst,
            staff=self.driver_staff,
            license_no="DL-001",
            license_expiry=date(2028, 1, 1),
        )
        self.other_driver = Driver.objects.create(
            institution=self.inst,
            staff=self.other_driver_staff,
            license_no="DL-002",
            license_expiry=date(2028, 1, 1),
        )
        self.vehicle = Vehicle.objects.create(
            institution=self.inst,
            branch=self.branch,
            registration_no="DHAKA-1234",
            capacity=30,
            gps_device_id="GPS-UNIT-01",
        )
        self.gps_token = rotate_vehicle_gps_token(vehicle=self.vehicle, gps_device_id="GPS-UNIT-01")
        self.route = Route.objects.create(
            institution=self.inst,
            branch=self.branch,
            name="Banani Loop",
            code="BN-01",
            vehicle=self.vehicle,
            driver=self.driver,
        )
        self.stop = RouteStop.objects.create(
            institution=self.inst,
            route=self.route,
            name="Road 11",
            order=1,
        )
        self.guardian_user = User.objects.create_user(
            username="guard_1",
            password="pass",
            institution=self.inst,
            phone="+8801711002200",
            user_type=UserType.GUARDIAN,
        )
        self.guardian = Guardian.objects.create(
            institution=self.inst,
            user=self.guardian_user,
            name_en="Rezaul Karim",
            phone="+8801711002200",
        )
        self.student = Student.objects.create(
            institution=self.inst,
            student_id="STU-900",
            name_en="Arif Karim",
            name_bn="আরিফ করিম",
            dob=date(2013, 2, 10),
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
        assign_transport(
            institution=self.inst,
            session=self.session,
            route=self.route,
            stop=self.stop,
            student=self.student,
        )

    def test_driver_trip_permissions_and_boarding_idempotency(self) -> None:
        # Other driver cannot start driver 1's route trip
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_driver_user)
        forbidden_start = other_client.post(
            reverse("v1_transport:trip-start"),
            {"route": str(self.route.id), "direction": TripDirection.MORNING_PICKUP},
            format="json",
        )
        assert forbidden_start.status_code == status.HTTP_403_FORBIDDEN

        # Assigned driver starts trip
        driver_client = APIClient()
        driver_client.force_authenticate(user=self.driver_user)
        start_resp = driver_client.post(
            reverse("v1_transport:trip-start"),
            {"route": str(self.route.id), "direction": TripDirection.MORNING_PICKUP},
            format="json",
        )
        assert start_resp.status_code == status.HTTP_201_CREATED
        trip_id = start_resp.data["id"]

        # Boarding scan is idempotent & alerts guardian once
        scan_payload = {
            "trip": trip_id,
            "student": str(self.student.id),
            "stop": str(self.stop.id),
            "event_type": BoardingEventType.BOARDED,
            "method": BoardingMethod.QR,
            "idempotency_key": "scan-trip-stu-900",
        }
        scan_1 = driver_client.post(
            reverse("v1_transport:boarding-event-scan"), scan_payload, format="json"
        )
        assert scan_1.status_code == status.HTTP_201_CREATED
        scan_2 = driver_client.post(
            reverse("v1_transport:boarding-event-scan"), scan_payload, format="json"
        )
        assert scan_2.status_code == status.HTTP_200_OK
        assert scan_1.data["id"] == scan_2.data["id"]
        assert BoardingEvent.objects.count() == 1
        assert (
            NotificationEvent.objects.filter(
                institution=self.inst, event_type="transport_boarded"
            ).count()
            == 1
        )

        # Guardian can view their ward's boarding event
        g_client = APIClient()
        g_client.force_authenticate(user=self.guardian_user)
        g_events = g_client.get(reverse("v1_transport:boarding-event-list"))
        assert g_events.status_code == status.HTTP_200_OK
        assert g_events.data["count"] == 1

        # Assigned driver ends trip
        end_resp = driver_client.post(
            reverse("v1_transport:trip-end", kwargs={"pk": trip_id}),
            {"notes": "Arrived safely"},
            format="json",
        )
        assert end_resp.status_code == status.HTTP_200_OK
        assert end_resp.data["status"] == "completed"

    def test_gps_device_token_auth_and_live_location_latest_history(self) -> None:
        anon = APIClient()
        ping_url = reverse("v1_transport:gps-ping")

        bad_resp = anon.post(
            ping_url,
            {"gps_device_id": "GPS-UNIT-01", "latitude": "23.7937", "longitude": "90.4066"},
            HTTP_X_GPS_DEVICE_TOKEN="wrong-token",
            format="json",
        )
        assert bad_resp.status_code == status.HTTP_401_UNAUTHORIZED

        ok_resp = anon.post(
            ping_url,
            {
                "latitude": "23.793700",
                "longitude": "90.406600",
                "speed_kmh": "32.50",
            },
            HTTP_X_GPS_DEVICE_ID="GPS-UNIT-01",
            HTTP_X_GPS_DEVICE_TOKEN=self.gps_token,
            format="json",
        )
        assert ok_resp.status_code == status.HTTP_201_CREATED

        # Guardian can view latest location of ward's assigned vehicle
        g_client = APIClient()
        g_client.force_authenticate(user=self.guardian_user)
        latest_resp = g_client.get(
            reverse("v1_transport:live-location-latest"),
            {"vehicle": str(self.vehicle.id)},
        )
        assert latest_resp.status_code == status.HTTP_200_OK
        assert Decimal(latest_resp.data["latitude"]) == Decimal("23.793700")

        # Tenant isolation: institution B manager cannot see institution A's vehicles or locations
        other_mgr = User.objects.create_user(
            username="mgr_b",
            password="pass",
            institution=self.inst_b,
            user_type=UserType.STAFF,
        )
        _grant_transport_perms(other_mgr, ["transport.view", "transport.manage"])
        b_client = APIClient()
        b_client.force_authenticate(user=other_mgr)
        b_locs = b_client.get(reverse("v1_transport:live-location-list"))
        assert b_locs.status_code == status.HTTP_200_OK
        assert b_locs.data["count"] == 0
