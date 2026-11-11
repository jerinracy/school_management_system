"""Bulk promotion workflow service."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import User
from apps.institutions.models import AcademicSession
from apps.students.models import (
    EnrollmentStatus,
    PromotionAction,
    PromotionBatch,
    PromotionBatchStatus,
    PromotionItem,
    StudentEnrollment,
)


@transaction.atomic
def preview_promotion(
    institution_id: UUID | str,
    from_session_id: UUID | str,
    to_session_id: UUID | str,
    from_class_id: UUID | str,
    to_class_id: UUID | str,
    default_target_section_id: UUID | str | None = None,
    passing_gpa_threshold: Decimal = Decimal("2.00"),
    student_overrides: list[dict[str, Any]] | None = None,
) -> PromotionBatch:
    """Simulate and generate a promotion preview batch.

    Creates PromotionBatch and PromotionItem records for administrative review.
    """
    from_session = AcademicSession.objects.get(id=from_session_id, institution_id=institution_id)
    to_session = AcademicSession.objects.get(id=to_session_id, institution_id=institution_id)
    from_class = ClassLevel.objects.get(id=from_class_id, institution_id=institution_id)
    to_class = ClassLevel.objects.get(id=to_class_id, institution_id=institution_id)

    # Get target sections
    target_sections = list(
        Section.objects.filter(
            institution_id=institution_id,
            session=to_session,
            class_level=to_class,
        )
    )
    if not target_sections:
        raise ValidationError(
            f"No sections exist in target class '{to_class.name}' for target session '{to_session.name}'."
        )

    fallback_section = target_sections[0]
    if default_target_section_id:
        fallback_section = next(
            (s for s in target_sections if str(s.id) == str(default_target_section_id)),
            target_sections[0],
        )

    # Existing enrollments in source class/session
    enrollments = (
        StudentEnrollment.objects.filter(
            institution_id=institution_id,
            session=from_session,
            class_level=from_class,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("student", "section")
        .order_by("roll_no")
    )

    batch = PromotionBatch.objects.create(
        institution_id=institution_id,
        from_session=from_session,
        to_session=to_session,
        from_class=from_class,
        to_class=to_class,
        status=PromotionBatchStatus.PREVIEWED,
        total_students=enrollments.count(),
    )

    override_map: dict[str, dict[str, Any]] = {}
    if student_overrides:
        override_map = {str(o["student_id"]): o for o in student_overrides}

    promoted_count = 0
    retained_count = 0

    section_roll_counters: dict[UUID, int] = {s.id: 0 for s in target_sections}

    for enrollment in enrollments:
        student_id_str = str(enrollment.student.id)
        override = override_map.get(student_id_str, {})

        gpa = override.get("gpa")
        action = override.get("action")
        if not action:
            if gpa is not None and Decimal(str(gpa)) < passing_gpa_threshold:
                action = PromotionAction.REPEAT
            else:
                action = PromotionAction.PROMOTE

        if action == PromotionAction.PROMOTE:
            promoted_count += 1
            assigned_section = fallback_section
            if "target_section_id" in override:
                target_sec_id = override["target_section_id"]
                assigned_section = next(
                    (s for s in target_sections if str(s.id) == str(target_sec_id)),
                    fallback_section,
                )
            target_class_obj = to_class
        else:
            retained_count += 1
            # In case of repeat, retain in source class
            target_class_obj = from_class
            assigned_section = enrollment.section

        section_roll_counters[assigned_section.id] = (
            section_roll_counters.get(assigned_section.id, 0) + 1
        )
        assigned_roll = override.get("target_roll_no", section_roll_counters[assigned_section.id])

        PromotionItem.objects.create(
            institution_id=institution_id,
            batch=batch,
            student=enrollment.student,
            from_enrollment=enrollment,
            target_class=target_class_obj,
            target_section=assigned_section,
            target_roll_no=assigned_roll,
            action=action,
            gpa=Decimal(str(gpa)) if gpa is not None else None,
            remarks=override.get("remarks", ""),
        )

    batch.promoted_count = promoted_count
    batch.retained_count = retained_count
    batch.save(update_fields=["promoted_count", "retained_count"])

    return batch


@transaction.atomic
def apply_promotion(batch_id: UUID | str, applied_by: User | None = None) -> PromotionBatch:
    """Atomically commit a promotion preview batch."""
    batch = (
        PromotionBatch.objects.select_related("from_session", "to_session")
        .select_for_update()
        .get(id=batch_id)
    )

    if batch.status != PromotionBatchStatus.PREVIEWED:
        raise ValidationError(
            f"Promotion batch status must be PREVIEWED to apply (currently {batch.status})."
        )

    today = timezone.localdate()
    items = batch.items.select_related(
        "student", "from_enrollment", "target_class", "target_section"
    )

    for item in items:
        # Mark previous enrollment
        old_enrollment = item.from_enrollment
        if item.action == PromotionAction.PROMOTE:
            old_enrollment.status = EnrollmentStatus.PROMOTED
        elif item.action == PromotionAction.REPEAT:
            old_enrollment.status = EnrollmentStatus.REPEATED
        elif item.action == PromotionAction.WITHDRAW:
            old_enrollment.status = EnrollmentStatus.DROPPED
        old_enrollment.save(update_fields=["status"])

        if item.action in [PromotionAction.PROMOTE, PromotionAction.REPEAT]:
            new_enrollment = StudentEnrollment.objects.create(
                institution=batch.institution,
                student=item.student,
                session=batch.to_session,
                class_level=item.target_class,
                section=item.target_section,
                shift=item.target_section.shift,
                roll_no=item.target_roll_no,
                enrollment_date=today,
                status=EnrollmentStatus.ACTIVE,
            )
            item.to_enrollment = new_enrollment
            item.save(update_fields=["to_enrollment"])

    batch.status = PromotionBatchStatus.APPLIED
    batch.applied_at = timezone.now()
    batch.applied_by = applied_by
    batch.save(update_fields=["status", "applied_at", "applied_by"])

    return batch


@transaction.atomic
def rollback_promotion(batch_id: UUID | str, user: User | None = None) -> PromotionBatch:
    """Roll back an applied promotion batch."""
    batch = (
        PromotionBatch.objects.select_related("from_session", "to_session")
        .select_for_update()
        .get(id=batch_id)
    )

    if batch.status != PromotionBatchStatus.APPLIED:
        raise ValidationError(
            f"Only APPLIED promotion batches can be rolled back (currently {batch.status})."
        )

    items = batch.items.select_related("from_enrollment", "to_enrollment")
    for item in items:
        # Delete created target enrollment
        if item.to_enrollment:
            item.to_enrollment.delete()
            item.to_enrollment = None
            item.save(update_fields=["to_enrollment"])

        # Restore source enrollment to active
        old_enrollment = item.from_enrollment
        old_enrollment.status = EnrollmentStatus.ACTIVE
        old_enrollment.save(update_fields=["status"])

    batch.status = PromotionBatchStatus.ROLLED_BACK
    batch.save(update_fields=["status"])

    return batch
