"""Management command to export a student's personal data bundle for privacy requests."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.audit.models import AuditAction
from apps.audit.services.audit_service import record as audit_record
from apps.fees.models import Invoice
from apps.guardians.models import StudentGuardian
from apps.students.models import Student


class Command(BaseCommand):
    help = "Export a student's personal data bundle (JSON) for privacy/compliance requests."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("student_uuid", type=str, help="UUID of the Student record.")
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Destination JSON file path.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        student = (
            Student.objects.select_related("institution")
            .filter(id=options["student_uuid"], is_deleted=False)
            .first()
        )
        if student is None:
            raise CommandError("Student not found.")

        payload: dict[str, Any] = {
            "student": {
                "id": str(student.id),
                "institution_id": str(student.institution_id),
                "student_id": student.student_id,
                "name_en": student.name_en,
                "name_bn": student.name_bn,
                "dob": student.dob.isoformat(),
                "gender": student.gender,
                "admission_date": student.admission_date.isoformat(),
            },
            "guardians": list(
                StudentGuardian.objects.filter(student=student, guardian__is_deleted=False).values(
                    "relation", "is_primary", "guardian__name_en", "guardian__phone"
                )
            ),
            "attendance_count": student.daily_attendances.filter(is_deleted=False).count(),
            "invoices": [
                {
                    "invoice_number": inv.invoice_number,
                    "total_payable": str(inv.total_payable),
                    "paid_amount": str(inv.paid_amount),
                    "due_amount": str(inv.due_amount),
                    "status": inv.status,
                }
                for inv in Invoice.objects.filter(student=student, is_deleted=False)
            ],
        }

        out_path = Path(options["output"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

        audit_record(
            action=AuditAction.EXPORT,
            module="core",
            target_model="Student",
            target_object_id=student.id,
            target_repr=f"Privacy export for {student.student_id}",
            institution=student.institution,
        )
        self.stdout.write(self.style.SUCCESS(f"Privacy bundle written to {out_path}"))
