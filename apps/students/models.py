"""Data models for Student Management lifecycle."""

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    TRANSFERRED = "transferred", "Transferred"
    DROPPED = "dropped", "Dropped Out"
    GRADUATED = "graduated", "Graduated"
    ALUMNI = "alumni", "Alumni"
    SUSPENDED = "suspended", "Suspended"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class BloodGroup(models.TextChoices):
    A_POSITIVE = "A+", "A+"
    A_NEGATIVE = "A-", "A-"
    B_POSITIVE = "B+", "B+"
    B_NEGATIVE = "B-", "B-"
    AB_POSITIVE = "AB+", "AB+"
    AB_NEGATIVE = "AB-", "AB-"
    O_POSITIVE = "O+", "O+"
    O_NEGATIVE = "O-", "O-"
    UNKNOWN = "unknown", "Unknown"


class Religion(models.TextChoices):
    ISLAM = "islam", "Islam"
    HINDUISM = "hinduism", "Hinduism"
    BUDDHISM = "buddhism", "Buddhism"
    CHRISTIANITY = "christianity", "Christianity"
    OTHER = "other", "Other"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PROMOTED = "promoted", "Promoted"
    DEMOTED = "demoted", "Demoted"
    REPEATED = "repeated", "Repeated"
    TRANSFERRED = "transferred", "Transferred"
    DROPPED = "dropped", "Dropped Out"
    GRADUATED = "graduated", "Graduated"


class DocumentType(models.TextChoices):
    BIRTH_CERTIFICATE = "birth_certificate", "Birth Registration Certificate"
    NATIONAL_ID = "national_id", "National ID (NID)"
    PREVIOUS_MARKSHEET = "previous_marksheet", "Previous Marksheet"
    TRANSFER_CERTIFICATE = "transfer_certificate", "Transfer Certificate (TC)"
    MEDICAL_CERTIFICATE = "medical_certificate", "Medical Certificate"
    OTHER = "other", "Other"


class PromotionBatchStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PREVIEWED = "previewed", "Previewed"
    APPLIED = "applied", "Applied"
    ROLLED_BACK = "rolled_back", "Rolled Back"


class PromotionAction(models.TextChoices):
    PROMOTE = "promote", "Promote to Next Class"
    REPEAT = "repeat", "Repeat Current Class"
    DEMOTE = "demote", "Demote"
    WITHDRAW = "withdraw", "Withdraw"


class DropoutReason(models.TextChoices):
    FINANCIAL = "financial", "Financial Constraint"
    CHILD_MARRIAGE = "child_marriage", "Child Marriage"
    MIGRATION = "migration", "Family Migration"
    EMPLOYMENT = "employment", "Child Labor / Employment"
    ACADEMIC_FAILURE = "academic_failure", "Academic Failure"
    HEALTH = "health", "Health / Medical"
    OTHER = "other", "Other"


class Student(TenantOwnedModel, SoftDeleteMixin):
    """Core student master profile in an institution."""

    student_id = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Institution-configurable unique student roll/identifier (e.g. 2026100001).",
    )
    name_bn = models.CharField(max_length=255, help_text="Full name in Bangla script.")
    name_en = models.CharField(max_length=255, help_text="Full name in English.")
    dob = models.DateField(help_text="Date of birth.")
    gender = models.CharField(max_length=10, choices=Gender.choices)
    blood_group = models.CharField(
        max_length=10, choices=BloodGroup.choices, default=BloodGroup.UNKNOWN
    )
    religion = models.CharField(max_length=20, choices=Religion.choices, default=Religion.ISLAM)
    birth_reg_no = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        db_index=True,
        help_text="17-digit Bangladeshi Birth Registration Number.",
    )
    photo = models.ImageField(upload_to="students/photos/", blank=True, null=True)
    present_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=StudentStatus.choices, default=StudentStatus.ACTIVE, db_index=True
    )
    admission_date = models.DateField()

    # Special categories & stipends
    is_orphan = models.BooleanField(default=False)
    has_disability = models.BooleanField(default=False)
    disability_details = models.CharField(max_length=255, blank=True)
    quota_category = models.CharField(
        max_length=50, default="none", help_text="Quota category (e.g. freedom_fighter, sibling)"
    )
    has_stipend = models.BooleanField(default=False)

    # Contact & Guardianship placeholder (Task 07 will wire full Guardian models)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Student's mobile number for app login (+8801XXXXXXXXX).",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
        help_text="Login user account for mobile app / portal",
    )
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    application = models.OneToOneField(
        "admissions.Application",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
        help_text="Originating admission application if admitted via portal.",
    )

    class Meta:
        ordering = ["student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student_id"],
                condition=models.Q(is_deleted=False),
                name="unique_student_id_per_institution",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "student_id"]),
            models.Index(fields=["institution", "status"]),
            models.Index(fields=["institution", "birth_reg_no"]),
            models.Index(fields=["name_en"]),
            models.Index(fields=["name_bn"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_id} - {self.name_en} ({self.name_bn})"


class StudentEnrollment(TenantOwnedModel, SoftDeleteMixin):
    """Academic session enrollment linking student to class, section, shift, and roll number."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="student_enrollments",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    group = models.ForeignKey(
        "academics.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrollments",
    )
    shift = models.ForeignKey(
        "institutions.Shift",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrollments",
    )
    roll_no = models.PositiveIntegerField(help_text="Class section roll number.")
    enrollment_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["session", "class_level", "section", "roll_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "session", "section", "roll_no"],
                condition=models.Q(is_deleted=False),
                name="unique_roll_per_section_session",
            ),
            models.UniqueConstraint(
                fields=["institution", "student", "session"],
                condition=models.Q(status=EnrollmentStatus.ACTIVE, is_deleted=False),
                name="unique_active_enrollment_per_session",
            ),
        ]
        indexes = [
            models.Index(fields=["institution", "session", "section", "roll_no"]),
            models.Index(fields=["institution", "student", "session"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.section.name} (Roll: {self.roll_no})"


class StudentDocument(TenantOwnedModel, SoftDeleteMixin):
    """Archival documents submitted for a student."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="students/documents/")
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.title}"


