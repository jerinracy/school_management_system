"""Models for Library Management (Catalog, Copies, Members, Circulation, Reservations, Fines, E-Books)."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class LibraryMemberType(models.TextChoices):
    STUDENT = "student", "Student"
    TEACHER = "teacher", "Teacher"
    STAFF = "staff", "Staff"


class LibraryMemberStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    EXPIRED = "expired", "Expired"


class BookCopyStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ISSUED = "issued", "Issued"
    RESERVED = "reserved", "Reserved"
    MAINTENANCE = "maintenance", "Maintenance"
    LOST = "lost", "Lost"
    DAMAGED = "damaged", "Damaged"


class BookIssueStatus(models.TextChoices):
    ISSUED = "issued", "Issued"
    RETURNED = "returned", "Returned"
    OVERDUE = "overdue", "Overdue"
    LOST = "lost", "Lost"


class ReservationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    READY_FOR_PICKUP = "ready_for_pickup", "Ready for Pickup"
    FULFILLED = "fulfilled", "Fulfilled"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class LibraryFineReason(models.TextChoices):
    OVERDUE = "overdue", "Overdue Return"
    LOST = "lost", "Lost Book"
    DAMAGED = "damaged", "Damaged Book"


class LibraryFineStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID = "paid", "Paid"
    WAIVED = "waived", "Waived"


class LibraryPolicy(TenantOwnedModel):
    """Configurable borrowing, renewal, and fine policy per member type."""

    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="library_policies",
    )
    member_type = models.CharField(
        max_length=20,
        choices=LibraryMemberType.choices,
        default=LibraryMemberType.STUDENT,
        db_index=True,
    )
    max_books = models.PositiveSmallIntegerField(default=3)
    loan_days = models.PositiveSmallIntegerField(default=14)
    max_renewals = models.PositiveSmallIntegerField(default=1)
    renewal_days = models.PositiveSmallIntegerField(default=7)
    fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("5.00"))
    grace_days = models.PositiveSmallIntegerField(default=0)
    block_issue_on_library_fines = models.BooleanField(default=True)
    block_issue_on_fee_dues = models.BooleanField(default=False)
    max_unpaid_fine_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    reservation_hold_hours = models.PositiveSmallIntegerField(default=48)

    class Meta:
        ordering = ["member_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "branch", "member_type"],
                name="unique_library_policy_per_branch_member_type",
            ),
            models.UniqueConstraint(
                fields=["institution", "member_type"],
                condition=Q(branch__isnull=True),
                name="unique_default_library_policy_per_member_type",
            ),
            models.CheckConstraint(
                condition=Q(fine_per_day__gte=0) & Q(max_unpaid_fine_threshold__gte=0),
                name="library_policy_non_negative_amounts",
            ),
        ]

    def __str__(self) -> str:
        branch_label = self.branch.name if self.branch else "Default"
        return f"{self.member_type} ({branch_label})"


class Book(TenantOwnedModel, SoftDeleteMixin):
    """Bibliographic record in the institution library catalog."""

    isbn = models.CharField(max_length=32, blank=True, default="", db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    title_bn = models.CharField(max_length=255, blank=True, default="")
    authors = models.CharField(max_length=500, db_index=True)
    category = models.CharField(max_length=100, blank=True, default="", db_index=True)
    publisher = models.CharField(max_length=200, blank=True, default="")
    edition = models.CharField(max_length=64, blank=True, default="")
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    language = models.CharField(max_length=32, default="en", db_index=True)
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_books",
    )
    description = models.TextField(blank=True, default="")
    cover_image_url = models.URLField(max_length=500, blank=True, default="")
    is_reference_only = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["institution", "title"]),
            models.Index(fields=["institution", "isbn"]),
            models.Index(fields=["institution", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.isbn})" if self.isbn else self.title


class BookCopy(TenantOwnedModel, SoftDeleteMixin):
    """Physical copy of a Book tracked by accession number, barcode, and RFID."""

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="copies")
    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="library_copies",
    )
    accession_no = models.CharField(max_length=64, db_index=True)
    barcode = models.CharField(max_length=64, blank=True, default="", db_index=True)
    rfid_tag = models.CharField(max_length=64, blank=True, default="", db_index=True)
    shelf_location = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=BookCopyStatus.choices,
        default=BookCopyStatus.AVAILABLE,
        db_index=True,
    )
    condition_notes = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["accession_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "accession_no"],
                condition=Q(is_deleted=False),
                name="unique_active_accession_no_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "barcode"],
                condition=Q(is_deleted=False) & ~Q(barcode=""),
                name="unique_active_barcode_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "rfid_tag"],
                condition=Q(is_deleted=False) & ~Q(rfid_tag=""),
                name="unique_active_rfid_per_institution",
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="book_copy_non_negative_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.accession_no} - {self.book.title}"


class LibraryMember(TenantOwnedModel, SoftDeleteMixin):
    """Library membership card linked to either a Student or a Staff member."""

    member_type = models.CharField(
        max_length=20,
        choices=LibraryMemberType.choices,
        db_index=True,
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="library_memberships",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="library_memberships",
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="library_members",
    )
    card_number = models.CharField(max_length=64, db_index=True)
    rfid_card_uid = models.CharField(max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(
        max_length=20,
        choices=LibraryMemberStatus.choices,
        default=LibraryMemberStatus.ACTIVE,
        db_index=True,
    )
    joined_date = models.DateField(default=timezone.localdate)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["card_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "card_number"],
                condition=Q(is_deleted=False),
                name="unique_active_library_card_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "rfid_card_uid"],
                condition=Q(is_deleted=False) & ~Q(rfid_card_uid=""),
                name="unique_active_member_rfid_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "student"],
                condition=Q(is_deleted=False, student__isnull=False),
                name="unique_active_library_member_student",
            ),
            models.UniqueConstraint(
                fields=["institution", "staff"],
                condition=Q(is_deleted=False, staff__isnull=False),
                name="unique_active_library_member_staff",
            ),
            models.CheckConstraint(
                condition=(
                    Q(student__isnull=False, staff__isnull=True)
                    | Q(student__isnull=True, staff__isnull=False)
                ),
                name="library_member_exactly_one_holder",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.card_number} ({self.member_type})"


class BookIssue(TenantOwnedModel):
    """Circulation record tracking an issued BookCopy."""

    copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name="issues")
    member = models.ForeignKey(LibraryMember, on_delete=models.PROTECT, related_name="issues")
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_issues_created",
    )
    returned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_returns_processed",
    )
    issue_date = models.DateField(default=timezone.localdate, db_index=True)
    due_date = models.DateField(db_index=True)
    return_date = models.DateField(null=True, blank=True, db_index=True)
    renewal_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=BookIssueStatus.choices,
        default=BookIssueStatus.ISSUED,
        db_index=True,
    )
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["institution", "status", "due_date"]),
            models.Index(fields=["institution", "member", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["copy"],
                condition=Q(status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE]),
                name="unique_active_issue_per_copy",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.copy.accession_no} -> {self.member.card_number} ({self.status})"


class Reservation(TenantOwnedModel):
    """FIFO reservation queue for a Book title."""

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="reservations")
    member = models.ForeignKey(LibraryMember, on_delete=models.PROTECT, related_name="reservations")
    queue_position = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.QUEUED,
        db_index=True,
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    fulfilled_copy = models.ForeignKey(
        BookCopy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfilled_reservations",
    )

    class Meta:
        ordering = ["queue_position", "reserved_at"]
        indexes = [
            models.Index(fields=["institution", "book", "status", "queue_position"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "member"],
                condition=Q(
                    status__in=[ReservationStatus.QUEUED, ReservationStatus.READY_FOR_PICKUP]
                ),
                name="unique_active_reservation_per_book_member",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book.title} - {self.member.card_number} (#{self.queue_position})"


class LibraryFine(TenantOwnedModel):
    """Fine assessed on overdue, lost, or damaged books."""

    issue = models.ForeignKey(BookIssue, on_delete=models.PROTECT, related_name="fines")
    member = models.ForeignKey(LibraryMember, on_delete=models.PROTECT, related_name="fines")
    reason = models.CharField(
        max_length=32,
        choices=LibraryFineReason.choices,
        default=LibraryFineReason.OVERDUE,
    )
    overdue_days = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=20,
        choices=LibraryFineStatus.choices,
        default=LibraryFineStatus.UNPAID,
        db_index=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, default="")
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waived_library_fines",
    )
    waive_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "member", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0)
                & Q(paid_amount__gte=0)
                & Q(paid_amount__lte=models.F("amount")),
                name="library_fine_valid_amounts",
            ),
        ]

    def __str__(self) -> str:
        return f"Fine {self.amount} BDT ({self.status}) - {self.member.card_number}"


class EBook(TenantOwnedModel, SoftDeleteMixin):
    """Digital resource / E-book in the institutional library."""

    title = models.CharField(max_length=255, db_index=True)
    title_bn = models.CharField(max_length=255, blank=True, default="")
    authors = models.CharField(max_length=500, blank=True, default="")
    category = models.CharField(max_length=100, blank=True, default="", db_index=True)
    language = models.CharField(max_length=32, default="en")
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebooks",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_ebooks",
    )
    file = models.FileField(upload_to="library/ebooks/", null=True, blank=True)
    external_url = models.URLField(max_length=500, blank=True, default="")
    is_public_to_members = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["institution", "category"]),
        ]

    def __str__(self) -> str:
        return self.title
