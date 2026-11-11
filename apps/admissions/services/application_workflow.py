"""Admission application workflow and state machine management."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.admissions.models import (
    AdmissionCircular,
    Application,
    ApplicationStatus,
    CircularStatus,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    ApplicationStatus.DRAFT: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.PAID,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.PAID: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.TEST_SCHEDULED,
        ApplicationStatus.ADMITTED,
        ApplicationStatus.WAITLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.TEST_SCHEDULED: {
        ApplicationStatus.ADMITTED,
        ApplicationStatus.WAITLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.WAITLISTED: {
        ApplicationStatus.ADMITTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.ADMITTED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}


def generate_application_number(circular: AdmissionCircular) -> str:
    """Generate human-friendly unique application number: ADM-{session.name}-{sequence:05d}."""
    session_name = circular.session.name.replace(" ", "")
    prefix = f"ADM-{session_name}-"
    # Find current max count for this prefix
    last_app = (
        Application.objects.filter(
            institution_id=circular.institution_id,
            application_no__startswith=prefix,
        )
        .order_by("-application_no")
        .first()
    )
    if last_app:
        try:
            last_seq = int(last_app.application_no.split("-")[-1])
            seq = last_seq + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:05d}"


def validate_applicant_eligibility(
    circular: AdmissionCircular,
    dob: date,
    previous_gpa: Decimal | None = None,
) -> None:
    """Validates applicant against circular's age and GPA requirements."""
    criteria = circular.eligibility_criteria or {}

    today = timezone.localdate()
    age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    min_age = criteria.get("min_age_years")
    if min_age is not None and age_years < min_age:
        raise ValidationError(
            f"Applicant age ({age_years} years) is below minimum age requirement of {min_age} years."
        )

    max_age = criteria.get("max_age_years")
    if max_age is not None and age_years > max_age:
        raise ValidationError(
            f"Applicant age ({age_years} years) exceeds maximum age requirement of {max_age} years."
        )

    min_gpa = criteria.get("min_gpa")
    if min_gpa is not None:
        if previous_gpa is None or previous_gpa < Decimal(str(min_gpa)):
            raise ValidationError(
                f"Applicant GPA ({previous_gpa}) does not meet the minimum requirement of {min_gpa}."
            )


def check_duplicate_application(
    *,
    circular: AdmissionCircular,
    birth_reg_no: str,
    dob: date,
    exclude_id: UUID | str | None = None,
) -> None:
    """Ensures duplicate applications with same Birth Registration Number & DOB are prevented."""
    qs = Application.objects.filter(
        circular=circular,
        birth_reg_no=birth_reg_no.strip(),
        dob=dob,
    )
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    if qs.exists():
        raise ValidationError(
            "An application has already been submitted for this child with the same Birth Certificate Number and Date of Birth."
        )


def transition_application_status(
    *,
    application: Application,
    new_status: str,
    notes: str = "",
) -> Application:
    """Enforces state machine rules when advancing application status."""
    current_status = application.status
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition application from '{application.get_status_display()}' to '{new_status}'."
        )

    application.status = new_status
    if notes:
        if application.notes:
            application.notes += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
        else:
            application.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {notes}"

    if new_status == ApplicationStatus.SUBMITTED and not application.submitted_at:
        application.submitted_at = timezone.now()

    application.save(update_fields=["status", "notes", "submitted_at", "updated_at"])
    return application


def submit_application(application_id: UUID | str) -> Application:
    """Submits a draft application, validating circular open dates and auto-progressing if free."""
    with transaction.atomic():
        application = Application.objects.select_for_update().get(id=application_id)
        circular = application.circular

        if circular.status != CircularStatus.PUBLISHED:
            raise ValidationError(
                "Cannot submit application because circular is not currently open/published."
            )

        today = timezone.localdate()
        if today < circular.form_open_date:
            raise ValidationError(f"Application submissions open on {circular.form_open_date}.")
        if today > circular.form_close_date:
            raise ValidationError(f"Application submissions closed on {circular.form_close_date}.")

        # Advance to SUBMITTED
        transition_application_status(
            application=application,
            new_status=ApplicationStatus.SUBMITTED,
            notes="Application submitted online by guardian.",
        )

        # If zero fee, automatically mark as PAID
        if circular.application_fee == Decimal("0.00"):
            transition_application_status(
                application=application,
                new_status=ApplicationStatus.PAID,
                notes="Zero application fee; automatically marked as paid.",
            )

    return application
