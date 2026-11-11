"""Guardian management service layer."""

import logging
import secrets
from typing import Any

from django.contrib.auth.models import Permission
from django.db import transaction

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.services.sms import get_sms_service
from apps.core.utils.phone import normalize_bd_phone
from apps.guardians.models import Family, Guardian, GuardianRelation, StudentGuardian
from apps.institutions.models import Institution
from apps.students.models import Student

logger = logging.getLogger(__name__)


def create_or_update_guardian(
    institution: Institution,
    phone: str,
    name_en: str,
    name_bn: str = "",
    relation_default: str = GuardianRelation.FATHER,
    alt_phone: str = "",
    email: str = "",
    nid: str = "",
    occupation: str = "",
    annual_income: Any = None,
    present_address: str = "",
    permanent_address: str = "",
    photo: Any = None,
    is_emergency_contact: bool = False,
    family: Family | None = None,
) -> Guardian:
    """Create a new guardian or update an existing guardian matching the normalized phone within the institution."""
    normalized_phone = normalize_bd_phone(phone)
    normalized_alt = normalize_bd_phone(alt_phone) if alt_phone else ""

    guardian, created = Guardian.objects.get_or_create(
        institution=institution,
        phone=normalized_phone,
        defaults={
            "name_en": name_en,
            "name_bn": name_bn,
            "relation_default": relation_default,
            "alt_phone": normalized_alt,
            "email": email,
            "nid": nid,
            "occupation": occupation,
            "annual_income": annual_income,
            "present_address": present_address,
            "permanent_address": permanent_address,
            "photo": photo,
            "is_emergency_contact": is_emergency_contact,
            "family": family,
        },
    )

    if not created:
        updates: dict[str, Any] = {
            "name_en": name_en or guardian.name_en,
            "name_bn": name_bn or guardian.name_bn,
            "relation_default": relation_default or guardian.relation_default,
            "alt_phone": normalized_alt or guardian.alt_phone,
            "email": email or guardian.email,
            "nid": nid or guardian.nid,
            "occupation": occupation or guardian.occupation,
            "present_address": present_address or guardian.present_address,
            "permanent_address": permanent_address or guardian.permanent_address,
        }
        if annual_income is not None:
            updates["annual_income"] = annual_income
        if photo:
            updates["photo"] = photo
        if is_emergency_contact:
            updates["is_emergency_contact"] = True
        if family:
            updates["family"] = family

        for attr, val in updates.items():
            setattr(guardian, attr, val)
        guardian.save()

    return guardian


def create_portal_user_for_guardian(
    guardian: Guardian,
) -> tuple[User, str]:
    """Create or link a user account for the guardian and send access credentials via SMS."""
    temp_password = secrets.token_urlsafe(8)

    with transaction.atomic():
        if guardian.user:
            user = guardian.user
            user.set_password(temp_password)
            user.save(update_fields=["password"])
        else:
            user, created = User.objects.get_or_create(
                phone=guardian.phone,
                institution=guardian.institution,
                defaults={
                    "username": guardian.phone,
                    "full_name": guardian.name_en[:150],
                    "email": guardian.email,
                    "user_type": UserType.GUARDIAN,
                },
            )
            user.set_password(temp_password)
            user.save(update_fields=["password"])

            guardian.user = user
            guardian.save(update_fields=["user"])

        # Ensure Guardian role assignment
        role, _ = Role.objects.get_or_create(
            institution=guardian.institution,
            code="guardian",
            defaults={"name": "Guardian"},
        )
        # Assign basic permissions for guardian if available
        perm_view = Permission.objects.filter(codename="view_student").first()
        if perm_view:
            role.permissions.add(perm_view)

        UserRole.objects.get_or_create(user=user, role=role)

    # Deliver credentials via SMS
    institution_name = getattr(guardian.institution, "name_en", "School")
    message = (
        f"Welcome to {institution_name} Parent Portal! "
        f"Login: {guardian.phone} | Password: {temp_password}"
    )
    try:
        sms_service = get_sms_service()
        sms_service.send_sms(guardian.phone, message)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to send portal credentials SMS to %s: %s", guardian.phone, exc)

    return user, temp_password


