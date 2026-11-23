"""Academic models for School Management System."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


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


class ClassLevel(TenantOwnedModel, SoftDeleteMixin):
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
    shift = models.ForeignKey(
        "institutions.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_levels",
        help_text="Associated shift (optional; null means common across all shifts)",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_levels",
        help_text="Associated academic session (optional; null means common across all sessions)",
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_levels",
        help_text="Associated branch (optional; null means common across all branches)",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Class Level"
        verbose_name_plural = "Class Levels"
        ordering = ["medium", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_class_code_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "medium", "order"],
                condition=models.Q(is_deleted=False),
                name="unique_class_order_per_medium_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_medium_display()})"


class Group(TenantOwnedModel, SoftDeleteMixin):
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
                condition=models.Q(is_deleted=False),
                name="unique_group_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Section(TenantOwnedModel, SoftDeleteMixin):
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
    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sections",
        help_text="Associated branch (optional; null means inherited from shift or primary branch)",
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
    teacher_staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_sections",
        help_text="Class teacher official Staff profile reference",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ["class_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_level", "shift", "session", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_section_per_class_shift_session",
            ),
            models.UniqueConstraint(
                fields=["session", "teacher_user"],
                condition=models.Q(teacher_user__isnull=False, is_deleted=False),
                name="unique_class_teacher_user_per_session",
                violation_error_message="This teacher is already assigned as Class Teacher to another section in this academic session.",
            ),
            models.UniqueConstraint(
                fields=["session", "teacher_staff"],
                condition=models.Q(teacher_staff__isnull=False, is_deleted=False),
                name="unique_class_teacher_staff_per_session",
                violation_error_message="This teacher is already assigned as Class Teacher to another section in this academic session.",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.class_level.name} - {self.name} ({self.session.name})"

    def _sync_and_validate_teachers(self) -> None:
        """Bidirectional synchronization and session conflict check for class teachers."""
        if self.teacher_staff_id and not self.teacher_user_id:
            if getattr(self.teacher_staff, "user_id", None):
                self.teacher_user = self.teacher_staff.user
        elif self.teacher_user_id and not self.teacher_staff_id:
            from apps.staff.models import Staff

            stf = Staff.objects.filter(
                institution_id=self.institution_id,
                user_id=self.teacher_user_id,
                is_deleted=False,
            ).first()
            if stf:
                self.teacher_staff = stf

        if self.teacher_staff_id and self.session_id:
            conflict_staff = (
                Section.objects.filter(
                    session_id=self.session_id,
                    teacher_staff_id=self.teacher_staff_id,
                )
                .exclude(pk=self.pk)
                .select_related("class_level")
                .first()
            )
            if conflict_staff:
                raise ValidationError(
                    {
                        "teacher_staff": (
                            f"This teacher is already assigned as Class Teacher for "
                            f"{conflict_staff.class_level.name} - {conflict_staff.name} in this session."
                        )
                    }
                )

        if self.teacher_user_id and self.session_id:
            conflict = (
                Section.objects.filter(
                    session_id=self.session_id,
                    teacher_user_id=self.teacher_user_id,
                )
                .exclude(pk=self.pk)
                .select_related("class_level")
                .first()
            )
            if conflict:
                raise ValidationError(
                    {
                        "teacher_user": (
                            f"This teacher is already assigned as Class Teacher for "
                            f"{conflict.class_level.name} - {conflict.name} in this session."
                        )
                    }
                )

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

        self._sync_and_validate_teachers()


class Subject(TenantOwnedModel, SoftDeleteMixin):
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
                condition=models.Q(is_deleted=False),
                name="unique_subject_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en} ({self.name_bn})"


class ClassSubject(TenantOwnedModel, SoftDeleteMixin):
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
                condition=models.Q(is_deleted=False),
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


class Room(TenantOwnedModel, SoftDeleteMixin):
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
                condition=models.Q(is_deleted=False),
                name="unique_room_per_branch",
            ),
        ]

    def __str__(self) -> str:
        branch_name = f" ({self.branch.name})" if self.branch else ""
        return f"{self.name}{branch_name}"


class Period(TenantOwnedModel, SoftDeleteMixin):
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
                condition=models.Q(is_deleted=False),
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


class RoutineSlot(TenantOwnedModel, SoftDeleteMixin):
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
    teacher_staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routine_slots",
        help_text="Assigned teacher staff profile reference",
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
                condition=models.Q(is_deleted=False),
                name="unique_slot_per_section_weekday_period",
            ),
            models.UniqueConstraint(
                fields=["room", "weekday", "period"],
                condition=models.Q(room__isnull=False, is_deleted=False),
                name="unique_slot_per_room_weekday_period",
            ),
            models.UniqueConstraint(
                fields=["teacher_user", "weekday", "period"],
                condition=models.Q(teacher_user__isnull=False, is_deleted=False),
                name="unique_slot_per_teacher_weekday_period",
            ),
            models.UniqueConstraint(
                fields=["teacher_staff", "weekday", "period"],
                condition=models.Q(teacher_staff__isnull=False, is_deleted=False),
                name="unique_slot_per_teacher_staff_weekday_period",
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


class SubstituteAssignment(TenantOwnedModel, SoftDeleteMixin):
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
    original_staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="original_substitutions",
    )
    substitute_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitute_assignments",
    )
    substitute_staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
                condition=models.Q(is_deleted=False),
                name="unique_substitution_per_slot_date",
            ),
        ]

    def __str__(self) -> str:
        teacher_name = (
            (self.substitute_staff.full_name_en or self.substitute_staff.full_name_bn)
            if self.substitute_staff
            else (self.substitute_teacher.full_name if self.substitute_teacher else "Assigned")
        )
        return f"{self.slot_date} | Slot {self.routine_slot_id} -> {teacher_name}"

    def clean(self) -> None:
        super().clean()
        if (
            self.substitute_teacher_id
            and self.substitute_teacher.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"substitute_teacher": "Substitute teacher must belong to the same institution."}
            )
        if self.substitute_staff_id and self.substitute_staff.institution_id != self.institution_id:
            raise ValidationError(
                {"substitute_staff": "Substitute staff must belong to the same institution."}
            )
        if not self.substitute_teacher_id and not self.substitute_staff_id:
            raise ValidationError(
                {"substitute_teacher": "A substitute teacher or staff must be assigned."}
            )
        if (
            self.original_teacher_id
            and self.substitute_teacher_id
            and self.substitute_teacher_id == self.original_teacher_id
        ):
            raise ValidationError(
                {"substitute_teacher": "Substitute teacher cannot be the original teacher."}
            )
        if (
            self.original_staff_id
            and self.substitute_staff_id
            and self.substitute_staff_id == self.original_staff_id
        ):
            raise ValidationError(
                {"substitute_staff": "Substitute teacher cannot be the original teacher."}
            )
