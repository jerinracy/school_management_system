"""Curriculum syllabus tracking and progress summary services."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassLevel, Subject
from apps.homework.models import SyllabusStatus, SyllabusTopic
from apps.institutions.models import AcademicSession, Institution


@transaction.atomic
def update_syllabus_topic_progress(
    topic: SyllabusTopic,
    completion_percentage: int,
    status: str | None = None,
) -> SyllabusTopic:
    """Update completion percentage and derive synchronized SyllabusStatus."""
    if completion_percentage < 0 or completion_percentage > 100:
        raise ValidationError("Completion percentage must be between 0 and 100.")

    derived_status: str
    if status is None:
        if completion_percentage == 0:
            derived_status = SyllabusStatus.NOT_STARTED
        elif completion_percentage >= 100:
            derived_status = SyllabusStatus.COMPLETED
        else:
            derived_status = SyllabusStatus.IN_PROGRESS
    else:
        derived_status = status
        if derived_status == SyllabusStatus.COMPLETED and completion_percentage < 100:
            completion_percentage = 100

    topic.completion_percentage = completion_percentage
    topic.status = derived_status
    topic.completed_at = timezone.now() if derived_status == SyllabusStatus.COMPLETED else None
    topic.save(update_fields=["completion_percentage", "status", "completed_at", "updated_at"])
    return topic


def get_subject_syllabus_summary(
    institution: Institution,
    session: AcademicSession,
    class_level: ClassLevel,
    subject: Subject | None = None,
) -> dict[str, Any]:
    """Compute syllabus completion summary for a class and optional subject."""
    qs = SyllabusTopic.objects.filter(
        institution=institution,
        session=session,
        class_level=class_level,
        is_deleted=False,
    )
    if subject is not None:
        qs = qs.filter(subject=subject)

    topics = list(qs)
    total = len(topics)
    if total == 0:
        return {
            "total_topics": 0,
            "completed_topics": 0,
            "in_progress_topics": 0,
            "average_completion_percentage": 0,
        }

    completed = sum(1 for t in topics if t.status == SyllabusStatus.COMPLETED)
    in_progress = sum(1 for t in topics if t.status == SyllabusStatus.IN_PROGRESS)
    avg_pct = round(sum(t.completion_percentage for t in topics) / total)
    return {
        "total_topics": total,
        "completed_topics": completed,
        "in_progress_topics": in_progress,
        "average_completion_percentage": avg_pct,
    }
