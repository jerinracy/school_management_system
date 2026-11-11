"""Examination seating arrangement generator service."""

from typing import Any
from uuid import UUID

from django.db import transaction

from apps.exams.models import Exam, ExamSubject, SeatPlan
from apps.students.models import EnrollmentStatus, StudentEnrollment


def _interleave_students(enrollments: list[StudentEnrollment]) -> list[StudentEnrollment]:
    class_buckets: dict[UUID, list[StudentEnrollment]] = {}
    for enr in enrollments:
        class_buckets.setdefault(enr.class_level_id, []).append(enr)

    bucket_lists = list(class_buckets.values())
    max_len = max(len(b) for b in bucket_lists)
    result: list[StudentEnrollment] = []
    for i in range(max_len):
        for b in bucket_lists:
            if i < len(b):
                result.append(b[i])
    return result


def _allocate_seats(
    students: list[StudentEnrollment],
    room_configs: list[dict[str, Any]],
    institution: Any,
    exam: Exam,
    exam_subject: ExamSubject | None,
) -> list[SeatPlan]:
    created_seat_plans: list[SeatPlan] = []
    student_idx = 0
    total_students = len(students)

    for room in room_configs:
        room_no = str(room["room_number"])
        bench_count = int(room.get("bench_count", 20))
        seats_per_bench = int(room.get("seats_per_bench", 2))

        for b_idx in range(1, bench_count + 1):
            bench_label = f"B-{b_idx}"
            for s_idx in range(1, seats_per_bench + 1):
                if student_idx >= total_students:
                    return created_seat_plans

                enr = students[student_idx]
                plan = SeatPlan(
                    institution=institution,
                    exam=exam,
                    exam_subject=exam_subject,
                    room_number=room_no,
                    bench_label=bench_label,
                    seat_number=s_idx,
                    student=enr.student,
                    roll_number=enr.roll_no,
                    class_level=enr.class_level,
                    section=enr.section,
                )
                created_seat_plans.append(plan)
                student_idx += 1

    return created_seat_plans


@transaction.atomic
def generate_seat_plans_for_exam(
    exam_id: UUID | str,
    room_configs: list[dict[str, Any]],
    interleave: bool = True,
    exam_subject_id: UUID | str | None = None,
) -> list[SeatPlan]:
    """Generate seat arrangements across examination rooms and benches."""
    exam = Exam.objects.select_related("institution", "session").get(id=exam_id)
    institution = exam.institution

    exam_subject = None
    if exam_subject_id:
        exam_subject = ExamSubject.objects.get(id=exam_subject_id, exam=exam)

    # Clean existing seat plans for this exam/subject
    qs_del = SeatPlan.objects.filter(exam=exam)
    if exam_subject:
        qs_del = qs_del.filter(exam_subject=exam_subject)
    qs_del.delete()

    # Find enrolled students participating in this exam
    target_classes = exam.target_classes.all()
    enrollment_qs = (
        StudentEnrollment.objects.filter(
            institution=institution,
            session=exam.session,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("student", "class_level", "section")
        .order_by("class_level__order", "roll_no")
    )

    if target_classes.exists():
        enrollment_qs = enrollment_qs.filter(class_level__in=target_classes)

    enrollments = list(enrollment_qs)
    if not enrollments:
        return []

    if interleave and target_classes.count() > 1:
        students_to_seat = _interleave_students(enrollments)
    else:
        students_to_seat = enrollments

    created_seat_plans = _allocate_seats(
        students=students_to_seat,
        room_configs=room_configs,
        institution=institution,
        exam=exam,
        exam_subject=exam_subject,
    )

    SeatPlan.objects.bulk_create(created_seat_plans)
    return created_seat_plans
