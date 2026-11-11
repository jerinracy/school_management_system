"""Pure table-driven golden tests for the Bangladesh National Curriculum (GPA 5.0) grading engine."""

from decimal import Decimal

import pytest

from apps.institutions.models import Institution
from apps.results.services.grading_engine import (
    calculate_combined_paper,
    calculate_cumulative_cgpa,
    calculate_final_gpa,
    evaluate_component_pass,
    sort_and_rank_students,
)
from apps.results.services.grading_scale_service import (
    resolve_grade_for_percentage,
    seed_default_bd_grading_scale,
)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Collegiate School",
        name_bn="ঢাকা কলেজিয়েট স্কুল",
        eiin="108257",
        address_line="Sadarghat, Dhaka",
        email="dcs@edu.bd",
        phone="+8801711223344",
    )


@pytest.fixture
def bd_scale(institution):
    return seed_default_bd_grading_scale(institution)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "percentage,expected_gp,expected_grade",
    [
        (Decimal("100.00"), Decimal("5.00"), "A+"),
        (Decimal("85.50"), Decimal("5.00"), "A+"),
        (Decimal("80.00"), Decimal("5.00"), "A+"),
        (Decimal("79.99"), Decimal("4.00"), "A"),
        (Decimal("72.00"), Decimal("4.00"), "A"),
        (Decimal("70.00"), Decimal("4.00"), "A"),
        (Decimal("69.99"), Decimal("3.50"), "A-"),
        (Decimal("60.00"), Decimal("3.50"), "A-"),
        (Decimal("59.99"), Decimal("3.00"), "B"),
        (Decimal("50.00"), Decimal("3.00"), "B"),
        (Decimal("49.99"), Decimal("2.00"), "C"),
        (Decimal("40.00"), Decimal("2.00"), "C"),
        (Decimal("39.99"), Decimal("1.00"), "D"),
        (Decimal("33.00"), Decimal("1.00"), "D"),
        (Decimal("32.99"), Decimal("0.00"), "F"),
        (Decimal("15.00"), Decimal("0.00"), "F"),
        (Decimal("0.00"), Decimal("0.00"), "F"),
    ],
)
def test_grade_percentage_resolution_boundaries(bd_scale, percentage, expected_gp, expected_grade):
    """Verify that percentage boundaries exactly match Bangladesh Ministry of Education standards."""
    info = resolve_grade_for_percentage(bd_scale, percentage)
    assert info["grade_point"] == expected_gp
    assert info["letter_grade"] == expected_grade


@pytest.mark.django_db
def test_component_pass_policies(bd_scale):
    """Test component-level pass evaluation across different policy configurations."""
    # Case A: all_components policy - Total passed (75/100) but MCQ failed (8/30, pass mark 10)
    passed, reason = evaluate_component_pass(
        pass_policy="all_components",
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_marks=Decimal("50.00"),
        creative_pass=Decimal("23.00"),
        mcq_marks=Decimal("8.00"),
        mcq_pass=Decimal("10.00"),
        practical_marks=Decimal("17.00"),
        practical_pass=Decimal("8.00"),
        total_marks=Decimal("75.00"),
    )
    assert passed is False
    assert "MCQ marks 8.00 is below pass mark 10.00" in reason

    # Case B: overall_aggregate policy - Same marks, but passes because aggregate is 75 >= 33
    passed_agg, reason_agg = evaluate_component_pass(
        pass_policy="overall_aggregate",
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_marks=Decimal("50.00"),
        creative_pass=Decimal("23.00"),
        mcq_marks=Decimal("8.00"),
        mcq_pass=Decimal("10.00"),
        practical_marks=Decimal("17.00"),
        practical_pass=Decimal("8.00"),
        total_marks=Decimal("75.00"),
    )
    assert passed_agg is True
    assert reason_agg == ""


@pytest.mark.django_db
def test_combined_paper_evaluation(bd_scale):
    """Test 200-mark combined paper evaluation (e.g. Bangla 1st + 2nd)."""
    # 30 in Paper 1 + 40 in Paper 2 = 70/200 (35%) -> Meets combined pass mark 66 -> Grade D
    res_pass = calculate_combined_paper(
        paper_1_marks=Decimal("30.00"),
        paper_1_full=Decimal("100.00"),
        paper_2_marks=Decimal("40.00"),
        paper_2_full=Decimal("100.00"),
        combined_pass_marks=Decimal("66.00"),
        scale=bd_scale,
    )
    assert res_pass["is_passed"] is True
    assert res_pass["total_marks"] == Decimal("70.00")
    assert res_pass["letter_grade"] == "D"
    assert res_pass["grade_point"] == Decimal("1.00")

    # 25 in Paper 1 + 30 in Paper 2 = 55/200 (27.5%) -> Below combined pass mark 66 -> Grade F
    res_fail = calculate_combined_paper(
        paper_1_marks=Decimal("25.00"),
        paper_1_full=Decimal("100.00"),
        paper_2_marks=Decimal("30.00"),
        paper_2_full=Decimal("100.00"),
        combined_pass_marks=Decimal("66.00"),
        scale=bd_scale,
    )
    assert res_fail["is_passed"] is False
    assert res_fail["letter_grade"] == "F"
    assert res_fail["grade_point"] == Decimal("0.00")


