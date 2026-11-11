"""Services package for Results and Grading Engine."""

from apps.results.services.analytics_service import (
    get_promotion_eligibility_feed,
    get_weak_students_analytics,
)
from apps.results.services.grading_engine import (
    calculate_combined_paper,
    calculate_cumulative_cgpa,
    calculate_final_gpa,
    evaluate_component_pass,
    evaluate_subject_marks,
    sort_and_rank_students,
)
from apps.results.services.grading_scale_service import (
    get_default_grading_scale,
    resolve_grade_for_gpa,
    resolve_grade_for_percentage,
    seed_default_bd_grading_scale,
)
from apps.results.services.publication_service import (
    approve_exam_results,
    can_view_exam_result,
    publish_exam_results,
    unpublish_exam_results,
)
from apps.results.services.report_card_service import (
    create_or_update_report_card,
    generate_bulk_report_cards_zip,
    generate_student_report_card_pdf,
)
from apps.results.services.result_processor import (
    tabulate_cumulative_results,
    tabulate_exam_results,
)
from apps.results.services.tabulation_service import (
    create_tabulation_sheet_record,
    generate_tabulation_excel,
    generate_tabulation_pdf,
)

__all__ = [
    "approve_exam_results",
    "calculate_combined_paper",
    "calculate_cumulative_cgpa",
    "calculate_final_gpa",
    "can_view_exam_result",
    "create_or_update_report_card",
    "create_tabulation_sheet_record",
    "evaluate_component_pass",
    "evaluate_subject_marks",
    "generate_bulk_report_cards_zip",
    "generate_student_report_card_pdf",
    "generate_tabulation_excel",
    "generate_tabulation_pdf",
    "get_default_grading_scale",
    "get_promotion_eligibility_feed",
    "get_weak_students_analytics",
    "publish_exam_results",
    "resolve_grade_for_gpa",
    "resolve_grade_for_percentage",
    "seed_default_bd_grading_scale",
    "sort_and_rank_students",
    "tabulate_cumulative_results",
    "tabulate_exam_results",
    "unpublish_exam_results",
]
