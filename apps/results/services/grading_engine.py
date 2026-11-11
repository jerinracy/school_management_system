"""Pure, table-driven grading engine for Bangladesh National Curriculum (GPA 5.0).

Encapsulates:
- Subject component pass evaluation (Creative / CQ, MCQ, Practical)
- Combined 1st & 2nd paper evaluation (Bangla / English)
- Optional 4th subject bonus points math: max(0, GPA - 2.00)
- Mandatory fail rule: Fail in any mandatory subject = GPA 0.00 / F
- Deterministic merit ranking and tie-breaking algorithms
- Multi-term weighted CGPA calculation
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from apps.results.models import GradingScale
from apps.results.services.grading_scale_service import (
    resolve_grade_for_gpa,
    resolve_grade_for_percentage,
)


def _q2(val: Decimal | float | int | str) -> Decimal:
    """Quantize to 2 decimal places with ROUND_HALF_UP."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _check_all_components(
    c_m: Decimal | None,
    c_p: Decimal | None,
    m_m: Decimal | None,
    m_p: Decimal | None,
    p_m: Decimal | None,
    p_p: Decimal | None,
) -> tuple[bool, str]:
    if c_p and c_m is not None and c_m < c_p:
        return False, f"Creative (CQ) marks {c_m} is below pass mark {c_p}"
    if m_p and m_m is not None and m_m < m_p:
        return False, f"MCQ marks {m_m} is below pass mark {m_p}"
    if p_p and p_m is not None and p_m < p_p:
        return False, f"Practical marks {p_m} is below pass mark {p_p}"
    return True, ""


def _check_theory_practical_separate(
    c_m: Decimal | None,
    c_p: Decimal | None,
    m_m: Decimal | None,
    m_p: Decimal | None,
    p_m: Decimal | None,
    p_p: Decimal | None,
) -> tuple[bool, str]:
    theory_marks = (c_m or Decimal("0.00")) + (m_m or Decimal("0.00"))
    theory_pass = (c_p or Decimal("0.00")) + (m_p or Decimal("0.00"))

    if theory_pass > Decimal("0.00") and theory_marks < theory_pass:
        return False, f"Theory total {theory_marks} is below theory pass mark {theory_pass}"

    if p_p and p_m is not None and p_m < p_p:
        return False, f"Practical marks {p_m} is below pass mark {p_p}"

    return True, ""


def evaluate_component_pass(
    pass_policy: str,
    full_marks: Decimal,
    pass_marks: Decimal,
    creative_marks: Decimal | None,
    creative_pass: Decimal | None,
    mcq_marks: Decimal | None,
    mcq_pass: Decimal | None,
    practical_marks: Decimal | None,
    practical_pass: Decimal | None,
    total_marks: Decimal,
) -> tuple[bool, str]:
    """Check component-level pass conditions based on the subject's pass policy."""
    if total_marks < pass_marks:
        return False, f"Total marks {total_marks} is below pass mark {pass_marks}"

    if pass_policy == "overall_aggregate":
        return True, ""

    if pass_policy == "all_components":
        return _check_all_components(
            creative_marks, creative_pass, mcq_marks, mcq_pass, practical_marks, practical_pass
        )

    if pass_policy == "theory_practical_separate":
        return _check_theory_practical_separate(
            creative_marks, creative_pass, mcq_marks, mcq_pass, practical_marks, practical_pass
        )

    return total_marks >= pass_marks, ""