@pytest.mark.django_db
def test_golden_case_1_without_fourth_subject(bd_scale):
    """Golden Case 1: 6 mandatory subjects (5.0, 5.0, 4.0, 3.5, 4.0, 5.0).
    Sum = 26.50 / 6 = 4.42 (Grade A).
    """
    mandatory_gps = [
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("4.00"),
        Decimal("3.50"),
        Decimal("4.00"),
        Decimal("5.00"),
    ]
    final_gpa, gpa_no_4th, bonus, final_grade, is_passed = calculate_final_gpa(
        mandatory_subject_grades=mandatory_gps,
        fourth_subject_grade=None,
        scale=bd_scale,
    )
    assert is_passed is True
    assert bonus == Decimal("0.00")
    assert gpa_no_4th == Decimal("4.42")
    assert final_gpa == Decimal("4.42")
    assert final_grade == "A"


@pytest.mark.django_db
def test_golden_case_2_with_fourth_subject_elevation(bd_scale):
    """Golden Case 2: 6 mandatory subjects (sum = 29.00), GPA without 4th = 4.83.
    4th subject GP = 5.00 -> bonus = 3.00.
    Total = 32.00 / 6 = 5.33 -> capped at 5.00 (Grade A+).
    """
    mandatory_gps = [
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("4.00"),
    ]
    fourth_gp = Decimal("5.00")

    final_gpa, gpa_no_4th, bonus, final_grade, is_passed = calculate_final_gpa(
        mandatory_subject_grades=mandatory_gps,
        fourth_subject_grade=fourth_gp,
        scale=bd_scale,
    )
    assert is_passed is True
    assert bonus == Decimal("3.00")
    assert gpa_no_4th == Decimal("4.83")
    assert final_gpa == Decimal("5.00")
    assert final_grade == "A+"


@pytest.mark.django_db
def test_golden_case_3_mandatory_subject_failure(bd_scale):
    """Golden Case 3: Student achieves GP 5.00 in 5 subjects, but GP 0.00 (F) in English.
    Result: is_passed = False, final_gpa = 0.00, final_grade = 'F'.
    """
    mandatory_gps = [
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("5.00"),
        Decimal("0.00"),  # Failed English
    ]
    fourth_gp = Decimal("5.00")

    final_gpa, gpa_no_4th, bonus, final_grade, is_passed = calculate_final_gpa(
        mandatory_subject_grades=mandatory_gps,
        fourth_subject_grade=fourth_gp,
        scale=bd_scale,
    )
    assert is_passed is False
    assert final_gpa == Decimal("0.00")
    assert final_grade == "F"


@pytest.mark.django_db
def test_deterministic_student_ranking():
    """Verify tie-breaking hierarchy:
    1. Passed before failed
    2. GPA descending
    3. Total marks descending
    4. Roll number ascending
    """
    records = [
        {
            "student_id": "S1",
            "is_passed": True,
            "final_gpa": Decimal("5.00"),
            "total_marks": Decimal("550.00"),
            "roll_no": 2,
            "section_id": "sec-a",
        },
        {
            "student_id": "S2",
            "is_passed": True,
            "final_gpa": Decimal("5.00"),
            "total_marks": Decimal("580.00"),
            "roll_no": 5,
            "section_id": "sec-a",
        },  # Higher marks -> Class Pos 1
        {
            "student_id": "S3",
            "is_passed": True,
            "final_gpa": Decimal("4.50"),
            "total_marks": Decimal("520.00"),
            "roll_no": 1,
            "section_id": "sec-b",
        },
        {
            "student_id": "S4",
            "is_passed": False,
            "final_gpa": Decimal("0.00"),
            "total_marks": Decimal("400.00"),
            "roll_no": 3,
            "section_id": "sec-b",
        },  # Failed -> Last
    ]
    ranked = sort_and_rank_students(records)
    assert ranked[0]["student_id"] == "S2"  # 5.00 GPA, 580 marks
    assert ranked[0]["class_position"] == 1
    assert ranked[1]["student_id"] == "S1"  # 5.00 GPA, 550 marks
    assert ranked[1]["class_position"] == 2
    assert ranked[2]["student_id"] == "S3"  # 4.50 GPA
    assert ranked[2]["class_position"] == 3
    assert ranked[3]["student_id"] == "S4"  # Failed
    assert ranked[3]["class_position"] == 4


@pytest.mark.django_db
def test_cumulative_cgpa_calculation(bd_scale):
    """Test annual cumulative CGPA with 30% Half-Yearly + 70% Annual weightage."""
    terms = [
        {
            "exam_id": "exam-1",
            "exam_name": "Half-Yearly",
            "final_gpa": "4.50",
            "total_marks": "450.00",
            "is_passed": True,
        },
        {
            "exam_id": "exam-2",
            "exam_name": "Annual",
            "final_gpa": "5.00",
            "total_marks": "500.00",
            "is_passed": True,
        },
    ]
    rules = [
        {"exam_id": "exam-1", "weightage_percentage": "30.00"},
        {"exam_id": "exam-2", "weightage_percentage": "70.00"},
    ]
    # CGPA = (4.50 * 0.30) + (5.00 * 0.70) = 1.35 + 3.50 = 4.85 (Grade A)
    res = calculate_cumulative_cgpa(terms, rules, bd_scale)
    assert res["cumulative_gpa"] == Decimal("4.85")
    assert res["cumulative_grade"] == "A"
    assert res["is_passed"] is True
    assert res["promotion_recommended"] is True
