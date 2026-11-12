"""Models for Notice Board receipts, Events, Clubs, Competitions, Achievements, Certificates & Gallery."""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.communications.models import NoticeAudience
from apps.core.models import SoftDeleteMixin, TenantOwnedModel

ALLOWED_GALLERY_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm"}
MAX_GALLERY_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def validate_gallery_media_file(file_obj: models.fields.files.FieldFile) -> None:
    """Validate gallery media file extension and size."""
    if not file_obj or not file_obj.name:
        return
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_GALLERY_EXTENSIONS:
        raise ValidationError(
            f"Unsupported media file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_GALLERY_EXTENSIONS))}."
        )
    size = getattr(file_obj, "size", None)
    if size is not None and size > MAX_GALLERY_FILE_SIZE_BYTES:
        raise ValidationError("Gallery media file size cannot exceed 20 MB.")


class NoticeReadReceipt(TenantOwnedModel):
    """Tracks when a user reads a communications.Notice."""

    notice = models.ForeignKey(
        "communications.Notice",
        on_delete=models.CASCADE,
        related_name="read_receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notice_read_receipts",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notice Read Receipt"
        verbose_name_plural = "Notice Read Receipts"
        unique_together = ("institution", "notice", "user")
        indexes = [
            models.Index(fields=["institution", "notice"]),
            models.Index(fields=["institution", "user"]),
        ]

    def __str__(self) -> str:
        return f"Receipt({self.notice_id}, {self.user_id})"


class EventCategory(models.TextChoices):
    ACADEMIC = "academic", "Academic"
    SPORTS = "sports", "Sports Day"
    ANNUAL_FUNCTION = "annual_function", "Annual Function"
    NATIONAL_DAY = "national_day", "National Day"
    CULTURAL = "cultural", "Cultural"
    CLUB = "club", "Club Activity"
    EXAM = "exam", "Exam"
    MEETING = "meeting", "Parent/Staff Meeting"
    OTHER = "other", "Other"


class ClubCategory(models.TextChoices):
    SCOUTS = "scouts", "Scouts"
    ROVER = "rover", "Rover Scouts"
    BNCC = "bncc", "BNCC"
    DEBATE = "debate", "Debate"
    CULTURAL = "cultural", "Cultural"
    SCIENCE = "science", "Science"
    SPORTS = "sports", "Sports"
    OTHER = "other", "Other"


class Club(TenantOwnedModel, SoftDeleteMixin):
    """Co-curricular club (Scouts, Rover, BNCC, Debate, Cultural, etc.)."""

    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True)
    category = models.CharField(
        max_length=30,
        choices=ClubCategory.choices,
        default=ClubCategory.OTHER,
    )
    description = models.TextField(blank=True)
    advisor = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="advised_clubs",
    )
    meeting_schedule = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        unique_together = ("institution", "name_en")
        ordering = ["name_en"]

    def __str__(self) -> str:
        return self.name_en


class ClubMembershipRole(models.TextChoices):
    MEMBER = "member", "Member"
    PRESIDENT = "president", "President"
    SECRETARY = "secretary", "Secretary"
    TREASURER = "treasurer", "Treasurer"
    CAPTAIN = "captain", "Captain"


class ClubMembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class ClubMembership(TenantOwnedModel, SoftDeleteMixin):
    """Student membership in a co-curricular club."""

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="club_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=ClubMembershipRole.choices,
        default=ClubMembershipRole.MEMBER,
    )
    joined_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ClubMembershipStatus.choices,
        default=ClubMembershipStatus.ACTIVE,
        db_index=True,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Club Membership"
        verbose_name_plural = "Club Memberships"
        unique_together = ("institution", "club", "student")

    def __str__(self) -> str:
        return f"{self.student_id} - {self.club_id} ({self.role})"


class Event(TenantOwnedModel, SoftDeleteMixin):
    """School, club, or national day event on the unified calendar."""

    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    description_en = models.TextField(blank=True)
    description_bn = models.TextField(blank=True)
    category = models.CharField(
        max_length=30,
        choices=EventCategory.choices,
        default=EventCategory.ACADEMIC,
        db_index=True,
    )
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    is_all_day = models.BooleanField(default=False)
    venue = models.CharField(max_length=255, blank=True)
    target_audience = models.CharField(
        max_length=20,
        choices=NoticeAudience.choices,
        default=NoticeAudience.ALL,
        db_index=True,
    )
    target_class_level = models.ForeignKey(
        "academics.ClassLevel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    target_section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    organizer = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="organized_events",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    requires_rsvp = models.BooleanField(default=False)
    max_participants = models.PositiveIntegerField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["institution", "start_datetime", "end_datetime"]),
            models.Index(fields=["institution", "is_published"]),
        ]

    def clean(self) -> None:
        super().clean()
        if self.end_datetime and self.start_datetime and self.end_datetime < self.start_datetime:
            raise ValidationError("end_datetime cannot be earlier than start_datetime.")

    def __str__(self) -> str:
        return self.title_en


