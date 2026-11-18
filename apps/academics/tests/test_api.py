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

    def test_create_class_level_with_numeric_order_alias(
        self, institution: Institution, admin_user: User
    ) -> None:
        client = api_client_as(admin_user)
        payload = {
            "name": "Class 10",
            "code": "c10",
            "numeric_order": 10,
        }
        res = client.post("/api/v1/academics/classes/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "Class 10"
        assert res.data["order"] == 10

    def test_create_class_level_by_superuser_with_null_institution(
        self, institution: Institution
    ) -> None:
        # Superuser created with institution=None
        su = User.objects.create_superuser(
            username="standalone_superuser",
            password="Password123#",
            user_type="superadmin",
            institution=None,
        )
        client = api_client_as(su)
        payload = {
            "name": "Class 11",
            "code": "c11",
            "numeric_order": 11,
        }
        res = client.post("/api/v1/academics/classes/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "Class 11"
        assert res.data["order"] == 11
        # Institution was automatically resolved
        created_cls = ClassLevel.objects.get(id=res.data["id"])
        assert created_cls.institution == institution


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

    def test_bulk_create_sections_with_class_id_and_auto_shift_session(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8
        )
        client = api_client_as(admin_user)
        # Client sends only class_id and names (matching UI quick-create)
        payload = {
            "class_id": str(cls.id),
            "names": ["Section A", "Section B"],
        }
        res = client.post("/api/v1/academics/sections/bulk-create/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert len(res.data) == 2
        sections = Section.objects.filter(class_level=cls)
        assert sections.count() == 2
        for sec in sections:
            assert sec.shift == shift
            assert sec.session == session

    def test_bulk_create_sections_by_superuser_with_null_institution(
        self,
        institution: Institution,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        superuser = User.objects.create_superuser(
            username="super_test",
            password="password123",
            user_type=UserType.SUPERADMIN,
            institution=None,
        )
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 9", code="c09", order=9
        )
        client = api_client_as(superuser)
        payload = {
            "class_id": str(cls.id),
            "names": ["Science", "Commerce"],
        }
        res = client.post("/api/v1/academics/sections/bulk-create/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert len(res.data) == 2
        assert Section.objects.filter(class_level=cls).count() == 2

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

    def test_create_routine_slot(
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
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        sub = Subject.objects.create(
            institution=institution, code="108", name_en="Math", name_bn="গণিত"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        client = api_client_as(admin_user)
        # Payload sent by RoutineBuilderPage.tsx
        payload = {
            "section": str(sec.id),
            "weekday": 0,
            "period": str(period.id),
            "subject": str(sub.id),
        }
        res = client.post("/api/v1/academics/routine/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED

    def test_validate_routine_slot_with_frontend_payload(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 6", code="c06", order=6
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="B"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="2nd Period",
            start_time=time(9, 0),
            end_time=time(9, 45),
            order=2,
        )
        client = api_client_as(admin_user)
        # Payload sent by RoutineBuilderPage.tsx: handleValidateSlot
        payload = {
            "section": str(sec.id),
            "period": str(period.id),
            "weekday": 0,
            "room": "",
        }
        res = client.post("/api/v1/academics/routine/validate/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["is_valid"] is True

    def test_create_and_patch_routine_slot_with_teacher_staff(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        from apps.staff.models import Staff

        cls = ClassLevel.objects.create(
            institution=institution, name="Class 7", code="c07", order=7
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        sub = Subject.objects.create(
            institution=institution, code="ENG701", name_en="English", name_bn="ইংরেজি"
        )
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            start_time=time(8, 0),
            end_time=time(8, 45),
            order=1,
        )
        teacher_staff = Staff.objects.create(
            institution=institution,
            full_name_en="Abdur Rahman",
            full_name_bn="আব্দুর রহমান",
            staff_type="teacher",
            phone="+8801700000001",
            dob=date(1990, 1, 1),
            joining_date=date(2020, 1, 1),
            employee_id="TCH-001",
        )

        client = api_client_as(admin_user)
        # 1. Create slot without teacher (deferred)
        create_payload = {
            "section": str(sec.id),
            "period": str(period.id),
            "subject": str(sub.id),
            "weekday": 2,
        }
        res_create = client.post("/api/v1/academics/routine/", create_payload, format="json")
        assert res_create.status_code == status.HTTP_201_CREATED
        slot_id = res_create.data["id"]
        assert res_create.data["teacher_name"] is None

        # 2. Assign teacher later via PATCH
        patch_payload = {
            "teacher": str(teacher_staff.id),
        }
        res_patch = client.patch(
            f"/api/v1/academics/routine/{slot_id}/", patch_payload, format="json"
        )
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.data["teacher_name"] == "Abdur Rahman"
        assert res_patch.data["teacher_staff"] == teacher_staff.id

    def test_sections_list_with_branch_filter_inherited_from_class(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        branch = Branch.objects.create(institution=institution, name="Dhanmondi Branch")
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 8", code="c08", order=8, branch=branch
        )
        sec = Section.objects.create(
            institution=institution, class_level=cls, shift=shift, session=session, name="A"
        )
        # sec.branch is None, but class.branch is set to branch
        client = api_client_as(admin_user)
        res = client.get(f"/api/v1/academics/sections/?class_level={cls.id}&branch={branch.id}")
        assert res.status_code == status.HTTP_200_OK
        results = res.data["results"]
        assert len(results) == 1
        assert results[0]["id"] == str(sec.id)


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


@pytest.mark.django_db
class TestAcademicCrudFixes:
    def test_create_catalog_subject_with_bilingual_fields(
        self, institution: Institution, admin_user: User
    ) -> None:
        client = api_client_as(admin_user)
        payload = {
            "name_en": "Higher Mathematics",
            "name_bn": "উচ্চতর গণিত",
            "code": "HM-101",
            "type": "compulsory",
        }
        res = client.post("/api/v1/academics/subjects/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name_en"] == "Higher Mathematics"
        assert res.data["name_bn"] == "উচ্চতর গণিত"
        assert res.data["type"] == "compulsory"

    def test_create_catalog_subject_with_legacy_payload(
        self, institution: Institution, admin_user: User
    ) -> None:
        client = api_client_as(admin_user)
        # Old frontend payload with 'name' and 'subject_type': 'theory'
        payload = {
            "name": "General Science",
            "code": "GS-102",
            "subject_type": "theory",
        }
        res = client.post("/api/v1/academics/subjects/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name_en"] == "General Science"
        assert res.data["name_bn"] == "General Science"
        assert res.data["type"] == "compulsory"

    def test_create_class_subject_with_total_and_pass_marks_and_auto_session(
        self,
        institution: Institution,
        admin_user: User,
        session: AcademicSession,
    ) -> None:
        client = api_client_as(admin_user)
        cls = ClassLevel.objects.create(
            institution=institution, name="Class 9", code="c09", order=9
        )
        subj = Subject.objects.create(
            institution=institution,
            name_en="Physics",
            name_bn="পদার্থবিজ্ঞান",
            code="PHY-101",
            type="compulsory",
        )
        payload = {
            "class_level": str(cls.id),
            "subject": str(subj.id),
            "total_marks": 100,
            "pass_marks": 33,
        }
        res = client.post("/api/v1/academics/class-subjects/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["full_marks"] == "100.00"
        assert str(res.data["session"]) == str(session.id)
        assert res.data["pass_rule"] == {"pass_marks": 33}

    def test_create_room_with_room_number_and_room_type(
        self, institution: Institution, admin_user: User
    ) -> None:
        client = api_client_as(admin_user)
        payload = {
            "room_number": "Lab-201",
            "capacity": 45,
            "room_type": "lab",
        }
        res = client.post("/api/v1/academics/rooms/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "Lab-201"
        assert res.data["type"] == "lab"

    def test_create_period_with_period_order_and_auto_shift(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
    ) -> None:
        client = api_client_as(admin_user)
        payload = {
            "name": "1st Period",
            "start_time": "08:00:00",
            "end_time": "08:45:00",
            "period_order": 1,
        }
        res = client.post("/api/v1/academics/periods/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["order"] == 1
        assert str(res.data["shift"]) == str(shift.id)

    def test_class_levels_filtered_by_shift_and_session(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        other_shift = Shift.objects.create(
            institution=institution,
            branch=shift.branch,
            name="Day Shift",
            start_time=time(12, 30),
            end_time=time(17, 30),
        )
        c_morning = ClassLevel.objects.create(
            institution=institution,
            name="Class 1 Morning",
            code="c01m",
            order=1,
            shift=shift,
            session=session,
        )
        c_day = ClassLevel.objects.create(
            institution=institution,
            name="Class 1 Day",
            code="c01d",
            order=2,
            shift=other_shift,
            session=session,
        )

        client = api_client_as(admin_user)
        # Filter for morning shift
        res = client.get(f"/api/v1/academics/classes/?shift={shift.id}")
        assert res.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in res.data["results"]]
        assert str(c_morning.id) in ids
        assert str(c_day.id) not in ids


@pytest.mark.django_db
class TestSubstituteAssignmentAPI:
    def test_create_and_delete_substitute_assignment(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        from apps.academics.models import SubstituteAssignment
        from apps.staff.models import Staff

        cls = ClassLevel.objects.create(
            institution=institution, name="Class 9", code="c09", order=9
        )
        sec = Section.objects.create(
            institution=institution,
            class_level=cls,
            shift=shift,
            session=session,
            name="Padma",
        )
        sub = Subject.objects.create(institution=institution, name_en="Physics", code="PHY101")
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="1st Period",
            order=1,
            start_time=time(8, 0),
            end_time=time(8, 45),
            is_break=False,
        )
        orig_teacher = Staff.objects.create(
            institution=institution,
            employee_id="TCH-001",
            phone="+8801700000001",
            full_name_en="Original Teacher",
            dob=date(1985, 1, 1),
            joining_date=date(2015, 1, 1),
        )
        sub_teacher = Staff.objects.create(
            institution=institution,
            employee_id="TCH-002",
            phone="+8801700000002",
            full_name_en="Cover Teacher",
            dob=date(1990, 5, 5),
            joining_date=date(2020, 1, 1),
        )

        # 2026-11-18 is Wednesday -> NCTB weekday: (Wednesday(2) + 2) % 7 = 4
        slot = RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            period=period,
            subject=sub,
            weekday=4,
            teacher_staff=orig_teacher,
        )

        client = api_client_as(admin_user)
        payload = {
            "routine_slot": str(slot.id),
            "slot_date": "2026-11-18",
            "teacher": str(sub_teacher.id),
            "reason": "Medical Leave",
        }
        res = client.post("/api/v1/academics/substitutes/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.data
        assert data["substitute_teacher_name"] == "Cover Teacher"
        assert data["original_teacher_name"] == "Original Teacher"
        assert data["class_level_name"] == "Class 9"
        assert data["section_name"] == "Padma"
        assert data["period_name"] == "1st Period"
        assert data["subject_name_en"] == "Physics"
        assert data["reason"] == "Medical Leave"
        sub_id = data["id"]

        # Delete
        del_res = client.delete(f"/api/v1/academics/substitutes/{sub_id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT
        assert not SubstituteAssignment.objects.filter(id=sub_id).exists()

    def test_substitute_rejects_same_teacher_and_mismatched_weekday(
        self,
        institution: Institution,
        admin_user: User,
        shift: Shift,
        session: AcademicSession,
    ) -> None:
        from apps.staff.models import Staff

        cls = ClassLevel.objects.create(
            institution=institution, name="Class 10", code="c10", order=10
        )
        sec = Section.objects.create(
            institution=institution,
            class_level=cls,
            shift=shift,
            session=session,
            name="Meghna",
        )
        sub = Subject.objects.create(institution=institution, name_en="Math", code="MTH101")
        period = Period.objects.create(
            institution=institution,
            shift=shift,
            name="2nd Period",
            order=2,
            start_time=time(9, 0),
            end_time=time(9, 45),
            is_break=False,
        )
        orig_teacher = Staff.objects.create(
            institution=institution,
            employee_id="TCH-003",
            phone="+8801700000003",
            full_name_en="Math Teacher",
            dob=date(1985, 1, 1),
            joining_date=date(2015, 1, 1),
        )

        # Slot is on Wednesday (4)
        slot = RoutineSlot.objects.create(
            institution=institution,
            section=sec,
            period=period,
            subject=sub,
            weekday=4,
            teacher_staff=orig_teacher,
        )

        client = api_client_as(admin_user)

        # 1. Attempt assigning original teacher as substitute
        res1 = client.post(
            "/api/v1/academics/substitutes/",
            {
                "routine_slot": str(slot.id),
                "slot_date": "2026-11-18",
                "teacher": str(orig_teacher.id),
                "reason": "Self cover",
            },
            format="json",
        )
        assert res1.status_code == status.HTTP_400_BAD_REQUEST

        # 2. Attempt assigning for mismatched date (2026-11-17 is Tuesday = 3, but slot is Wednesday = 4)
        sub_teacher = Staff.objects.create(
            institution=institution,
            employee_id="TCH-004",
            phone="+8801700000004",
            full_name_en="Other Teacher",
            dob=date(1992, 1, 1),
            joining_date=date(2021, 1, 1),
        )
        res2 = client.post(
            "/api/v1/academics/substitutes/",
            {
                "routine_slot": str(slot.id),
                "slot_date": "2026-11-17",
                "teacher": str(sub_teacher.id),
                "reason": "Date mismatch",
            },
            format="json",
        )
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        details = res2.data.get("details", res2.data)
        assert "slot_date" in details