def evaluate_subject_marks(
    full_marks: Decimal,
    pass_marks: Decimal,
    creative_marks: Decimal | None,
    creative_pass: Decimal | None,
    mcq_marks: Decimal | None,
    mcq_pass: Decimal | None,
    practical_marks: Decimal | None,
    practical_pass: Decimal | None,
    pass_policy: str,
    is_absent: bool,
    grace_marks: Decimal,
    scale: GradingScale,
) -> dict[str, Any]:
    """Calculate the grade point, letter grade, percentage, and pass status for a single subject."""
    if is_absent:
        return {
            "total_marks": Decimal("0.00"),
            "marks_percentage": Decimal("0.00"),
            "grade_point": Decimal("0.00"),
            "letter_grade": "F",
            "is_passed": False,
            "fail_reason": "Student was absent for the examination",
            "grace_marks": Decimal("0.00"),
        }

    c_m = creative_marks or Decimal("0.00")
    m_m = mcq_marks or Decimal("0.00")
    p_m = practical_marks or Decimal("0.00")
    raw_total = c_m + m_m + p_m
    effective_total = min(full_marks, raw_total + grace_marks)

    pct = Decimal("0.00")
    if full_marks > Decimal("0.00"):
        pct = _q2((effective_total / full_marks) * Decimal("100.00"))

    is_passed, fail_reason = evaluate_component_pass(
        pass_policy=pass_policy,
        full_marks=full_marks,
        pass_marks=pass_marks,
        creative_marks=creative_marks,
        creative_pass=creative_pass,
        mcq_marks=mcq_marks,
        mcq_pass=mcq_pass,
        practical_marks=practical_marks,
        practical_pass=practical_pass,
        total_marks=effective_total,
    )

    if not is_passed:
        return {
            "total_marks": effective_total,
            "marks_percentage": pct,
            "grade_point": Decimal("0.00"),
            "letter_grade": "F",
            "is_passed": False,
            "fail_reason": fail_reason,
            "grace_marks": grace_marks,
        }

    grade_info = resolve_grade_for_percentage(scale, pct)
    return {
        "total_marks": effective_total,
        "marks_percentage": pct,
        "grade_point": grade_info["grade_point"],
        "letter_grade": grade_info["letter_grade"],
        "is_passed": grade_info["grade_point"] > Decimal("0.00"),
        "fail_reason": "",
        "grace_marks": grace_marks,
    }


def calculate_combined_paper(
    paper_1_marks: Decimal,
    paper_1_full: Decimal,
    paper_2_marks: Decimal,
    paper_2_full: Decimal,
    combined_pass_marks: Decimal,
    scale: GradingScale,
) -> dict[str, Any]:
    """Calculate aggregate result for combined 1st and 2nd papers (e.g. Bangla 200 marks)."""
    total_marks = paper_1_marks + paper_2_marks
    total_full = paper_1_full + paper_2_full
    pct = Decimal("0.00")
    if total_full > Decimal("0.00"):
        pct = _q2((total_marks / total_full) * Decimal("100.00"))

    is_passed = total_marks >= combined_pass_marks
    if not is_passed:
        return {
            "total_marks": total_marks,
            "full_marks": total_full,
            "marks_percentage": pct,
            "grade_point": Decimal("0.00"),
            "letter_grade": "F",
            "is_passed": False,
            "fail_reason": f"Combined total {total_marks} is below pass mark {combined_pass_marks}",
        }

    grade_info = resolve_grade_for_percentage(scale, pct)
    return {
        "total_marks": total_marks,
        "full_marks": total_full,
        "marks_percentage": pct,
        "grade_point": grade_info["grade_point"],
        "letter_grade": grade_info["letter_grade"],
        "is_passed": grade_info["grade_point"] > Decimal("0.00"),
        "fail_reason": "",
    }


def calculate_final_gpa(
    mandatory_subject_grades: list[Decimal],
    fourth_subject_grade: Decimal | None,
    scale: GradingScale,
) -> tuple[Decimal, Decimal, Decimal, str, bool]:
    """Calculate the final overall GPA under Bangladesh National Curriculum standards.

    Formula:
    1. If ANY mandatory subject has GP == 0.00 (F), then:
       final_gpa = 0.00, grade = 'F', is_passed = False.
    2. Fourth subject bonus points = max(0.00, fourth_subject_grade - 2.00).
    3. GPA without fourth = sum(mandatory) / count(mandatory).
    4. Final GPA = min(5.00, (sum(mandatory) + fourth_bonus) / count(mandatory)).
    5. Capped at scale.max_gpa (default 5.00).
    """
    if not mandatory_subject_grades:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), "F", False

    # Check for failure in any mandatory subject
    for gp in mandatory_subject_grades:
        if gp <= Decimal("0.00"):
            return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), "F", False

    num_mandatory = len(mandatory_subject_grades)
    sum_mandatory = sum(mandatory_subject_grades)
    gpa_without_fourth = _q2(sum_mandatory / Decimal(num_mandatory))

    # Calculate 4th subject bonus
    fourth_bonus = Decimal("0.00")
    if fourth_subject_grade is not None and fourth_subject_grade > Decimal("2.00"):
        fourth_bonus = _q2(fourth_subject_grade - Decimal("2.00"))

    # Final GPA calculation
    computed_gpa = _q2((sum_mandatory + fourth_bonus) / Decimal(num_mandatory))
    final_gpa = min(scale.max_gpa, computed_gpa)
    final_grade = resolve_grade_for_gpa(scale, final_gpa)

    return final_gpa, gpa_without_fourth, fourth_bonus, final_grade, True


