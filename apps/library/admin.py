"""Django Admin registrations for Library Management."""

from django.contrib import admin

from apps.library.models import (
    Book,
    BookCopy,
    BookIssue,
    EBook,
    LibraryFine,
    LibraryMember,
    LibraryPolicy,
    Reservation,
)


@admin.register(LibraryPolicy)
class LibraryPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "institution",
        "branch",
        "member_type",
        "max_books",
        "loan_days",
        "fine_per_day",
    )
    list_filter = ("member_type", "block_issue_on_library_fines", "block_issue_on_fee_dues")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn", "authors", "category", "language", "is_reference_only")
    search_fields = ("title", "isbn", "authors", "category")
    list_filter = ("language", "is_reference_only")


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("accession_no", "book", "barcode", "rfid_tag", "shelf_location", "status")
    search_fields = ("accession_no", "barcode", "rfid_tag", "book__title")
    list_filter = ("status",)


@admin.register(LibraryMember)
class LibraryMemberAdmin(admin.ModelAdmin):
    list_display = ("card_number", "member_type", "student", "staff", "status", "joined_date")
    search_fields = ("card_number", "rfid_card_uid")
    list_filter = ("member_type", "status")


@admin.register(BookIssue)
class BookIssueAdmin(admin.ModelAdmin):
    list_display = (
        "copy",
        "member",
        "issue_date",
        "due_date",
        "return_date",
        "renewal_count",
        "status",
    )
    search_fields = ("copy__accession_no", "member__card_number")
    list_filter = ("status",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("book", "member", "queue_position", "status", "reserved_at", "expires_at")
    list_filter = ("status",)


@admin.register(LibraryFine)
class LibraryFineAdmin(admin.ModelAdmin):
    list_display = ("member", "reason", "overdue_days", "amount", "paid_amount", "status")
    list_filter = ("status", "reason")


@admin.register(EBook)
class EBookAdmin(admin.ModelAdmin):
    list_display = ("title", "authors", "category", "language", "is_public_to_members")
    search_fields = ("title", "authors", "category")
    list_filter = ("language", "is_public_to_members")
