"""API integration tests for Staff, HR, and Leave endpoints."""

from datetime import date

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import Department, Designation, LeaveType, Staff, StaffType


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="134567",
    )


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Rajshahi Model School",
        name_bn="রাজশাহী মডেল স্কুল",
        eiin="765432",
    )


@pytest.fixture
def session(db, institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="Academic Year 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def staff_permissions(db):
    ct_staff = ContentType.objects.get_for_model(Staff)
    p_view, _ = Permission.objects.get_or_create(
        codename="view",
        content_type=ct_staff,
        defaults={"name": "Can view staff"},
    )
    p_manage, _ = Permission.objects.get_or_create(
        codename="manage",
        content_type=ct_staff,
        defaults={"name": "Can manage staff"},
    )
    p_apply, _ = Permission.objects.get_or_create(
        codename="apply",
        content_type=ct_staff,
        defaults={"name": "Can apply leave"},
    )
    p_approve, _ = Permission.objects.get_or_create(
        codename="approve",
        content_type=ct_staff,
        defaults={"name": "Can approve leave"},
    )
    return p_view, p_manage, p_apply, p_approve


@pytest.fixture
def admin_user(db, institution, staff_permissions) -> User:
    user = make_user(
        username="hr_admin",
        institution=institution,
        user_type=UserType.STAFF,
        phone="+8801700000001",
    )
    role, _ = Role.objects.get_or_create(institution=institution, code="hr_admin")
    p_view, p_manage, p_apply, p_approve = staff_permissions
    role.permissions.add(p_view, p_manage, p_apply, p_approve)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def client_for():
    def _create(user: User) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _create


@pytest.mark.django_db
class TestStaffAPI:
    def test_staff_crud(self, client_for, admin_user, institution):
        client = client_for(admin_user)

        dept = Department.objects.create(institution=institution, name="English")
        desig = Designation.objects.create(
            institution=institution, title="Assistant Teacher", rank_order=3
        )

        # 1. Create Staff
        payload = {
            "full_name_en": "Kazi Nazrul",
            "full_name_bn": "কাজী নজরুল",
            "phone": "01722334455",
            "gender": "male",
            "dob": "1988-05-24",
            "joining_date": "2020-01-01",
            "staff_type": "teacher",
            "department": str(dept.id),
            "designation": str(desig.id),
            "is_mpo": True,
            "mpo_index_number": "MPO-554433",
        }
        res = client.post("/api/v1/staff/staff/", payload)
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        staff_id = data["id"]
        assert data["employee_id"].startswith("EMP-")
        assert data["phone"] == "+8801722334455"

        # 2. List Staff
        list_res = client.get("/api/v1/staff/staff/")
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()["results"]) == 1

        # 3. Retrieve Staff
        ret_res = client.get(f"/api/v1/staff/staff/{staff_id}/")
        assert ret_res.status_code == status.HTTP_200_OK
        assert ret_res.json()["full_name_en"] == "Kazi Nazrul"

        # 4. Update Staff
        patch_res = client.patch(
            f"/api/v1/staff/staff/{staff_id}/", {"mpo_index_number": "MPO-999999"}
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.json()["mpo_index_number"] == "MPO-999999"

    def test_create_portal_account(self, client_for, admin_user, institution):
        client = client_for(admin_user)
        staff = Staff.objects.create(
            institution=institution,
            employee_id="EMP-2026-00099",
            full_name_en="Teacher One",
            phone="+8801733445566",
            gender="female",
            dob=date(1990, 1, 1),
            joining_date=date(2021, 1, 1),
            staff_type=StaffType.TEACHER,
        )

        res = client.post(f"/api/v1/staff/staff/{staff.id}/create-portal-account/")
        assert res.status_code == status.HTTP_200_OK
        assert "user_id" in res.json()

        staff.refresh_from_db()
        assert staff.user is not None
        assert staff.user.phone == "+8801733445566"

    def test_leave_endpoints_flow(self, client_for, admin_user, institution, session):
        client = client_for(admin_user)

        staff = Staff.objects.create(
            institution=institution,
            employee_id="EMP-2026-00050",
            full_name_en="Leave Applicant",
            phone="+8801755667788",
            gender="male",
            dob=date(1987, 8, 12),
            joining_date=date(2019, 1, 1),
            staff_type=StaffType.TEACHER,
            user=admin_user,
        )
        cl = LeaveType.objects.create(
            institution=institution, name="Casual Leave", code="CL", yearly_quota=15
        )

        # 1. Initialize balances
        init_res = client.post(
            "/api/v1/staff/leave-balances/initialize-session/",
            {"session_id": str(session.id)},
        )
        assert init_res.status_code == status.HTTP_200_OK

        # 2. Apply for leave
        apply_payload = {
            "staff_id": str(staff.id),
            "leave_type_id": str(cl.id),
            "session_id": str(session.id),
            "start_date": "2026-03-01",
            "end_date": "2026-03-03",
            "reason": "Personal medical checkup",
        }
        apply_res = client.post("/api/v1/staff/leave-requests/", apply_payload)
        assert apply_res.status_code == status.HTTP_201_CREATED
        leave_id = apply_res.json()["id"]
        assert apply_res.json()["days_count"] == "3.0"

        # 3. Recommend leave
        rec_res = client.post(f"/api/v1/staff/leave-requests/{leave_id}/recommend/")
        assert rec_res.status_code == status.HTTP_200_OK
        assert rec_res.json()["status"] == "recommended"

        # 4. Approve leave
        app_res = client.post(f"/api/v1/staff/leave-requests/{leave_id}/approve/")
        assert app_res.status_code == status.HTTP_200_OK
        assert app_res.json()["status"] == "approved"

    def test_cross_tenant_isolation(self, client_for, admin_user, other_institution):
        other_staff = Staff.objects.create(
            institution=other_institution,
            employee_id="EMP-2026-00001",
            full_name_en="Other School Staff",
            phone="+8801799881122",
            gender="male",
            dob=date(1985, 2, 2),
            joining_date=date(2017, 1, 1),
        )

        client = client_for(admin_user)
        res = client.get(f"/api/v1/staff/staff/{other_staff.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_summary_and_superadmin_isolation(self, client_for, admin_user, institution):
        # Create a regular staff member
        Staff.objects.create(
            institution=institution,
            employee_id="EMP-REG-001",
            full_name_en="Regular Teacher",
            phone="+8801700112233",
            staff_type="teacher",
            gender="female",
            dob=date(1992, 5, 5),
            joining_date=date(2025, 1, 1),
        )

        # Create a superadmin user and staff
        sa_user = User.objects.create(
            username="sa_tester",
            user_type="superadmin",
            is_superuser=True,
            institution=institution,
        )
        sa_staff = Staff.objects.create(
            institution=institution,
            employee_id="EMP-SA-001",
            full_name_en="Superadmin Tester",
            phone="+8801700998877",
            staff_type="superadmin",
            user=sa_user,
            gender="male",
            dob=date(1990, 1, 1),
            joining_date=date(2026, 1, 1),
        )

        # 1. Superadmin calls summary -> gets all 4 categories including superadmin
        sa_client = client_for(sa_user)
        res_sa = sa_client.get("/api/v1/staff/staff/summary/")
        assert res_sa.status_code == status.HTTP_200_OK
        data_sa = res_sa.json()
        assert "superadmin" in data_sa
        assert data_sa["superadmin"] >= 1
        assert "admin" in data_sa
        assert "teacher" in data_sa
        assert "staff" in data_sa

        # 2. Regular admin calls summary -> superadmin count is omitted
        admin_client = client_for(admin_user)
        res_admin = admin_client.get("/api/v1/staff/staff/summary/")
        assert res_admin.status_code == status.HTTP_200_OK
        data_admin = res_admin.json()
        assert "superadmin" not in data_admin
        assert "admin" in data_admin
        assert "teacher" in data_admin
        assert "staff" in data_admin

        # 3. Regular admin calls list -> superadmin staff is excluded from results
        res_list = admin_client.get("/api/v1/staff/staff/")
        assert res_list.status_code == status.HTTP_200_OK
        returned_ids = [item["id"] for item in res_list.json()["results"]]
        assert str(sa_staff.id) not in returned_ids

    def test_create_staff_with_portal_access_and_branch(self, client_for, admin_user, institution):
        from apps.institutions.models import Branch

        branch = Branch.objects.create(
            institution=institution,
            name="North Campus",
            code="NORTH",
        )
        client = client_for(admin_user)
        payload = {
            "full_name_en": "New Admin Officer",
            "phone": "+8801811223344",
            "gender": "male",
            "dob": "1988-03-15",
            "joining_date": "2026-02-01",
            "staff_type": "admin",
            "branch": str(branch.id),
            "give_portal_access": True,
            "portal_username": "admin_officer",
            "portal_password": "NewSecretPass123#",
        }
        res = client.post("/api/v1/staff/staff/", payload)
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert data["full_name_en"] == "New Admin Officer"

        staff = Staff.objects.get(id=data["id"])
        assert staff.branch == branch
        assert staff.user is not None
        assert staff.user.username == "admin_officer"
        assert staff.user.check_password("NewSecretPass123#")
        assert staff.user.institution == institution

    def test_reset_staff_password(self, client_for, admin_user, institution):
        client = client_for(admin_user)
        staff = Staff.objects.create(
            institution=institution,
            employee_id="EMP-2026-00077",
            full_name_en="Password Test Staff",
            phone="+8801999888777",
            gender="male",
            dob=date(1991, 4, 20),
            joining_date=date(2025, 1, 1),
            staff_type=StaffType.SUPPORT,
        )

        # Reset password (creates portal account if none)
        res = client.post(
            f"/api/v1/staff/staff/{staff.id}/reset-password/",
            {"password": "ResetPassword456#"},
        )
        assert res.status_code == status.HTTP_200_OK
        staff.refresh_from_db()
        assert staff.user is not None
        assert staff.user.check_password("ResetPassword456#")
