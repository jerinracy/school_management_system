"""Tests for transport capacity limits, expiry alert Celery task, and LiveLocation retention."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.communications.models import NotificationEvent
from apps.institutions.models import AcademicSession, Branch, Institution
from apps.staff.models import Staff
from apps.students.models import Gender, Student
from apps.transport.models import (
    Driver,
    LiveLocation,
    Route,
    RouteStop,
    Vehicle,
)
from apps.transport.services import assign_transport
from apps.transport.tasks import purge_old_live_locations, send_transport_expiry_alerts


@pytest.mark.django_db
class TestTransportCapacityExpiryAndRetention:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(name_en="Uttara High", name_bn="উত্তরা হাই")
        self.branch = Branch.objects.create(
            institution=self.inst, name="Main", code="M", is_main=True
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.admin = User.objects.create_user(
            username="admin_u",
            password="pass",
            institution=self.inst,
            phone="+8801711000000",
            user_type=UserType.ADMIN,
        )
        self.driver_staff = Staff.objects.create(
            institution=self.inst,
            employee_id="DRV-01",
            full_name_en="Babul Mia",
            phone="+8801711110001",
            dob=date(1982, 5, 1),
            joining_date=date(2020, 1, 1),
        )
        self.driver = Driver.objects.create(
            institution=self.inst,
            staff=self.driver_staff,
            license_no="DL-BD-1001",
            license_expiry=timezone.localdate() + timedelta(days=10),
        )
        self.vehicle = Vehicle.objects.create(
            institution=self.inst,
            branch=self.branch,
            registration_no="DHAKA-METRO-GA-11-2233",
            capacity=2,
            fitness_expiry=timezone.localdate() + timedelta(days=5),
        )
        self.route = Route.objects.create(
            institution=self.inst,
            branch=self.branch,
            name="Uttara Sector 10",
            code="R-01",
            vehicle=self.vehicle,
            driver=self.driver,
            monthly_fee=Decimal("1500.00"),
        )
        self.other_route = Route.objects.create(
            institution=self.inst,
            branch=self.branch,
            name="Mirpur 10",
            code="R-02",
        )
        self.stop1 = RouteStop.objects.create(
            institution=self.inst,
            route=self.route,
            name="Sector 10 Gate",
            order=1,
            pickup_time=time(7, 30),
        )
        self.other_stop = RouteStop.objects.create(
            institution=self.inst,
            route=self.other_route,
            name="Mirpur Circle",
            order=1,
        )
        self.students = [
            Student.objects.create(
                institution=self.inst,
                student_id=f"STU-{i}",
                name_en=f"Student {i}",
                name_bn=f"শিক্ষার্থী {i}",
                dob=date(2012, 1, i),
                gender=Gender.MALE,
                admission_date=date(2026, 1, 5),
            )
            for i in range(1, 4)
        ]

    def test_capacity_and_stop_validation(self) -> None:
        with pytest.raises(ValidationError, match="does not belong to the chosen route"):
            assign_transport(
                institution=self.inst,
                session=self.session,
                route=self.route,
                stop=self.other_stop,
                student=self.students[0],
            )

        assign_transport(
            institution=self.inst,
            session=self.session,
            route=self.route,
            stop=self.stop1,
            student=self.students[0],
        )
        assign_transport(
            institution=self.inst,
            session=self.session,
            route=self.route,
            stop=self.stop1,
            student=self.students[1],
        )
        with pytest.raises(ValidationError, match="capacity reached"):
            assign_transport(
                institution=self.inst,
                session=self.session,
                route=self.route,
                stop=self.stop1,
                student=self.students[2],
            )

    def test_expiry_alerts_and_location_retention(self) -> None:
        result = send_transport_expiry_alerts(days_ahead=30)
        assert result["alerts_sent"] == 2
        assert (
            NotificationEvent.objects.filter(
                institution=self.inst,
                source_module="transport",
                event_type__in=["transport_vehicle_expiry", "transport_driver_license_expiry"],
            ).count()
            == 2
        )

        old_ts = timezone.now() - timedelta(days=35)
        recent_ts = timezone.now() - timedelta(days=2)
        LiveLocation.objects.create(
            institution=self.inst,
            vehicle=self.vehicle,
            latitude=Decimal("23.875900"),
            longitude=Decimal("90.379500"),
            recorded_at=old_ts,
        )
        LiveLocation.objects.create(
            institution=self.inst,
            vehicle=self.vehicle,
            latitude=Decimal("23.876100"),
            longitude=Decimal("90.380100"),
            recorded_at=recent_ts,
        )
        purge_result = purge_old_live_locations(retention_days=30)
        assert purge_result["deleted"] == 1
        assert LiveLocation.objects.filter(vehicle=self.vehicle).count() == 1
