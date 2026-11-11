"""Database service orchestrating mark tabulation, grading evaluation, and ranking."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.exams.models import Exam, ExamSubject, GraceMarkRule, MarkEntry
from apps.results.models import (
    CombinedSubjectResult,
    CumulativeResult,
    ExamResult,
    ExamResultStatus,
    GradingScale,
    StudentOptionalSubject,
    SubjectResult,
    TermWeightageRule,
)
from apps.results.services.grading_engine import (
    calculate_cumulative_cgpa,
    calculate_final_gpa,
    evaluate_subject_marks,
    sort_and_rank_students,
)
from apps.results.services.grading_scale_service import get_default_grading_scale
from apps.students.models import Student, StudentEnrollment


def _evaluate_grace_marks(
    exam_subject: ExamSubject,
    raw_total: Decimal,
    grace_rules: list[GraceMarkRule],
) -> Decimal:
    """Determine if any GraceMarkRule applies to this subject's score."""
    if not grace_rules:
        return Decimal("0.00")

    deficit = exam_subject.pass_marks - raw_total
    if deficit <= Decimal("0.00"):
        return Decimal("0.00")

    for rule in grace_rules:
        if rule.subject_id is None or rule.subject_id == exam_subject.subject_id:
            if deficit <= rule.max_grace_marks:
                return deficit

    return Decimal("0.00")


def _tabulate_student_subjects(
    student: Student,
    exam: Exam,
    exam_subjects: list[ExamSubject],
    marks_map: dict[tuple[UUID, UUID], MarkEntry],
    optional_subj_ids: set[UUID],
    grace_rules: list[GraceMarkRule],
    scale: Any,
) -> tuple[list[SubjectResult], list[CombinedSubjectResult]]:
    """Compute and persist SubjectResult records for a single student."""
    subj_results: list[SubjectResult] = []
    combined_results: list[CombinedSubjectResult] = []

    for es in exam_subjects:
        entry = marks_map.get((es.id, student.id))
        is_absent = entry.is_absent if entry else False
        c_m = entry.creative_marks if entry else None
        m_m = entry.mcq_marks if entry else None
        p_m = entry.practical_marks if entry else None

        raw_total = (c_m or Decimal("0.00")) + (m_m or Decimal("0.00")) + (p_m or Decimal("0.00"))
        grace = _evaluate_grace_marks(es, raw_total, grace_rules)

        is_fourth = es.subject_id in optional_subj_ids

        res_data = evaluate_subject_marks(
            full_marks=es.full_marks,
            pass_marks=es.pass_marks,
            creative_marks=c_m,
            creative_pass=es.creative_pass_marks,
            mcq_marks=m_m,
            mcq_pass=es.mcq_pass_marks,
            practical_marks=p_m,
            practical_pass=es.practical_pass_marks,
            pass_policy=getattr(es, "pass_policy", "all_components"),
            is_absent=is_absent,
            grace_marks=grace,
            scale=scale,
        )

        subj_res, _ = SubjectResult.objects.update_or_create(
            institution=exam.institution,
            exam=exam,
            exam_subject=es,
            student=student,
            defaults={
                "creative_marks": c_m,
                "mcq_marks": m_m,
                "practical_marks": p_m,
                "total_marks": res_data["total_marks"],
                "full_marks": es.full_marks,
                "marks_percentage": res_data["marks_percentage"],
                "grade_point": res_data["grade_point"],
                "letter_grade": res_data["letter_grade"],
                "is_passed": res_data["is_passed"],
                "is_absent": is_absent,
                "grace_marks": res_data["grace_marks"],
                "is_fourth_subject": is_fourth,
                "fail_reason": res_data["fail_reason"],
            },
        )
        subj_results.append(subj_res)

    return subj_results, combined_results


