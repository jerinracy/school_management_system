"""Integration tests for exam eligibility, seat planning, admit cards, and mark entries."""

from datetime import date, time
from decimal import Decimal

import pytest

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.test_helpers import make_user
from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.exams.models import (
    AdmitCard,
    ClearanceStatus,
    Exam,
    ExamStatus,
    ExamSubject,
    ExamType,
    MarkEntry,
    MarkEntryLog,
    SeatPlan,
    StudentExamEligibility,
)
from apps.exams.services import (
    evaluate_exam_eligibility_for_exam,
    export_mark_entry_excel,
    generate_admit_card_pdf,
    generate_admit_cards_for_eligible_students,
    generate_seat_plans_for_exam,
    import_mark_entry_excel,
    lock_exam_subject_marks,
    save_single_mark_entry,
    unlock_exam_subject_marks,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import Staff
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model College",
        name_bn="ঢাকা মডেল কলেজ",
        eiin="332211",
        address_line="Dhanmondi, Dhaka",
    )


@pytest.fixture
def branch(db, institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Campus", code="MAIN")


@pytest.fixture
def academic_session(db, institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def shift(db, institution, branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="Morning Shift",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )


@pytest.fixture
def class_level_6(db, institution) -> ClassLevel:
    return ClassLevel.objects.create(institution=institution, name="Class 6", code="CLS-6", order=6)


@pytest.fixture
def class_level_7(db, institution) -> ClassLevel:
    return ClassLevel.objects.create(institution=institution, name="Class 7", code="CLS-7", order=7)


@pytest.fixture
def section_6a(db, institution, class_level_6, shift, academic_session) -> Section:
    return Section.objects.create(
        institution=institution,
        class_level=class_level_6,
        shift=shift,
        session=academic_session,
        name="Section A",
    )


@pytest.fixture
def section_7a(db, institution, class_level_7, shift, academic_session) -> Section:
    return Section.objects.create(
        institution=institution,
        class_level=class_level_7,
        shift=shift,
        session=academic_session,
        name="Section A",
    )


@pytest.fixture
def subject_math(db, institution) -> Subject:
    return Subject.objects.create(institution=institution, name_en="Mathematics", code="MTH-101")


@pytest.fixture
def exam(db, institution, academic_session, class_level_6, class_level_7) -> Exam:
    etype = ExamType.objects.create(institution=institution, name="Term Final", code="FINAL")
    exam_obj = Exam.objects.create(
        institution=institution,
        exam_type=etype,
        session=academic_session,
        name="Annual Final Examination 2026",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
        status=ExamStatus.SCHEDULED,
    )
    exam_obj.target_classes.add(class_level_6, class_level_7)
    return exam_obj


@pytest.fixture
def student_one(db, institution, academic_session, class_level_6, section_6a, shift) -> Student:
    s = Student.objects.create(
        institution=institution,
        student_id="STU-601",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        dob="2013-02-10",
        gender="male",
        admission_date="2026-01-01",
    )
    StudentEnrollment.objects.create(
        institution=institution,
        student=s,
        session=academic_session,
        class_level=class_level_6,
        section=section_6a,
        shift=shift,
        roll_no=1,
        enrollment_date=date(2026, 1, 1),
        status=EnrollmentStatus.ACTIVE,
    )
    return s


@pytest.fixture
def student_two(db, institution, academic_session, class_level_7, section_7a, shift) -> Student:
    s = Student.objects.create(
        institution=institution,
        student_id="STU-701",
        name_en="Sadia Sultana",
        name_bn="সাদিয়া সুলতানা",
        dob="2012-07-22",
        gender="female",
        admission_date="2026-01-01",
    )
    StudentEnrollment.objects.create(
        institution=institution,
        student=s,
        session=academic_session,
        class_level=class_level_7,
        section=section_7a,
        shift=shift,
        roll_no=1,
        enrollment_date=date(2026, 1, 1),
        status=EnrollmentStatus.ACTIVE,
    )
    return s


@pytest.mark.django_db
def test_exam_eligibility_and_admit_card_issuance(institution, exam, student_one):
    # Setup DailyAttendance: 8 present out of 10 working days = 80% (Regular)
    for day in range(1, 9):
        DailyAttendance.objects.create(
            institution=institution,
            student=student_one,
            date=date(2026, 10, day),
            status=AttendanceStatus.PRESENT,
        )
    for day in range(9, 11):
        DailyAttendance.objects.create(
            institution=institution,
            student=student_one,
            date=date(2026, 10, day),
            status=AttendanceStatus.ABSENT,
        )

    # 1. Evaluate eligibility
    eligibilities = evaluate_exam_eligibility_for_exam(exam.id)
    assert len(eligibilities) >= 1
    elig = StudentExamEligibility.objects.get(exam=exam, student=student_one)
    assert elig.attendance_percentage == Decimal("80.00")
    assert elig.clearance_status == ClearanceStatus.ELIGIBLE

    # 2. Generate admit cards
    cards = generate_admit_cards_for_eligible_students(exam.id)
    assert len(cards) >= 1
    card = AdmitCard.objects.get(exam=exam, student=student_one)
    assert card.card_number.startswith("ADM-2026-")

    # 3. Generate Admit Card PDF
    pdf_bytes = generate_admit_card_pdf(card.id)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


@pytest.mark.django_db
def test_seat_plan_generation_sequential_and_interleaved(exam, student_one, student_two):
    room_configs = [
        {"room_number": "201", "bench_count": 5, "seats_per_bench": 2},
    ]

    # Generate interleaved seat plan
    plans = generate_seat_plans_for_exam(
        exam_id=exam.id,
        room_configs=room_configs,
        interleave=True,
    )
    assert len(plans) == 2

    # Verify first seat is Class 6, second seat is Class 7 (interleaving)
    bench_one_seats = SeatPlan.objects.filter(exam=exam, bench_label="B-1").order_by("seat_number")
    assert bench_one_seats.count() == 2
    assert bench_one_seats[0].student == student_one
    assert bench_one_seats[1].student == student_two


@pytest.mark.django_db
def test_mark_entry_validation_locking_and_audit(
    institution, exam, class_level_6, subject_math, student_one
):
    user_teacher = make_user(
        username="math_teacher", phone="+8801700000081", institution=institution
    )
    staff_member = Staff.objects.create(
        institution=institution,
        user=user_teacher,
        employee_id="TCH-101",
        full_name_en="Azizul Haque",
        dob="1985-01-01",
        gender="male",
        joining_date="2020-01-01",
    )

    exam_subj = ExamSubject.objects.create(
        institution=institution,
        exam=exam,
        class_level=class_level_6,
        subject=subject_math,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("30.00"),
        practical_full_marks=Decimal("0.00"),
        assigned_teacher=staff_member,
    )

    # 1. Successful mark entry
    mark = save_single_mark_entry(
        exam_subject=exam_subj,
        student=student_one,
        user=user_teacher,
        creative_marks=Decimal("62.50"),
        mcq_marks=Decimal("28.00"),
        reason="Initial entry",
    )
    assert mark.total_marks == Decimal("90.50")
    assert mark.is_absent is False

    # 2. Update mark creates audit log
    mark_updated = save_single_mark_entry(
        exam_subject=exam_subj,
        student=student_one,
        user=user_teacher,
        creative_marks=Decimal("65.00"),
        mcq_marks=Decimal("28.00"),
        reason="Re-calculated CQ question 3",
    )
    assert mark_updated.total_marks == Decimal("93.00")
    log = MarkEntryLog.objects.filter(mark_entry=mark, field_name="creative_marks").first()
    assert log is not None
    assert log.old_value == "62.50"
    assert log.new_value == "65.00"
    assert "Re-calculated" in log.reason

    # 3. Lock marks
    admin_user = make_user(
        username="exam_admin", phone="+8801700000082", institution=institution, role="admin"
    )
    lock_exam_subject_marks(exam_subj.id, user=admin_user)
    exam_subj.refresh_from_db()
    assert exam_subj.is_marks_locked is True

    # 4. Modifying locked mark raises error
    with pytest.raises(Exception) as exc:
        save_single_mark_entry(
            exam_subject=exam_subj,
            student=student_one,
            user=user_teacher,
            creative_marks=Decimal("60.00"),
        )
    assert "locked" in str(exc.value)

    # 5. Unlock marks allows modification again
    unlock_exam_subject_marks(
        exam_subj.id, user=admin_user, reason="Principal approval for correction"
    )
    exam_subj.refresh_from_db()
    assert exam_subj.is_marks_locked is False


@pytest.mark.django_db
def test_excel_export_and_import(institution, exam, class_level_6, subject_math, student_one):
    user_teacher = make_user(
        username="math_teacher2", phone="+8801700000083", institution=institution
    )
    staff_member = Staff.objects.create(
        institution=institution,
        user=user_teacher,
        employee_id="TCH-102",
        full_name_en="Rafiqul Islam",
        dob="1988-02-02",
        gender="male",
        joining_date="2021-01-01",
    )

    exam_subj = ExamSubject.objects.create(
        institution=institution,
        exam=exam,
        class_level=class_level_6,
        subject=subject_math,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("30.00"),
        assigned_teacher=staff_member,
    )

    # 1. Export Excel template
    excel_bytes = export_mark_entry_excel(exam_subj.id)
    assert len(excel_bytes) > 2000

    # 2. Modify Excel bytes in-memory and import
    import io

    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    ws = wb.active
    # Row 6 has student_one
    ws.cell(row=6, column=5, value=58.0)  # CQ
    ws.cell(row=6, column=6, value=26.0)  # MCQ
    modified_buf = io.BytesIO()
    wb.save(modified_buf)

    count, errors = import_mark_entry_excel(
        exam_subject_id=exam_subj.id,
        file_bytes=modified_buf.getvalue(),
        user=user_teacher,
    )
    assert count == 1
    assert len(errors) == 0

    entry = MarkEntry.objects.get(exam_subject=exam_subj, student=student_one)
    assert entry.creative_marks == Decimal("58.00")
    assert entry.mcq_marks == Decimal("26.00")
    assert entry.total_marks == Decimal("84.00")
