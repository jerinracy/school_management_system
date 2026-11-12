"""Online Quiz lifecycle and auto-grading service."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.homework.models import Quiz, QuizAttempt, QuizAttemptStatus, QuizOption
from apps.students.models import Student


@transaction.atomic
def recalculate_quiz_total_marks(quiz: Quiz) -> Quiz:
    """Recalculate Quiz.total_marks from sum of its QuizQuestion marks."""
    total = quiz.questions.aggregate(total=Sum("marks"))["total"] or Decimal("0.00")
    quiz.total_marks = total
    quiz.save(update_fields=["total_marks", "updated_at"])
    return quiz


@transaction.atomic
def start_quiz_attempt(
    quiz: Quiz,
    student: Student,
    now: Any = None,
) -> QuizAttempt:
    """Start or resume a timed QuizAttempt enforcing schedule window and attempt limit."""
    if quiz.institution_id != student.institution_id:
        raise ValidationError("Student does not belong to quiz institution.")
    if not quiz.is_published:
        raise ValidationError("Quiz is not published.")

    current_time = now or timezone.now()
    if current_time < quiz.starts_at:
        raise ValidationError("Quiz has not started yet.")
    if current_time > quiz.ends_at:
        raise ValidationError("Quiz submission window has closed.")

    existing_in_progress = QuizAttempt.objects.filter(
        quiz=quiz,
        student=student,
        status=QuizAttemptStatus.IN_PROGRESS,
    ).first()
    if existing_in_progress:
        return existing_in_progress

    completed_count = QuizAttempt.objects.filter(quiz=quiz, student=student).count()
    if completed_count >= quiz.max_attempts:
        raise ValidationError(f"Maximum attempts ({quiz.max_attempts}) reached for this quiz.")

    return QuizAttempt.objects.create(
        institution=quiz.institution,
        quiz=quiz,
        student=student,
        attempt_number=completed_count + 1,
        started_at=current_time,
        status=QuizAttemptStatus.IN_PROGRESS,
    )


@transaction.atomic
def submit_quiz_attempt(
    attempt: QuizAttempt,
    answers: dict[str, str],
    now: Any = None,
) -> QuizAttempt:
    """Auto-grade objective answers and finalize QuizAttempt."""
    if attempt.status != QuizAttemptStatus.IN_PROGRESS:
        raise ValidationError("This quiz attempt has already been submitted.")

    current_time = now or timezone.now()
    quiz = attempt.quiz
    questions = list(quiz.questions.prefetch_related("options").all())

    correct_option_by_question: dict[str, set[str]] = {}
    marks_by_question: dict[str, Decimal] = {}
    for q in questions:
        qid = str(q.id)
        marks_by_question[qid] = q.marks
        correct_option_by_question[qid] = {str(opt.id) for opt in q.options.all() if opt.is_correct}

    # Verify supplied option IDs belong to this quiz
    valid_option_ids = {
        str(oid)
        for oid in QuizOption.objects.filter(question__quiz=quiz).values_list("id", flat=True)
    }

    normalized_answers: dict[str, str] = {}
    score = Decimal("0.00")
    for qid, selected_opt in answers.items():
        qid_str = str(qid)
        opt_str = str(selected_opt)
        if qid_str not in marks_by_question or opt_str not in valid_option_ids:
            continue
        normalized_answers[qid_str] = opt_str
        if opt_str in correct_option_by_question.get(qid_str, set()):
            score += marks_by_question[qid_str]

    attempt.answers_json = normalized_answers
    attempt.score = score
    attempt.submitted_at = current_time
    attempt.status = QuizAttemptStatus.GRADED
    attempt.save(update_fields=["answers_json", "score", "submitted_at", "status", "updated_at"])
    return attempt