def _evaluate_student_exam_summary(
    student: Student,
    enr: StudentEnrollment,
    exam: Exam,
    exam_subjects: list[ExamSubject],
    marks_map: dict[tuple[UUID, UUID], MarkEntry],
    optional_subj_ids: set[UUID],
    grace_rules: list[GraceMarkRule],
    scale: GradingScale,
) -> dict[str, Any]:
    """Calculate subject results and overall exam performance for a single student."""
    subj_results, _ = _tabulate_student_subjects(
        student=student,
        exam=exam,
        exam_subjects=exam_subjects,
        marks_map=marks_map,
        optional_subj_ids=optional_subj_ids,
        grace_rules=grace_rules,
        scale=scale,
    )

    mandatory_gps: list[Decimal] = []
    fourth_gp: Decimal | None = None
    tot_marks = Decimal("0.00")
    tot_full = Decimal("0.00")
    failed_subjs: list[str] = []

    for sr in subj_results:
        tot_marks += sr.total_marks
        tot_full += sr.full_marks
        if sr.is_fourth_subject:
            fourth_gp = sr.grade_point
        else:
            mandatory_gps.append(sr.grade_point)
            if not sr.is_passed:
                failed_subjs.append(sr.exam_subject.subject.name_en)

    final_gpa, gpa_no_4th, bonus, final_grade, is_passed = calculate_final_gpa(
        mandatory_subject_grades=mandatory_gps,
        fourth_subject_grade=fourth_gp,
        scale=scale,
    )

    pct = Decimal("0.00")
    if tot_full > Decimal("0.00"):
        pct = Decimal(str((tot_marks / tot_full) * Decimal("100.00"))).quantize(Decimal("0.01"))

    return {
        "student": student,
        "enrollment": enr,
        "section_id": enr.section_id,
        "class_level_id": enr.class_level_id,
        "roll_no": enr.roll_no,
        "total_marks": tot_marks,
        "total_full_marks": tot_full,
        "percentage": pct,
        "gpa_without_fourth": gpa_no_4th,
        "fourth_subject_bonus": bonus,
        "final_gpa": final_gpa,
        "final_grade": final_grade,
        "is_passed": is_passed,
        "failed_subject_count": len(failed_subjs),
        "failed_subjects_summary": failed_subjs,
    }


def _save_ranked_exam_results(
    exam: Exam,
    ranked_records: list[dict[str, Any]],
) -> tuple[int, int]:
    """Persist ranked exam results and return (passed_count, failed_count)."""
    passed_count = 0
    failed_count = 0

    for rec in ranked_records:
        if rec["is_passed"]:
            passed_count += 1
        else:
            failed_count += 1

        ExamResult.objects.update_or_create(
            institution=exam.institution,
            exam=exam,
            student=rec["student"],
            defaults={
                "enrollment": rec["enrollment"],
                "total_marks": rec["total_marks"],
                "total_full_marks": rec["total_full_marks"],
                "percentage": rec["percentage"],
                "gpa_without_fourth": rec["gpa_without_fourth"],
                "fourth_subject_bonus": rec["fourth_subject_bonus"],
                "final_gpa": rec["final_gpa"],
                "final_grade": rec["final_grade"],
                "is_passed": rec["is_passed"],
                "failed_subject_count": rec["failed_subject_count"],
                "failed_subjects_summary": rec["failed_subjects_summary"],
                "section_position": rec.get("section_position"),
                "class_position": rec.get("class_position"),
                "status": ExamResultStatus.DRAFT,
            },
        )
    return passed_count, failed_count


@transaction.atomic
def tabulate_exam_results(exam_id: UUID | str) -> dict[str, Any]:
    """Execute complete mark tabulation and ranking for an entire examination."""
    exam = Exam.objects.select_related("institution", "session").get(id=exam_id)
    scale = get_default_grading_scale(exam.institution)

    exam_subjects = list(ExamSubject.objects.filter(exam=exam).select_related("subject"))
    if not exam_subjects:
        return {"status": "error", "message": "No exam subjects configured for this exam."}

    mark_entries = list(MarkEntry.objects.filter(exam_subject__exam=exam))
    marks_map = {(me.exam_subject_id, me.student_id): me for me in mark_entries}

    student_ids = {me.student_id for me in mark_entries}
    if not student_ids:
        return {"status": "error", "message": "No student marks recorded for this exam."}

    students = list(Student.objects.filter(id__in=student_ids, institution=exam.institution))
    enrollments_map = {
        enr.student_id: enr
        for enr in StudentEnrollment.objects.filter(
            student_id__in=student_ids,
            session=exam.session,
            is_deleted=False,
        ).select_related("section", "class_level")
    }

    optional_subjects = StudentOptionalSubject.objects.filter(
        student_id__in=student_ids,
        session=exam.session,
        is_deleted=False,
    )
    optional_subj_map: dict[UUID, set[UUID]] = {}
    for os in optional_subjects:
        optional_subj_map.setdefault(os.student_id, set()).add(os.subject_id)

    grace_rules = list(
        GraceMarkRule.objects.filter(
            institution=exam.institution,
            exam=exam,
            is_active=True,
        )
    )

    unranked_results: list[dict[str, Any]] = []

    for student in students:
        enr = enrollments_map.get(student.id)
        if not enr:
            continue

        st_opt_ids = optional_subj_map.get(student.id, set())
        st_summary = _evaluate_student_exam_summary(
            student=student,
            enr=enr,
            exam=exam,
            exam_subjects=exam_subjects,
            marks_map=marks_map,
            optional_subj_ids=st_opt_ids,
            grace_rules=grace_rules,
            scale=scale,
        )
        unranked_results.append(st_summary)

    # Deterministic ranking across class and section
    ranked_records = sort_and_rank_students(unranked_results)
    passed_count, failed_count = _save_ranked_exam_results(exam, ranked_records)

    # Transition exam status if currently marks_entry
    if exam.status in ["marks_entry", "scheduled"]:
        exam.status = "tabulating"
        exam.save(update_fields=["status", "updated_at"])

    return {
        "status": "success",
        "exam_id": str(exam.id),
        "exam_name": exam.name,
        "total_students": len(ranked_records),
        "passed_count": passed_count,
        "failed_count": failed_count,
    }