class PreviousSchool(TenantOwnedModel, SoftDeleteMixin):
    """Previous academic and school history."""

    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="previous_school"
    )
    school_name = models.CharField(max_length=255)
    board = models.CharField(max_length=100, blank=True)
    last_class_passed = models.CharField(max_length=100, blank=True)
    tc_number = models.CharField(max_length=100, blank=True)
    tc_date = models.DateField(null=True, blank=True)
    gpa_obtained = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.school_name}"


class StudentIDCard(TenantOwnedModel, SoftDeleteMixin):
    """Student digital/physical identification card."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="id_cards")
    enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.CASCADE, related_name="id_cards"
    )
    card_no = models.CharField(max_length=64, db_index=True)
    qr_payload = models.TextField(blank=True)
    rfid_uid = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "card_no"],
                condition=models.Q(is_deleted=False),
                name="unique_card_no_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"ID Card: {self.card_no} ({self.student.student_id})"


class PromotionBatch(TenantOwnedModel, SoftDeleteMixin):
    """Batch record for academic session progression."""

    from_session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="promotions_out",
    )
    to_session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="promotions_in",
    )
    from_class = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="promotions_out",
    )
    to_class = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="promotions_in",
    )
    status = models.CharField(
        max_length=20,
        choices=PromotionBatchStatus.choices,
        default=PromotionBatchStatus.DRAFT,
    )
    total_students = models.PositiveIntegerField(default=0)
    promoted_count = models.PositiveIntegerField(default=0)
    retained_count = models.PositiveIntegerField(default=0)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def __str__(self) -> str:
        return f"Promotion {self.from_class.name} -> {self.to_class.name} ({self.from_session.name} to {self.to_session.name})"


class PromotionItem(TenantOwnedModel, SoftDeleteMixin):
    """Individual student promotion row inside a batch."""

    batch = models.ForeignKey(PromotionBatch, on_delete=models.CASCADE, related_name="items")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="promotion_items")
    from_enrollment = models.ForeignKey(
        StudentEnrollment,
        on_delete=models.CASCADE,
        related_name="promotion_out_records",
    )
    to_enrollment = models.ForeignKey(
        StudentEnrollment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="promotion_in_records",
    )
    target_class = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="+",
    )
    target_section = models.ForeignKey(
        "academics.Section",
        on_delete=models.CASCADE,
        related_name="+",
    )
    target_roll_no = models.PositiveIntegerField()
    action = models.CharField(
        max_length=20, choices=PromotionAction.choices, default=PromotionAction.PROMOTE
    )
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.student.student_id} -> Roll {self.target_roll_no} ({self.action})"


class TransferCertificate(TenantOwnedModel, SoftDeleteMixin):
    """Official School Leaving / Transfer Certificate (ছাড়পত্র)."""

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="transfer_certificates"
    )
    enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.CASCADE, related_name="transfer_certificates"
    )
    tc_number = models.CharField(max_length=64, db_index=True)
    issue_date = models.DateField()
    reason = models.TextField()
    conduct_remarks = models.CharField(max_length=255, default="Satisfactory")
    dues_cleared = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    pdf_file = models.FileField(upload_to="students/certificates/tc/", blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "tc_number"],
                condition=models.Q(is_deleted=False),
                name="unique_tc_number_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tc_number} - {self.student.student_id}"


class Testimonial(TenantOwnedModel, SoftDeleteMixin):
    """Academic Character Certificate / Testimonial (প্রশংসাপত্র)."""

    __test__ = False

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="testimonials")
    enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.CASCADE, related_name="testimonials"
    )
    certificate_no = models.CharField(max_length=64, db_index=True)
    issue_date = models.DateField()
    exam_name = models.CharField(max_length=100)
    passing_year = models.PositiveIntegerField()
    gpa = models.DecimalField(max_digits=4, decimal_places=2)
    character = models.CharField(max_length=100, default="Good")
    pdf_file = models.FileField(
        upload_to="students/certificates/testimonials/", blank=True, null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "certificate_no"],
                condition=models.Q(is_deleted=False),
                name="unique_testimonial_no_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.certificate_no} - {self.student.student_id}"


class DropoutRecord(TenantOwnedModel, SoftDeleteMixin):
    """Formal record of student dropout/attrition."""

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="dropout_record")
    dropout_date = models.DateField()
    reason = models.CharField(max_length=30, choices=DropoutReason.choices)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Dropout: {self.student.student_id} ({self.get_reason_display()})"


class AlumniProfile(TenantOwnedModel, SoftDeleteMixin):
    """Profile for graduated student network."""

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="alumni_profile")
    graduation_year = models.PositiveIntegerField()
    higher_study_institute = models.CharField(max_length=255, blank=True)
    current_profession = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return f"Alumni: {self.student.student_id} ({self.graduation_year})"
