"""Admissions business service exports."""

from apps.admissions.services.application_workflow import (
    generate_application_number,
    submit_application,
    transition_application_status,
    validate_applicant_eligibility,
)
from apps.admissions.services.lottery import conduct_lottery_draw
from apps.admissions.services.merit_calculator import generate_merit_list
from apps.admissions.services.student_converter import convert_admitted_application_to_student

__all__ = [
    "generate_application_number",
    "submit_application",
    "transition_application_status",
    "validate_applicant_eligibility",
    "conduct_lottery_draw",
    "generate_merit_list",
    "convert_admitted_application_to_student",
]