@transaction.atomic
def tabulate_cumulative_results(
    session_id: UUID | str, class_level_id: UUID | str
) -> dict[str, Any]:
    """Calculate annual cumulative CGPA across weighted exams for a class in a session."""
    session_uuid = UUID(str(session_id)) if not isinstance(session_id, UUID) else session_id
    class_level_uuid = (
        UUID(str(class_level_id)) if not isinstance(class_level_id, UUID) else class_level_id
    )

    weight_rules = list(
        TermWeightageRule.objects.filter(
            session_id=session_uuid,
            class_level_id=class_level_uuid,
            is_deleted=False,
        ).select_related("exam", "institution")
    )
    if not weight_rules:
        return {"status": "error", "message": "No term weightage rules configured."}

    institution = weight_rules[0].institution
    scale = get_default_grading_scale(institution)

    exam_ids = [w.exam_id for w in weight_rules]
    exam_results = list(
        ExamResult.objects.filter(
            exam_id__in=exam_ids,
            enrollment__class_level_id=class_level_uuid,
            is_deleted=False,
        ).select_related("student", "enrollment", "exam")
    )

    # Group by student
    student_exam_map: dict[UUID, list[ExamResult]] = {}
    enrollments: dict[UUID, StudentEnrollment] = {}
    students: dict[UUID, Student] = {}

    for er in exam_results:
        student_exam_map.setdefault(er.student_id, []).append(er)
        enrollments[er.student_id] = er.enrollment
        students[er.student_id] = er.student

    rule_dicts = [
        {"exam_id": w.exam_id, "weightage_percentage": w.weightage_percentage} for w in weight_rules
    ]

    unranked_cumulatives: list[dict[str, Any]] = []

    for st_id, er_list in student_exam_map.items():
        term_dicts = [
            {
                "exam_id": er.exam_id,
                "exam_name": er.exam.name,
                "final_gpa": er.final_gpa,
                "total_marks": er.total_marks,
                "is_passed": er.is_passed,
            }
            for er in er_list
        ]

        cum_data = calculate_cumulative_cgpa(term_dicts, rule_dicts, scale)

        enr = enrollments[st_id]
        unranked_cumulatives.append(
            {
                "student": students[st_id],
                "enrollment": enr,
                "section_id": enr.section_id,
                "roll_no": enr.roll_no,
                "cumulative_marks": cum_data["cumulative_marks"],
                "cumulative_gpa": cum_data["cumulative_gpa"],
                "cumulative_grade": cum_data["cumulative_grade"],
                "is_passed": cum_data["is_passed"],
                "promotion_recommended": cum_data["promotion_recommended"],
                "term_results": cum_data["term_results"],
                "final_gpa": cum_data["cumulative_gpa"],
                "total_marks": cum_data["cumulative_marks"],
            }
        )

    ranked_cohort = sort_and_rank_students(unranked_cumulatives)

    for rec in ranked_cohort:
        CumulativeResult.objects.update_or_create(
            institution=institution,
            session_id=session_id,
            class_level_id=class_level_id,
            student=rec["student"],
            defaults={
                "enrollment": rec["enrollment"],
                "term_results": rec["term_results"],
                "cumulative_marks": rec["cumulative_marks"],
                "cumulative_gpa": rec["cumulative_gpa"],
                "cumulative_grade": rec["cumulative_grade"],
                "is_passed": rec["is_passed"],
                "final_section_position": rec.get("section_position"),
                "final_class_position": rec.get("class_position"),
                "promotion_recommended": rec["promotion_recommended"],
            },
        )

    return {
        "status": "success",
        "session_id": str(session_id),
        "class_level_id": str(class_level_id),
        "students_tabulated": len(ranked_cohort),
    }
