"""Service to copy academic structure (sections, subject offerings, routines) from previous session."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.academics.models import ClassSubject, RoutineSlot, Section
from apps.institutions.models import AcademicSession


@dataclass
class CopySessionResult:
    source_session_id: str
    target_session_id: str
    dry_run: bool
    sections_count: int = 0
    class_subjects_count: int = 0
    routine_slots_count: int = 0
    skipped_sections_count: int = 0
    skipped_subjects_count: int = 0
    preview: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_session_id": self.source_session_id,
            "target_session_id": self.target_session_id,
            "dry_run": self.dry_run,
            "sections_count": self.sections_count,
            "class_subjects_count": self.class_subjects_count,
            "routine_slots_count": self.routine_slots_count,
            "skipped_sections_count": self.skipped_sections_count,
            "skipped_subjects_count": self.skipped_subjects_count,
            "preview": self.preview,
        }


def _copy_sections(
    institution_id: UUID | str,
    source_session: AcademicSession,
    target_session: AcademicSession,
    preserve_teachers: bool,
    dry_run: bool,
    result: CopySessionResult,
    section_mapping: dict[UUID, Section],
) -> None:
    source_sections = Section.objects.filter(
        institution_id=institution_id,
        session=source_session,
    ).select_related("class_level", "shift")

    existing_sections = {
        (s.class_level_id, s.shift_id, s.name): s
        for s in Section.objects.filter(institution_id=institution_id, session=target_session)
    }

    for sec in source_sections:
        key = (sec.class_level_id, sec.shift_id, sec.name)
        if key in existing_sections:
            result.skipped_sections_count += 1
            section_mapping[sec.id] = existing_sections[key]
            continue

        preview_label = f"{sec.class_level.name} - {sec.name} ({sec.shift.name})"
        result.preview["sections"].append(preview_label)
        result.sections_count += 1

        if not dry_run:
            new_sec = Section.objects.create(
                institution_id=institution_id,
                class_level=sec.class_level,
                shift=sec.shift,
                session=target_session,
                name=sec.name,
                capacity=sec.capacity,
                teacher_user=sec.teacher_user if preserve_teachers else None,
            )
            section_mapping[sec.id] = new_sec


def _copy_class_subjects(
    institution_id: UUID | str,
    source_session: AcademicSession,
    target_session: AcademicSession,
    dry_run: bool,
    result: CopySessionResult,
) -> None:
    source_class_subjects = ClassSubject.objects.filter(
        institution_id=institution_id,
        session=source_session,
    ).select_related("class_level", "group", "subject")

    existing_subjects = {
        (cs.class_level_id, cs.group_id, cs.subject_id)
        for cs in ClassSubject.objects.filter(institution_id=institution_id, session=target_session)
    }

    for cs in source_class_subjects:
        key = (cs.class_level_id, cs.group_id, cs.subject_id)
        if key in existing_subjects:
            result.skipped_subjects_count += 1
            continue

        group_name = f" [{cs.group.name}]" if cs.group else ""
        preview_label = f"{cs.class_level.name}{group_name} -> {cs.subject.name_en}"
        result.preview["class_subjects"].append(preview_label)
        result.class_subjects_count += 1

        if not dry_run:
            ClassSubject.objects.create(
                institution_id=institution_id,
                class_level=cs.class_level,
                group=cs.group,
                session=target_session,
                subject=cs.subject,
                full_marks=cs.full_marks,
                pass_rule=cs.pass_rule,
                credit_weight=cs.credit_weight,
                is_optional_elective=cs.is_optional_elective,
            )


def _copy_routine_slots(
    institution_id: UUID | str,
    source_session: AcademicSession,
    section_mapping: dict[UUID, Section],
    preserve_teachers: bool,
    dry_run: bool,
    result: CopySessionResult,
) -> None:
    if dry_run:
        old_slots_count = RoutineSlot.objects.filter(
            institution_id=institution_id,
            section__session=source_session,
        ).count()
        result.routine_slots_count = old_slots_count
        result.preview["routine_slots"].append(f"{old_slots_count} routine slots eligible to copy")
        return

    for old_sec_id, new_sec in section_mapping.items():
        old_slots = RoutineSlot.objects.filter(
            institution_id=institution_id,
            section_id=old_sec_id,
        )
        for slot in old_slots:
            RoutineSlot.objects.create(
                institution_id=institution_id,
                section=new_sec,
                weekday=slot.weekday,
                period=slot.period,
                subject=slot.subject,
                teacher_user=slot.teacher_user if preserve_teachers else None,
                room=slot.room,
            )
            result.routine_slots_count += 1


def copy_academic_structure_from_previous_session(
    *,
    institution_id: UUID | str,
    source_session_id: UUID | str,
    target_session_id: UUID | str,
    copy_sections: bool = True,
    copy_class_subjects: bool = True,
    copy_routine: bool = False,
    preserve_teachers: bool = False,
    dry_run: bool = True,
) -> CopySessionResult:
    """Copies academic structure (sections, subject offerings, optional routines)

    from source session to target session.
    If dry_run=True, simulates and returns what would be created without saving to DB.
    """
    source_session = AcademicSession.objects.get(
        id=source_session_id, institution_id=institution_id
    )
    target_session = AcademicSession.objects.get(
        id=target_session_id, institution_id=institution_id
    )

    result = CopySessionResult(
        source_session_id=str(source_session.id),
        target_session_id=str(target_session.id),
        dry_run=dry_run,
        preview={"sections": [], "class_subjects": [], "routine_slots": []},
    )

    with transaction.atomic():
        section_mapping: dict[UUID, Section] = {}

        if copy_sections:
            _copy_sections(
                institution_id,
                source_session,
                target_session,
                preserve_teachers,
                dry_run,
                result,
                section_mapping,
            )

        if copy_class_subjects:
            _copy_class_subjects(
                institution_id,
                source_session,
                target_session,
                dry_run,
                result,
            )

        if copy_routine:
            _copy_routine_slots(
                institution_id,
                source_session,
                section_mapping,
                preserve_teachers,
                dry_run,
                result,
            )

        if dry_run:
            transaction.set_rollback(True)

    return result
