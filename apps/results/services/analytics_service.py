"""Academic analytics: weak-student diagnostics and promotion eligibility feed."""

from collections import Counter
from decimal import Decimal
from typing import Any
from uuid import UUID

from apps.academics.models import ClassLevel
from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.exams.models import Exam
from apps.institutions.models import AcademicSession
from apps.results.models import CumulativeResult, ExamResult


def get_weak_students_analytics(
    exam_id: UUID | str,
    gpa_threshold: Decimal = Decimal("2.00"),
) -> dict[str, Any]:
    """Identify students at academic risk (failed subjects or below GPA threshold)."""
    exam = Exam.objects.select_related("institution", "session").get(id=exam_id)

    all_results = list(
        ExamResult.objects.filter(exam=exam, is_deleted=False)
        .select_related("student", "enrollment", "enrollment__section", "enrollment__class_level")
        .order_by("final_gpa", "total_marks")
    )
    total_cohort = len(all_results)
    if total_cohort == 0:
        return {
            "exam_id": str(exam.id),
            "exam_name": exam.name,
            "total_students": 0,
            "weak_student_count": 0,
            "weak_student_percentage": Decimal("0.00"),
            "subject_failure_frequencies": [],
            "students": [],
        }

    weak_records = []
    subject_fails_counter: Counter[str] = Counter()

    for er in all_results:
        is_weak = False
        reasons = []

        if not er.is_passed or er.failed_subject_count > 0:
            is_weak = True
            reasons.append(f"Failed {er.failed_subject_count} subject(s)")
            for s_name in er.failed_subjects_summary:
                subject_fails_counter[s_name] += 1

        if er.final_gpa < gpa_threshold:
            is_weak = True
            reasons.append(f"GPA {er.final_gpa} below threshold ({gpa_threshold})")

        if is_weak:
            sec_name = er.enrollment.section.name if er.enrollment.section else "N/A"
            weak_records.append(
                {
                    "student_id": er.student.student_id,
                    "student_name": er.student.name_en,
                    "class_name": er.enrollment.class_level.name,
                    "section_name": sec_name,
                    "roll_no": er.enrollment.roll_no,
                    "final_gpa": str(er.final_gpa),
                    "final_grade": er.final_grade,
                    "failed_subjects": er.failed_subjects_summary,
                    "risk_reasons": reasons,
                }
            )

    weak_count = len(weak_records)
    weak_pct = Decimal(str((weak_count / total_cohort) * 100)).quantize(Decimal("0.01"))

    # Convert subject failures to sorted list
    freq_list = [
        {"subject_name": subj, "failure_count": count}
        for subj, count in subject_fails_counter.most_common()
    ]

    return {
        "exam_id": str(exam.id),
        "exam_name": exam.name,
        "total_students": total_cohort,
        "weak_student_count": weak_count,
        "weak_student_percentage": weak_pct,
        "subject_failure_frequencies": freq_list,
        "students": weak_records,
    }


def get_promotion_eligibility_feed(
    session_id: UUID | str,
    class_level_id: UUID | str,
    min_cgpa: Decimal = Decimal("2.00"),
    min_attendance_pct: Decimal = Decimal("70.00"),
) -> dict[str, Any]:
    """Generate promotion recommendations based on annual CGPA and attendance."""
    session = AcademicSession.objects.get(id=session_id)
    class_level = ClassLevel.objects.get(id=class_level_id)

    cum_results = list(
        CumulativeResult.objects.filter(
            session=session,
            class_level=class_level,
            is_deleted=False,
        ).select_related("student", "enrollment", "enrollment__section")
    )

    eligible = []
    conditional = []
    retained = []

    for cr in cum_results:
        student = cr.student
        enr = cr.enrollment
        sec_name = enr.section.name if enr.section else "N/A"

        # Calculate session-wide attendance percentage
        att_qs = DailyAttendance.objects.filter(
            student=student,
            date__gte=session.start_date,
            date__lte=session.end_date,
        )
        working_days = att_qs.exclude(
            status__in=[AttendanceStatus.HOLIDAY, AttendanceStatus.WEEKEND]
        ).count()
        present_count = att_qs.filter(
            status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE]
        ).count()

        att_pct = Decimal("0.00")
        if working_days > 0:
            att_pct = Decimal(str((present_count / working_days) * 100)).quantize(Decimal("0.01"))

        stu_info = {
            "student_id": student.student_id,
            "student_name": student.name_en,
            "roll_no": enr.roll_no,
            "section_name": sec_name,
            "cumulative_gpa": str(cr.cumulative_gpa),
            "cumulative_grade": cr.cumulative_grade,
            "attendance_percentage": str(att_pct),
        }

        # Decision rule:
        # 1. Eligible: Passed all terms, CGPA >= min_cgpa, Attendance >= min_attendance_pct
        if cr.is_passed and cr.cumulative_gpa >= min_cgpa and att_pct >= min_attendance_pct:
            eligible.append({**stu_info, "recommendation": "PROMOTE"})
        # 2. Conditional: Passed, CGPA >= min_cgpa, but low attendance
        elif cr.is_passed and cr.cumulative_gpa >= min_cgpa and att_pct < min_attendance_pct:
            conditional.append(
                {
                    **stu_info,
                    "recommendation": "CONDITIONAL_PROMOTION",
                    "reason": f"Attendance {att_pct}% is below required {min_attendance_pct}%",
                }
            )
        # 3. Retained: Failed compulsory subjects or CGPA < min_cgpa
        else:
            reasons = []
            if not cr.is_passed:
                reasons.append("Failed mandatory examination requirements")
            if cr.cumulative_gpa < min_cgpa:
                reasons.append(f"CGPA {cr.cumulative_gpa} below minimum {min_cgpa}")
            retained.append(
                {
                    **stu_info,
                    "recommendation": "RETAIN",
                    "reason": "; ".join(reasons),
                }
            )

    return {
        "session_id": str(session.id),
        "session_name": session.name,
        "class_level_id": str(class_level.id),
        "class_level_name": class_level.name,
        "total_evaluated": len(cum_results),
        "promoted_count": len(eligible),
        "conditional_count": len(conditional),
        "retained_count": len(retained),
        "eligible": eligible,
        "conditional": conditional,
        "retained": retained,
    }
