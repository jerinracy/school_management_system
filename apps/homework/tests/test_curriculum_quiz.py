"""Tests for Syllabus progress tracking and Lite Online Quiz auto-grading."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.academics.models import ClassLevel, Subject
from apps.homework.models import (
    QuestionType,
    Quiz,
    QuizAttemptStatus,
    QuizOption,
    QuizQuestion,
    SyllabusStatus,
    SyllabusTopic,
)
from apps.homework.services import (
    get_subject_syllabus_summary,
    recalculate_quiz_total_marks,
    start_quiz_attempt,
    submit_quiz_attempt,
    update_syllabus_topic_progress,
)
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import Gender, Student


@pytest.mark.django_db
class TestCurriculumAndQuiz:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Comilla Victoria Collegiate School",
            name_bn="কুমিল্লা ভিক্টোরিয়া কলেজিয়েট স্কুল",
        )
        self.session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.class_8 = ClassLevel.objects.create(
            institution=self.inst, name="Class 8", code="C08", order=8
        )
        self.subject = Subject.objects.create(
            institution=self.inst, code="107", name_en="English 1st Paper", name_bn="ইংরেজি ১ম পত্র"
        )
        self.student = Student.objects.create(
            institution=self.inst,
            student_id="CVC-08-001",
            name_en="Fahim Chowdhury",
            name_bn="ফাহিম চৌধুরী",
            dob=date(2012, 3, 2),
            gender=Gender.MALE,
            admission_date=date(2026, 1, 5),
        )

    def test_syllabus_topic_progress_and_summary(self) -> None:
        t1 = SyllabusTopic.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_8,
            subject=self.subject,
            title="Unit 1: Articles & Prepositions",
            order=1,
        )
        t2 = SyllabusTopic.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_8,
            subject=self.subject,
            title="Unit 2: Voice Change",
            order=2,
        )
        update_syllabus_topic_progress(t1, 100)
        update_syllabus_topic_progress(t2, 50)
        t1.refresh_from_db()
        t2.refresh_from_db()

        assert t1.status == SyllabusStatus.COMPLETED
        assert t1.completed_at is not None
        assert t2.status == SyllabusStatus.IN_PROGRESS

        summary = get_subject_syllabus_summary(
            self.inst, self.session, self.class_8, subject=self.subject
        )
        assert summary["total_topics"] == 2
        assert summary["completed_topics"] == 1
        assert summary["in_progress_topics"] == 1
        assert summary["average_completion_percentage"] == 75

    def test_quiz_attempt_limits_and_auto_grading(self) -> None:
        now = timezone.now()
        quiz = Quiz.objects.create(
            institution=self.inst,
            session=self.session,
            class_level=self.class_8,
            subject=self.subject,
            title="Grammar Quick Check",
            starts_at=now - timedelta(minutes=30),
            ends_at=now + timedelta(hours=2),
            max_attempts=1,
            pass_marks=Decimal("2.00"),
            is_published=True,
        )
        q1 = QuizQuestion.objects.create(
            institution=self.inst,
            quiz=quiz,
            question_text="Choose the correct article: ___ honest man",
            question_type=QuestionType.MCQ,
            marks=Decimal("2.00"),
            order=1,
        )
        o1a = QuizOption.objects.create(
            institution=self.inst, question=q1, option_text="a", is_correct=False, order=1
        )
        o1b = QuizOption.objects.create(
            institution=self.inst, question=q1, option_text="an", is_correct=True, order=2
        )

        q2 = QuizQuestion.objects.create(
            institution=self.inst,
            quiz=quiz,
            question_text="Earth revolves around the sun.",
            question_type=QuestionType.TRUE_FALSE,
            marks=Decimal("1.00"),
            order=2,
        )
        o2_true = QuizOption.objects.create(
            institution=self.inst, question=q2, option_text="True", is_correct=True, order=1
        )
        o2_false = QuizOption.objects.create(
            institution=self.inst, question=q2, option_text="False", is_correct=False, order=2
        )

        recalculate_quiz_total_marks(quiz)
        quiz.refresh_from_db()
        assert quiz.total_marks == Decimal("3.00")

        attempt = start_quiz_attempt(quiz, self.student, now=now)
        # Resuming while in progress returns same attempt
        assert start_quiz_attempt(quiz, self.student, now=now).id == attempt.id

        # Pick 1 correct (2 pts) and 1 wrong (0 pts) -> keep option references used cleanly
        assert o1a.id != o1b.id and o2_true.id != o2_false.id
        graded = submit_quiz_attempt(
            attempt,
            answers={str(q1.id): str(o1b.id), str(q2.id): str(o2_false.id)},
            now=now,
        )
        assert graded.status == QuizAttemptStatus.GRADED
        assert graded.score == Decimal("2.00")

        # Exceeding max_attempts=1 fails
        with pytest.raises(ValidationError, match="Maximum attempts"):
            start_quiz_attempt(quiz, self.student, now=now)