def sort_and_rank_students(student_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministically rank students across a class level and within sections.

    Tie-breaking hierarchy:
    1. Passed candidates ranked above failed candidates
    2. Final GPA descending
    3. Total Marks descending
    4. Roll number ascending (as secondary tie-breaker)
    """

    # Sort key: (-is_passed, -final_gpa, -total_marks, roll_no)
    def _sort_key(rec: dict[str, Any]) -> tuple[int, Decimal, Decimal, int]:
        passed_flag = 0 if rec.get("is_passed", False) else 1
        gpa = rec.get("final_gpa", Decimal("0.00"))
        tot_marks = rec.get("total_marks", Decimal("0.00"))
        roll = rec.get("roll_no", 999999)
        return (passed_flag, -gpa, -tot_marks, roll)

    sorted_cohort = sorted(student_records, key=_sort_key)

    # Assign class_position
    for class_rank, rec in enumerate(sorted_cohort, start=1):
        rec["class_position"] = class_rank

    # Assign section_position per section
    sections: dict[str, list[dict[str, Any]]] = {}
    for rec in sorted_cohort:
        sec_id = str(rec.get("section_id", "default"))
        sections.setdefault(sec_id, []).append(rec)

    for sec_list in sections.values():
        for sec_rank, rec in enumerate(sec_list, start=1):
            rec["section_position"] = sec_rank

    return sorted_cohort


def calculate_cumulative_cgpa(
    term_results: list[dict[str, Any]],
    weightage_rules: list[dict[str, Any]],
    scale: GradingScale,
) -> dict[str, Any]:
    """Calculate annual cumulative weighted CGPA across examination terms.

    Example:
    Term 1 (Half Yearly): GPA 4.50 @ 30% = 1.35
    Term 2 (Annual): GPA 5.00 @ 70% = 3.50
    Total CGPA = 4.85 (Grade A)
    """
    total_weight = Decimal("0.00")
    weighted_gpa_sum = Decimal("0.00")
    cumulative_marks = Decimal("0.00")
    all_passed = True
    term_summary: list[dict[str, Any]] = []

    # Map exam_id to weight
    weights = {str(w["exam_id"]): Decimal(str(w["weightage_percentage"])) for w in weightage_rules}

    for tr in term_results:
        exam_id = str(tr["exam_id"])
        weight = weights.get(exam_id, Decimal("0.00"))
        total_weight += weight

        term_gpa = Decimal(str(tr.get("final_gpa", "0.00")))
        term_marks = Decimal(str(tr.get("total_marks", "0.00")))
        is_passed = tr.get("is_passed", False)
        if not is_passed:
            all_passed = False

        weighted_gpa_sum += term_gpa * (weight / Decimal("100.00"))
        cumulative_marks += term_marks * (weight / Decimal("100.00"))

        term_summary.append(
            {
                "exam_id": exam_id,
                "exam_name": tr.get("exam_name", ""),
                "weightage_percentage": str(weight),
                "final_gpa": str(term_gpa),
                "total_marks": str(term_marks),
                "is_passed": is_passed,
            }
        )

    # Normalize if total_weight is not 100
    if total_weight > Decimal("0.00") and total_weight != Decimal("100.00"):
        weighted_gpa_sum = (weighted_gpa_sum / total_weight) * Decimal("100.00")

    final_cgpa = _q2(min(scale.max_gpa, weighted_gpa_sum))
    final_grade = resolve_grade_for_gpa(scale, final_cgpa)

    return {
        "cumulative_marks": _q2(cumulative_marks),
        "cumulative_gpa": final_cgpa,
        "cumulative_grade": final_grade,
        "is_passed": all_passed and final_cgpa >= scale.pass_gpa,
        "promotion_recommended": all_passed and final_cgpa >= scale.pass_gpa,
        "term_results": term_summary,
    }
