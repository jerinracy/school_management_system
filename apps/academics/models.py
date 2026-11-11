"""Academic models for School Management System."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import TenantOwnedModel


class MediumType(models.TextChoices):
    BANGLA = "bangla", "Bangla Medium"
    ENGLISH_VERSION = "english_version", "English Version (NCTB)"
    ENGLISH_MEDIUM = "english_medium", "English Medium (Cambridge/Edexcel)"
    MADRASA = "madrasa", "Madrasa (Dakhil/Alim)"


class SubjectType(models.TextChoices):
    COMPULSORY = "compulsory", "Compulsory"
    OPTIONAL = "optional", "Optional / Elective"
    FOURTH_SUBJECT = "fourth_subject", "4th Subject (Additional)"
    CO_CURRICULAR = "co_curricular", "Co-Curricular / Activity"


class RoomType(models.TextChoices):
    CLASSROOM = "classroom", "Classroom"
    LAB = "lab", "Laboratory"
    LIBRARY = "library", "Library"
    AUDITORIUM = "auditorium", "Auditorium"
    OTHER = "other", "Other"


class Weekday(models.IntegerChoices):
    SATURDAY = 0, "Saturday"
    SUNDAY = 1, "Sunday"
    MONDAY = 2, "Monday"
    TUESDAY = 3, "Tuesday"
    WEDNESDAY = 4, "Wednesday"
    THURSDAY = 5, "Thursday"
    FRIDAY = 6, "Friday"


class ClassLevel(TenantOwnedModel):
    """Represents an academic grade or level (e.g. Play, Class 1, Class 9, Class 12)."""

    name = models.CharField(
        max_length=64, help_text="Class name in English/Bangla (e.g. Class 9, দশম শ্রেণি)"
    )
    code = models.CharField(max_length=20, help_text="Short code (e.g. c09, c10)")
    order = models.PositiveSmallIntegerField(
        help_text="Numeric sequencing from lowest to highest grade (1..14)"
    )
    medium = models.CharField(
        max_length=20,
        choices=MediumType.choices,
        default=MediumType.BANGLA,
        db_index=True,
    )
    has_groups = models.BooleanField(
        default=False,
        help_text="Whether students branch into streams/groups (typically Class 9+ in Bangladesh)",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Class Level"
        verbose_name_plural = "Class Levels"
        ordering = ["medium", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_class_code_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "medium", "order"],
                name="unique_class_order_per_medium_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_medium_display()})"


class Group(TenantOwnedModel):
    """Academic stream/group (e.g. Science, Business Studies, Humanities)."""

    name = models.CharField(max_length=64, help_text="Group name (e.g. Science, বিজ্ঞান)")
    code = models.CharField(max_length=20, help_text="Unique code (e.g. SCI, BUS, HUM)")

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Academic Group"
        verbose_name_plural = "Academic Groups"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_group_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Section(TenantOwnedModel):
    """A classroom section within a class level, shift, and academic session."""

    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    shift = models.ForeignKey(
        "institutions.Shift",
        on_delete=models.CASCADE,
        related_name="sections",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=64, help_text="Section name (e.g. Padma, Section A)")
    capacity = models.PositiveIntegerField(default=50, help_text="Maximum student capacity")
    teacher_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_sections",
        help_text="Class teacher user account reference",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ["class_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_level", "shift", "session", "name"],
                name="unique_section_per_class_shift_session",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.class_level.name} - {self.name} ({self.session.name})"

    def clean(self) -> None:
        super().clean()
        if self.class_level_id and self.class_level.institution_id != self.institution_id:
            raise ValidationError(
                {"class_level": "Class level must belong to the same institution."}
            )
        if self.shift_id and self.shift.institution_id != self.institution_id:
            raise ValidationError({"shift": "Shift must belong to the same institution."})
        if self.session_id and self.session.institution_id != self.institution_id:
            raise ValidationError({"session": "Session must belong to the same institution."})


class Subject(TenantOwnedModel):
    """Subject catalog entry for an institution."""

    code = models.CharField(
        max_length=20, help_text="Subject board/internal code (e.g. 101, 107, 137)"
    )
    name_bn = models.CharField(
        max_length=128, help_text="Bangla title (e.g. বাংলা ১ম পত্র, পদার্থবিজ্ঞান)"
    )
    name_en = models.CharField(
        max_length=128, help_text="English title (e.g. Bangla 1st Paper, Physics)"
    )
    type = models.CharField(
        max_length=20,
        choices=SubjectType.choices,
        default=SubjectType.COMPULSORY,
        db_index=True,
    )
    has_papers = models.BooleanField(
        default=False,
        help_text="Whether this subject has multiple papers (e.g. 1st Paper and 2nd Paper)",
    )
    paper_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Paper number (1 or 2) when has_papers is True",
    )
    marks_components_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default marks components, e.g. {'creative': {'full': 70, 'pass': 23}, 'mcq': {'full': 30, 'pass': 10}}",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_subject_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en} ({self.name_bn})"


class ClassSubject(TenantOwnedModel):
    """Subject offering assigned to a class level, academic stream, and session."""

    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        related_name="class_subjects",
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_subjects",
        help_text="Required when class_level.has_groups is True; null for common subjects",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="class_subjects",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="class_offerings",
    )
    full_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text="Total marks allocated (e.g. 100 or 50)",
    )
    pass_rule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Passing rules (e.g. {'aggregate_pass': 33, 'component_pass_required': true})",
    )
    credit_weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="Credit weight for GPA calculation",
    )
    is_optional_elective = models.BooleanField(
        default=False,
        help_text="True if this subject can be chosen as an optional/4th subject",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Class Subject Offering"
        verbose_name_plural = "Class Subject Offerings"
        ordering = ["class_level", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_level", "group", "session", "subject"],
                name="unique_subject_per_class_group_session",
            ),
        ]

    def __str__(self) -> str:
        group_str = f" [{self.group.name}]" if self.group else ""
        return f"{self.class_level.name}{group_str} - {self.subject.name_en} ({self.session.name})"

    def clean(self) -> None:
        super().clean()
        if self.class_level_id and self.class_level.institution_id != self.institution_id:
            raise ValidationError(
                {"class_level": "Class level must belong to the same institution."}
            )
        if self.subject_id and self.subject.institution_id != self.institution_id:
            raise ValidationError({"subject": "Subject must belong to the same institution."})
        if self.session_id and self.session.institution_id != self.institution_id:
            raise ValidationError({"session": "Session must belong to the same institution."})
        if self.group_id and self.group and self.group.institution_id != self.institution_id:
            raise ValidationError({"group": "Group must belong to the same institution."})
        if (
            self.class_level_id
            and self.class_level.has_groups
            and not self.group_id
            and self.subject.type != SubjectType.COMPULSORY
        ):
            # Classes with groups may still have common compulsory subjects (e.g. Bangla/English)
            pass


class Room(TenantOwnedModel):
    """Physical room or hall for class teaching or activities."""

    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rooms",
        help_text="Branch location for this room",
    )
    name = models.CharField(
        max_length=64, help_text="Room name / number (e.g. Room 302, Physics Lab)"
    )
    capacity = models.PositiveIntegerField(default=60, help_text="Seating capacity")
    type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.CLASSROOM,
        db_index=True,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Room"
        verbose_name_plural = "Rooms"
        ordering = ["branch", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "branch", "name"],
                name="unique_room_per_branch",
            ),
        ]

    def __str__(self) -> str:
        branch_name = f" ({self.branch.name})" if self.branch else ""
        return f"{self.name}{branch_name}"


class Period(TenantOwnedModel):
    """Class timetable period definition per shift."""

    shift = models.ForeignKey(
        "institutions.Shift",
        on_delete=models.CASCADE,
        related_name="periods",
    )
    name = models.CharField(max_length=64, help_text="Period name (e.g. 1st Period, Tiffin Break)")
    start_time = models.TimeField()
    end_time = models.TimeField()
    order = models.PositiveSmallIntegerField(help_text="Order in the day (1, 2, 3...)")
    is_break = models.BooleanField(default=False, help_text="True if this is a tiffin/prayer break")

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Period"
        verbose_name_plural = "Periods"
        ordering = ["shift", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "order"],
                name="unique_period_order_per_shift",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.shift.name} - {self.name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"

    def clean(self) -> None:
        super().clean()
        if self.shift_id and self.shift.institution_id != self.institution_id:
            raise ValidationError({"shift": "Shift must belong to the same institution."})
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "Period end_time must be after start_time."})


class RoutineSlot(TenantOwnedModel):
    """Weekly class routine / timetable slot."""

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="routine_slots",
    )
    weekday = models.IntegerField(
        choices=Weekday.choices,
        help_text="Day of the week (0=Saturday, 6=Friday)",
        db_index=True,
    )
    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        related_name="routine_slots",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="routine_slots",
    )
    teacher_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routine_slots",
        help_text="Assigned teacher user account",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routine_slots",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Routine Slot"
        verbose_name_plural = "Routine Slots"
        ordering = ["weekday", "period__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "weekday", "period"],
                name="unique_slot_per_section_weekday_period",
            ),
            models.UniqueConstraint(
                fields=["room", "weekday", "period"],
                condition=Q(room__isnull=False),
                name="unique_slot_per_room_weekday_period",
            ),
            models.UniqueConstraint(
                fields=["teacher_user", "weekday", "period"],
                condition=Q(teacher_user__isnull=False),
                name="unique_slot_per_teacher_weekday_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section} | {self.get_weekday_display()} - {self.period.name}: {self.subject.name_en}"

    def clean(self) -> None:
        super().clean()
        if self.section_id and self.section.institution_id != self.institution_id:
            raise ValidationError({"section": "Section must belong to the same institution."})
        if self.period_id and self.period.institution_id != self.institution_id:
            raise ValidationError({"period": "Period must belong to the same institution."})
        if self.subject_id and self.subject.institution_id != self.institution_id:
            raise ValidationError({"subject": "Subject must belong to the same institution."})
        if self.room_id and self.room and self.room.institution_id != self.institution_id:
            raise ValidationError({"room": "Room must belong to the same institution."})
        if (
            self.teacher_user_id
            and self.teacher_user
            and self.teacher_user.institution_id != self.institution_id
        ):
            raise ValidationError({"teacher_user": "Teacher must belong to the same institution."})
        if self.period.is_break:
            raise ValidationError(
                {"period": "Cannot schedule a routine slot during a break period."}
            )


class SubstituteAssignment(TenantOwnedModel):
    """Temporary teacher substitution for a specific date's routine slot."""

    routine_slot = models.ForeignKey(
        RoutineSlot,
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    slot_date = models.DateField(help_text="Calendar date for this substitution")
    original_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="original_substitutions",
    )
    substitute_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="substitute_assignments",
    )
    reason = models.CharField(max_length=255, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Substitute Assignment"
        verbose_name_plural = "Substitute Assignments"
        ordering = ["-slot_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["routine_slot", "slot_date"],
                name="unique_substitution_per_slot_date",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.slot_date} | Slot {self.routine_slot_id} -> {self.substitute_teacher.full_name}"
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.substitute_teacher_id
            and self.substitute_teacher.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"substitute_teacher": "Substitute teacher must belong to the same institution."}
            )
        if self.original_teacher_id and self.substitute_teacher_id == self.original_teacher_id:
            raise ValidationError(
                {"substitute_teacher": "Substitute teacher cannot be the original teacher."}
            )