class RSVPStatus(models.TextChoices):
    GOING = "going", "Going"
    INTERESTED = "interested", "Interested"
    DECLINED = "declined", "Declined"


class EventRSVP(TenantOwnedModel):
    """User/student RSVP for an Event."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="rsvps",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_rsvps",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="event_rsvps",
    )
    status = models.CharField(
        max_length=20,
        choices=RSVPStatus.choices,
        default=RSVPStatus.GOING,
    )
    note = models.CharField(max_length=255, blank=True)
    responded_at = models.DateTimeField(auto_now=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Event RSVP"
        verbose_name_plural = "Event RSVPs"
        unique_together = ("institution", "event", "user")

    def __str__(self) -> str:
        return f"RSVP({self.event_id}, {self.user_id}, {self.status})"


class CompetitionLevel(models.TextChoices):
    SCHOOL = "school", "School"
    UPAZILA = "upazila", "Upazila"
    DISTRICT = "district", "District"
    DIVISION = "division", "Division"
    NATIONAL = "national", "National"


class Competition(TenantOwnedModel, SoftDeleteMixin):
    """Co-curricular or academic competition."""

    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competitions",
    )
    club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competitions",
    )
    competition_date = models.DateField(db_index=True)
    level = models.CharField(
        max_length=20,
        choices=CompetitionLevel.choices,
        default=CompetitionLevel.SCHOOL,
    )
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Competition"
        verbose_name_plural = "Competitions"
        ordering = ["-competition_date"]

    def __str__(self) -> str:
        return self.title_en


class CompetitionPosition(models.TextChoices):
    FIRST = "1st", "1st Place"
    SECOND = "2nd", "2nd Place"
    THIRD = "3rd", "3rd Place"
    HONORABLE_MENTION = "honorable_mention", "Honorable Mention"
    PARTICIPANT = "participant", "Participant"


class CompetitionResult(TenantOwnedModel, SoftDeleteMixin):
    """Student placement/award in a Competition."""

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="results",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="competition_results",
    )
    position = models.CharField(
        max_length=30,
        choices=CompetitionPosition.choices,
        default=CompetitionPosition.PARTICIPANT,
    )
    score_or_remark = models.CharField(max_length=200, blank=True)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Competition Result"
        verbose_name_plural = "Competition Results"
        unique_together = ("institution", "competition", "student")

    def __str__(self) -> str:
        return f"{self.student_id} - {self.competition_id} ({self.position})"


class Achievement(TenantOwnedModel, SoftDeleteMixin):
    """Recorded student achievement (from competition or general merit)."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)
    achieved_date = models.DateField(db_index=True)
    competition_result = models.ForeignKey(
        CompetitionResult,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="achievements",
    )
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"
        ordering = ["-achieved_date"]

    def __str__(self) -> str:
        return f"{self.title_en} ({self.student_id})"


class Certificate(TenantOwnedModel, SoftDeleteMixin):
    """Issued certificate record with PDF generation support."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    achievement = models.ForeignKey(
        Achievement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
    )
    competition_result = models.ForeignKey(
        CompetitionResult,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
    )
    certificate_number = models.CharField(max_length=100)
    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    issued_date = models.DateField(db_index=True)
    template_code = models.CharField(max_length=60, default="standard")
    signatory_name = models.CharField(max_length=150, blank=True)
    signatory_title = models.CharField(max_length=150, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        unique_together = ("institution", "certificate_number")
        ordering = ["-issued_date"]

    def __str__(self) -> str:
        return f"{self.certificate_number} - {self.title_en}"


class Album(TenantOwnedModel, SoftDeleteMixin):
    """Photo/Video gallery album, optionally linked to an Event."""

    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="albums",
    )
    album_date = models.DateField(db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    is_public_to_guardians = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Album"
        verbose_name_plural = "Albums"
        ordering = ["-album_date"]

    def __str__(self) -> str:
        return self.title_en


class GalleryMediaType(models.TextChoices):
    PHOTO = "photo", "Photo"
    VIDEO = "video", "Video"


class GalleryMedia(TenantOwnedModel, SoftDeleteMixin):
    """Individual photo/video inside an Album with student consent gating."""

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="media_items",
    )
    media_type = models.CharField(
        max_length=10,
        choices=GalleryMediaType.choices,
        default=GalleryMediaType.PHOTO,
    )
    file = models.FileField(
        upload_to="events/gallery/",
        validators=[validate_gallery_media_file],
    )
    caption_en = models.CharField(max_length=255, blank=True)
    caption_bn = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    contains_students = models.BooleanField(
        default=True,
        help_text="True if media depicts identifiable students.",
    )
    guardian_consent_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Must be True before student-depicting media is visible to guardians/students.",
    )
    is_approved = models.BooleanField(default=False, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Gallery Media"
        verbose_name_plural = "Gallery Media"
        ordering = ["display_order", "-created_at"]

    def __str__(self) -> str:
        return f"{self.album_id} - {self.media_type} ({self.id})"
