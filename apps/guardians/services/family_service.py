"""Family and sibling discovery service layer."""

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.guardians.models import Family, Guardian, StudentGuardian
from apps.institutions.models import Institution
from apps.students.models import Student


def generate_family_code(institution: Institution) -> str:
    """Generate a unique family code per institution formatted as FAM-{YEAR}-{SEQUENCE}."""
    year = timezone.now().year
    prefix = f"FAM-{year}-"

    count = Family.all_objects.filter(
        institution=institution,
        family_code__startswith=prefix,
    ).count()

    seq = count + 1
    while True:
        code = f"{prefix}{seq:05d}"
        if not Family.all_objects.filter(institution=institution, family_code=code).exists():
            return code
        seq += 1


def _suggest_by_guardian(
    institution: Institution,
    guardian: Guardian,
    seen_student_ids: set[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    already_linked_ids = set(guardian.student_relations.values_list("student_id", flat=True))

    phone_matches = (
        Student.objects.filter(
            institution=institution,
            emergency_contact_phone=guardian.phone,
        )
        .exclude(id__in=already_linked_ids)
        .distinct()
    )
    for s in phone_matches:
        if str(s.id) not in seen_student_ids:
            seen_student_ids.add(str(s.id))
            candidates.append(
                {
                    "student_id": str(s.id),
                    "student_name": s.name_en,
                    "student_id_code": s.student_id,
                    "match_reason": "Matching emergency contact phone",
                    "matched_value": guardian.phone,
                }
            )

    if guardian.nid:
        same_nid_guardians = Guardian.objects.filter(
            institution=institution,
            nid=guardian.nid,
        ).exclude(id=guardian.id)

        for g in same_nid_guardians:
            for sg in g.student_relations.all():
                s = sg.student
                if s.id not in already_linked_ids and str(s.id) not in seen_student_ids:
                    seen_student_ids.add(str(s.id))
                    candidates.append(
                        {
                            "student_id": str(s.id),
                            "student_name": s.name_en,
                            "student_id_code": s.student_id,
                            "match_reason": "Matching guardian National ID (NID)",
                            "matched_value": guardian.nid,
                        }
                    )
    return candidates


def _suggest_by_student(
    institution: Institution,
    student: Student,
    seen_student_ids: set[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    if student.emergency_contact_phone:
        same_contact_students = (
            Student.objects.filter(
                institution=institution,
                emergency_contact_phone=student.emergency_contact_phone,
            )
            .exclude(id=student.id)
            .distinct()
        )
        for s in same_contact_students:
            if str(s.id) not in seen_student_ids:
                seen_student_ids.add(str(s.id))
                candidates.append(
                    {
                        "student_id": str(s.id),
                        "student_name": s.name_en,
                        "student_id_code": s.student_id,
                        "match_reason": "Shared emergency contact phone",
                        "matched_value": student.emergency_contact_phone,
                    }
                )

    guardian_phones = list(
        StudentGuardian.objects.filter(student=student).values_list("guardian__phone", flat=True)
    )
    if guardian_phones:
        co_guardians = StudentGuardian.objects.filter(
            institution=institution,
            guardian__phone__in=guardian_phones,
        ).exclude(student=student)
        for sg in co_guardians:
            s = sg.student
            if str(s.id) not in seen_student_ids:
                seen_student_ids.add(str(s.id))
                candidates.append(
                    {
                        "student_id": str(s.id),
                        "student_name": s.name_en,
                        "student_id_code": s.student_id,
                        "match_reason": f"Shared guardian phone ({sg.guardian.phone})",
                        "matched_value": sg.guardian.phone,
                    }
                )
    return candidates


def suggest_siblings(
    institution: Institution,
    guardian: Guardian | None = None,
    student: Student | None = None,
) -> list[dict[str, Any]]:
    """Discover potential sibling candidates across the institution based on phone, NID, or contact matching."""
    seen_student_ids: set[str] = set()

    if guardian:
        return _suggest_by_guardian(institution, guardian, seen_student_ids)
    if student:
        return _suggest_by_student(institution, student, seen_student_ids)

    return []


def link_siblings_to_family(
    institution: Institution,
    family: Family,
    student_ids: list[str],
) -> Family:
    """Associate guardians of specified students into the specified Family unit."""
    with transaction.atomic():
        guardians = Guardian.objects.filter(
            institution=institution,
            student_relations__student_id__in=student_ids,
        ).distinct()

        for g in guardians:
            g.family = family
            g.save(update_fields=["family"])

    return family
