"""Student portal and mobile app account provisioning service."""

import logging
import secrets

from django.contrib.auth.models import Permission
from django.db import transaction

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.services.sms import get_sms_service
from apps.core.utils.phone import normalize_bd_phone, validate_bd_phone
from apps.students.models import Student

logger = logging.getLogger(__name__)


def create_portal_user_for_student(
    student: Student,
    phone: str | None = None,
    password: str | None = None,
) -> tuple[User, str]:
    """Provision or update a login user account for a student for mobile app & portal access."""
    final_password = password.strip() if password and password.strip() else secrets.token_urlsafe(8)

    raw_phone = phone.strip() if phone and phone.strip() else (student.phone or "")
    if raw_phone and validate_bd_phone(raw_phone):
        target_phone = normalize_bd_phone(raw_phone)
    else:
        target_phone = raw_phone

    if target_phone and student.phone != target_phone:
        student.phone = target_phone
        student.save(update_fields=["phone"])

    chosen_username = target_phone or f"stu_{student.student_id}"

    with transaction.atomic():
        if student.user:
            user = student.user
            if target_phone and user.phone != target_phone:
                user.phone = target_phone
            if chosen_username and user.username != chosen_username:
                user.username = chosen_username
            user.set_password(final_password)
            user.must_change_password = False
            user.save()
        else:
            lookup_kwargs = {"institution": student.institution}
            if target_phone:
                lookup_kwargs["phone"] = target_phone
            else:
                lookup_kwargs["username"] = chosen_username

            user, _ = User.objects.get_or_create(
                **lookup_kwargs,
                defaults={
                    "username": chosen_username,
                    "phone": target_phone or None,
                    "full_name": student.name_en[:150],
                    "user_type": UserType.STUDENT,
                },
            )
            user.set_password(final_password)
            user.must_change_password = False
            user.institution = student.institution
            user.save()

            student.user = user
            student.save(update_fields=["user"])

        # Ensure student role assignment
        role, _ = Role.objects.get_or_create(
            institution=student.institution,
            code="student",
            defaults={"name": "Student"},
        )

        student_perms = [
            "view_student",
            "view_homework",
            "view_routineslot",
            "view_result",
            "view_attendance",
            "view_invoice",
            "view_notice",
        ]
        for codename in student_perms:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                role.permissions.add(perm)

        UserRole.objects.get_or_create(user=user, role=role)

    # Send SMS credentials if mobile phone is valid
    if target_phone and validate_bd_phone(target_phone):
        institution_name = getattr(student.institution, "name_en", "School")
        message = (
            f"Welcome to {institution_name} Student Portal! "
            f"Login: {target_phone} | Password: {final_password}"
        )
        try:
            sms_service = get_sms_service()
            sms_service.send_sms(target_phone, message)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to dispatch student portal SMS to %s: %s", target_phone, exc)

    return user, final_password
