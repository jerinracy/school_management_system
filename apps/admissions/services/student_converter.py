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
    section_id: UUID | str | None = None,
    roll_no: int | None = None,
) -> dict[str, Any]:
    """Conversion from an ADMITTED application to a Student profile.

    If section_id and roll_no are provided, executes full student enrollment.
    Otherwise returns structured intake payload ready for administrative section assignment.
    """
    application = Application.objects.select_related("circular").get(id=application_id)
    if application.status != ApplicationStatus.ADMITTED:
        raise ValidationError(
            f"Cannot convert application to student; status must be ADMITTED (currently {application.status})."
        )

    if section_id and roll_no:
        from apps.students.services.intake import admit_from_application

        student, enrollment = admit_from_application(
            application_id=application_id,
            section_id=section_id,
            roll_no=roll_no,
        )
        return {
            "status": "enrolled",
            "message": f"Successfully enrolled student {student.student_id}.",
            "student_id": student.student_id,
            "roll_no": enrollment.roll_no,
        }

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
