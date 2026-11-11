"""API tests for academic structure and routine endpoints."""

from datetime import date, time

import pytest
from rest_framework import status

from apps.academics.models import (
    ClassLevel,
    MediumType,
    Period,
    Room,
    RoutineSlot,
    Section,
    Subject,
    Weekday,
)
from apps.accounts.models import User, UserType
from apps.accounts.test_helpers import api_client_as, make_user
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
        name_bn="চিটাগাং কলেজিয়েট স্কুল",
        name_en="Chittagong Collegiate School",
        eiin="234567",
    )


@pytest.fixture
def admin_user(institution: Institution) -> User:
    return make_user(
        username="admin_user",
        institution=institution,
        user_type=UserType.ADMIN,
        role="admin",
        permissions=[
            "view_classlevel",
            "change_classlevel",
            "add_classlevel",
            "delete_classlevel",
            "view_group",
            "change_group",
            "view_section",
            "change_section",
            "view_subject",
            "change_subject",
            "view_classsubject",
            "change_classsubject",
            "view_room",
            "change_room",
            "view_period",
            "change_period",
            "view_routineslot",
            "change_routineslot",
            "view_substituteassignment",
            "change_substituteassignment",
        ],
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
        end_time=time(12, 30),
    )


@pytest.mark.django_db
class TestClassLevelAPI:
    def test_list_and_create_class_level(self, institution: Institution, admin_user: User) -> None:
        client = api_client_as(admin_user)
        # Create
        payload = {
            "name": "Class 9",
            "code": "c09",
            "order": 9,
            "medium": MediumType.BANGLA,
            "has_groups": True,
        }
        res = client.post("/api/v1/academics/classes/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "Class 9"
        assert res.data["medium_display"] == "Bangla Medium"

        # List
        res_list = client.get("/api/v1/academics/classes/")
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.data["results"]) == 1


@pytest.mark.django_db
class TestSectionAPI:
    def test_bulk_create_sections(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        client = api_client_as(admin_user)
        payload = {
            "class_level_id": str(cls.id),
            "shift_id": str(shift.id),
            "session_id": str(session.id),
            "names": ["Padma", "Meghna", "Jamuna"],
            "capacity": 55,
        }
        res = client.post("/api/v1/academics/sections/bulk-create/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert len(res.data) == 3
        assert Section.objects.filter(class_level=cls, session=session).count() == 3

    def test_section_timetable_endpoint(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 7", code="c07", order=7
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="Rose"
        )
        sub = Subject.objects.create(
            institution=institution, code="101", name_en="Bangla", name_bn="বাংলা"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            weekday=Weekday.SUNDAY,
            period=period,
            subject=sub,
        )
        client = api_client_as(admin_user)
        res = client.get(f"/api/v1/academics/sections/{sec.id}/timetable/")
        assert res.status_code == status.HTTP_200_OK
        assert "grid" in res.data
        assert res.data["section_id"] == str(sec.id)


@pytest.mark.django_db
class TestRoutineAPI:
    def test_routine_validate_endpoint(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8
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
        # Pre-existing slot
        RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            weekday=Weekday.MONDAY,
            period=period,
            subject=sub,
        )

        client = api_client_as(admin_user)
        # Validate proposed slot colliding with existing section slot
        payload = {
            "section_id": str(sec.id),
            "weekday": Weekday.MONDAY,
            "period_id": str(period.id),
        }
        res = client.post("/api/v1/academics/routine/validate/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["is_valid"] is False
        assert any(c["code"] == "SECTION_CLASH" for c in res.data["conflicts"])

    def test_routine_filters(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 10", code="c10", order=10
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="Lily"
        )
        sub = Subject.objects.create(
            institution=institution, code="109", name_en="Math", name_bn="গণিত"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        teacher = User.objects.create_user(
            username="rafiq_teacher",
            phone="+8801730000001",
            full_name="Rafiqul Islam",
            institution=institution,
        )
        room = Room.objects.create(institution=institution, name="Room 201")
        RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            weekday=Weekday.TUESDAY,
            period=period,
            subject=sub,
            teacher_user=teacher,
            room=room,
        )

        client = api_client_as(admin_user)
        # Filter by section
        res_sec = client.get(f"/api/v1/academics/routine/?section_id={sec.id}")
        assert res_sec.status_code == status.HTTP_200_OK
        assert len(res_sec.data["results"]) == 1

        # Filter by teacher
        res_t = client.get(f"/api/v1/academics/routine/?teacher_id={teacher.id}")
        assert res_t.status_code == status.HTTP_200_OK
        assert len(res_t.data["results"]) == 1

        # Filter by room
        res_r = client.get(f"/api/v1/academics/routine/?room_id={room.id}")
        assert res_r.status_code == status.HTTP_200_OK
        assert len(res_r.data["results"]) == 1


@pytest.mark.django_db
class TestCopySessionAPI:
    def test_copy_session_endpoint(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        target_session = AcademicSession.objects.create(
            institution=institution,
            name="Academic Year 2027",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )

        client = api_client_as(admin_user)
        payload = {
            "source_session_id": str(session.id),
            "target_session_id": str(target_session.id),
            "copy_sections": True,
            "copy_class_subjects": True,
            "dry_run": False,
        }
        res = client.post("/api/v1/academics/copy-session/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["sections_count"] == 1
        assert Section.objects.filter(session=target_session).count() == 1


@pytest.mark.django_db
class TestTenantIsolation:
    def test_user_cannot_see_other_institution_academics(
        self,
        institution: Institution,
        other_institution: Institution,
        admin_user: User,
    ) -> None:
        # Create Class in other institution
        other_cls = ClassLevel.objects.create(
            institution=other_institution,
            name="Other Class",
            code="oth01",
            order=1,
        )
        client = api_client_as(admin_user)
        res = client.get("/api/v1/academics/classes/")
        assert res.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in res.data["results"]]
        assert str(other_cls.id) not in ids

        # Attempt to retrieve other tenant's class directly
        res_detail = client.get(f"/api/v1/academics/classes/{other_cls.id}/")
        assert res_detail.status_code == status.HTTP_404_NOT_FOUND
