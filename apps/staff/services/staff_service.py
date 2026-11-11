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


def create_portal_user_for_staff(staff: Staff) -> tuple[User, str]:
    """Provision a login account for the staff member and send access credentials via SMS."""
    temp_password = secrets.token_urlsafe(8)

    with transaction.atomic():
        if staff.user:
            user = staff.user
            user.set_password(temp_password)
            user.save(update_fields=["password"])
        else:
            user_type = (
                UserType.TEACHER if staff.staff_type == StaffType.TEACHER else UserType.STAFF
            )
            user, _ = User.objects.get_or_create(
                phone=staff.phone,
                institution=staff.institution,
                defaults={
                    "username": staff.employee_id,
                    "full_name": staff.full_name_en[:150],
                    "email": staff.email,
                    "user_type": user_type,
                },
            )
            user.set_password(temp_password)
            user.save(update_fields=["password"])

            staff.user = user
            staff.save(update_fields=["user"])

        # Determine appropriate role
        role_code = "teacher" if staff.staff_type == StaffType.TEACHER else "staff"
        role_name = "Teacher" if staff.staff_type == StaffType.TEACHER else "Staff"
        role, _ = Role.objects.get_or_create(
            institution=staff.institution,
            code=role_code,
            defaults={"name": role_name},
        )
        # Grant basic view permissions
        for codename in ["view_student", "view_subject", "view_routineslot"]:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                role.permissions.add(perm)

        UserRole.objects.get_or_create(user=user, role=role)

    # Deliver SMS
    inst_name = getattr(staff.institution, "name_en", "School")
    msg = (
        f"Your {inst_name} Staff Account is ready. "
        f"Login: {staff.phone} | Password: {temp_password}"
    )
    try:
        get_sms_service().send_sms(staff.phone, msg)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to dispatch staff credentials SMS: %s", exc)

    return user, temp_password
