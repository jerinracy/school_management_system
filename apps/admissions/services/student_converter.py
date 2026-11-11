"""Student converter service stub.

Converts an admitted admission application into a permanent Student profile.
Full student models and enrollment tables land in Task 06.
"""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.admissions.models import Application, ApplicationStatus


def convert_admitted_application_to_student(
    application_id: UUID | str,
) -> dict[str, Any]:
    """Stub conversion from an ADMITTED application to a Student profile.

    Will be connected to apps.students.services.admit_from_application in Task 06.
    """
    application = Application.objects.get(id=application_id)
    if application.status != ApplicationStatus.ADMITTED:
        raise ValidationError(
            f"Cannot convert application to student; status must be ADMITTED (currently {application.status})."
        )

    # Return structured payload ready for Task 06 Student intake
    return {
        "status": "pending_student_intake",
        "message": "Application is ready for student enrollment in Task 06.",
        "applicant_info": {
            "application_no": application.application_no,
            "name_bn": application.name_bn,
            "name_en": application.name_en,
            "dob": str(application.dob),
            "gender": application.gender,
            "birth_reg_no": application.birth_reg_no,
            "guardian_name": application.guardian_name,
            "guardian_phone": application.guardian_phone,
            "class_level_id": str(application.circular.class_level_id),
            "session_id": str(application.circular.session_id),
        },
    }
