"""Staff provisioning, onboarding, and portal account services."""

import logging
import secrets
from typing import Any

from django.contrib.auth.models import Permission
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.services.sms import get_sms_service
from apps.core.utils.phone import normalize_bd_phone
from apps.institutions.models import Institution
from apps.staff.models import Department, Designation, Staff, StaffStatus, StaffType

logger = logging.getLogger(__name__)


def generate_employee_id(institution: Institution) -> str:
    """Generate sequential employee ID per institution formatted as EMP-{YEAR}-{SEQUENCE}."""
    year = timezone.now().year
    prefix = f"EMP-{year}-"

    count = Staff.all_objects.filter(
        institution=institution,
        employee_id__startswith=prefix,
    ).count()

    seq = count + 1
    while True:
        emp_id = f"{prefix}{seq:05d}"
        if not Staff.all_objects.filter(institution=institution, employee_id=emp_id).exists():
            return emp_id
        seq += 1


def create_staff(
    institution: Institution,
    full_name_en: str,
    phone: str,
    gender: str,
    dob: Any,
    joining_date: Any,
    employee_id: str = "",
    full_name_bn: str = "",
    staff_type: str = StaffType.TEACHER,
    department: Department | None = None,
    designation: Designation | None = None,
    alt_phone: str = "",
    email: str = "",
    nid: str = "",
    blood_group: str = "",
    present_address: str = "",
    permanent_address: str = "",
    photo: Any = None,
    status: str = StaffStatus.ACTIVE,
    is_mpo: bool = False,
    mpo_index_number: str = "",
    tin_number: str = "",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    emergency_contact_relation: str = "",
) -> Staff:
    """Create a new staff member with normalized phone and sequential employee ID."""
    normalized_phone = normalize_bd_phone(phone)
    normalized_alt = normalize_bd_phone(alt_phone) if alt_phone else ""

    if not employee_id:
        employee_id = generate_employee_id(institution)

    staff = Staff.objects.create(
        institution=institution,
        employee_id=employee_id,
        full_name_en=full_name_en,
        full_name_bn=full_name_bn,
        staff_type=staff_type,
        department=department,
        designation=designation,
        gender=gender,
        dob=dob,
        phone=normalized_phone,
        alt_phone=normalized_alt,
        email=email,
        nid=nid,
        blood_group=blood_group,
        present_address=present_address,
        permanent_address=permanent_address,
        photo=photo,
        joining_date=joining_date,
        status=status,
        is_mpo=is_mpo,
        mpo_index_number=mpo_index_number,
        tin_number=tin_number,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relation=emergency_contact_relation,
    )
    return staff


def _resolve_staff_role_and_user_type(staff_type: str) -> tuple[str, bool, bool, str, str]:
    """Helper to map staff_type to UserType and Role definitions."""
    if staff_type == StaffType.SUPERADMIN:
        return UserType.SUPERADMIN, True, True, "superadmin", "Super Admin"
    if staff_type == StaffType.ADMIN:
        return UserType.ADMIN, False, True, "admin", "Institution Admin"
    if staff_type == StaffType.TEACHER:
        return UserType.TEACHER, False, False, "teacher", "Teacher"
    return UserType.STAFF, False, False, "staff", "Staff"


def create_portal_user_for_staff(
    staff: Staff,
    username: str | None = None,
    password: str | None = None,
) -> tuple[User, str]:
    """Provision a login account for the staff member and send access credentials via SMS."""
    final_password = password.strip() if password and password.strip() else secrets.token_urlsafe(8)
    chosen_username = (
        username.strip() if username and username.strip() else (staff.employee_id or staff.phone)
    )
    user_type, is_su, is_st, role_code, role_name = _resolve_staff_role_and_user_type(
        staff.staff_type
    )

    with transaction.atomic():
        if staff.user:
            user = staff.user
            if chosen_username and user.username != chosen_username:
                user.username = chosen_username
            user.set_password(final_password)
            user.institution = staff.institution
            user.save()
        else:
            user, _ = User.objects.get_or_create(
                phone=staff.phone,
                institution=staff.institution,
                defaults={
                    "username": chosen_username,
                    "full_name": staff.full_name_en[:150],
                    "email": staff.email,
                    "user_type": user_type,
                    "is_superuser": is_su,
                    "is_staff": is_st,
                },
            )
            if user.username != chosen_username and chosen_username:
                user.username = chosen_username
            user.set_password(final_password)
            user.institution = staff.institution
            user.save()

            staff.user = user
            staff.save(update_fields=["user"])

        role, _ = Role.objects.get_or_create(
            institution=staff.institution,
            code=role_code,
            defaults={"name": role_name},
        )
        for codename in ["view_student", "view_subject", "view_routineslot"]:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                role.permissions.add(perm)

        UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={"branch": getattr(staff, "branch", None)},
        )

    # Deliver SMS
    inst_name = getattr(staff.institution, "name_en", "School")
    msg = (
        f"Your {inst_name} Staff Account is ready. "
        f"Login: {user.username} | Password: {final_password}"
    )
    try:
        get_sms_service().send_sms(staff.phone, msg)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to dispatch staff credentials SMS: %s", exc)

    return user, final_password