def link_student_guardian(
    institution: Institution,
    student: Student,
    guardian: Guardian,
    relation: str = GuardianRelation.FATHER,
    is_primary: bool = False,
    can_pickup: bool = True,
    receives_sms: bool = True,
    financial_responsible: bool = False,
) -> StudentGuardian:
    """Link a student to a guardian, enforcing primary contact invariants and emergency details sync."""
    if student.institution_id != institution.id or guardian.institution_id != institution.id:
        raise ValueError("Student and Guardian must belong to the specified institution.")

    with transaction.atomic():
        if is_primary:
            StudentGuardian.objects.filter(
                student=student,
                is_primary=True,
            ).update(is_primary=False)

            student.emergency_contact_name = guardian.name_en
            student.emergency_contact_phone = guardian.phone
            student.save(update_fields=["emergency_contact_name", "emergency_contact_phone"])

        sg, _ = StudentGuardian.objects.update_or_create(
            student=student,
            guardian=guardian,
            defaults={
                "institution": institution,
                "relation": relation,
                "is_primary": is_primary,
                "can_pickup": can_pickup,
                "receives_sms": receives_sms,
                "financial_responsible": financial_responsible,
            },
        )

    return sg


def unlink_student_guardian(
    institution: Institution,
    student: Student,
    guardian: Guardian,
) -> bool:
    """Unlink a guardian from a student. If primary was removed, promote the next available guardian."""
    with transaction.atomic():
        link = StudentGuardian.objects.filter(
            institution=institution,
            student=student,
            guardian=guardian,
        ).first()

        if not link:
            return False

        was_primary = link.is_primary
        link.delete()

        if was_primary:
            next_link = (
                StudentGuardian.objects.filter(
                    institution=institution,
                    student=student,
                )
                .order_by("-created_at")
                .first()
            )
            if next_link:
                next_link.is_primary = True
                next_link.save(update_fields=["is_primary"])
                student.emergency_contact_name = next_link.guardian.name_en
                student.emergency_contact_phone = next_link.guardian.phone
                student.save(update_fields=["emergency_contact_name", "emergency_contact_phone"])
            else:
                student.emergency_contact_name = ""
                student.emergency_contact_phone = ""
                student.save(update_fields=["emergency_contact_name", "emergency_contact_phone"])

        return True


def merge_duplicate_guardians(
    institution: Institution,
    primary_guardian: Guardian,
    duplicate_guardians: list[Guardian],
) -> Guardian:
    """Merge multiple duplicate guardian records into a single authoritative primary guardian."""
    with transaction.atomic():
        for dup in duplicate_guardians:
            if dup.id == primary_guardian.id:
                continue

            for sg in dup.student_relations.all():
                existing = StudentGuardian.objects.filter(
                    student=sg.student,
                    guardian=primary_guardian,
                ).first()

                if existing:
                    existing.is_primary = existing.is_primary or sg.is_primary
                    existing.can_pickup = existing.can_pickup or sg.can_pickup
                    existing.receives_sms = existing.receives_sms or sg.receives_sms
                    existing.financial_responsible = (
                        existing.financial_responsible or sg.financial_responsible
                    )
                    existing.save()
                    sg.delete()
                else:
                    sg.guardian = primary_guardian
                    sg.save(update_fields=["guardian"])

            if not primary_guardian.user and dup.user:
                primary_guardian.user = dup.user
                dup.user = None
                dup.save(update_fields=["user"])

            if not primary_guardian.nid and dup.nid:
                primary_guardian.nid = dup.nid
            if not primary_guardian.email and dup.email:
                primary_guardian.email = dup.email
            if not primary_guardian.name_bn and dup.name_bn:
                primary_guardian.name_bn = dup.name_bn

            dup.delete()

        primary_guardian.save()

    return primary_guardian
