"""Serializers for Library Management."""

import os
from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.library.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookIssue,
    EBook,
    LibraryFine,
    LibraryMember,
    LibraryPolicy,
    Reservation,
)

ALLOWED_EBOOK_EXTENSIONS = {".pdf", ".epub", ".doc", ".docx", ".txt"}
MAX_EBOOK_SIZE_BYTES = 50 * 1024 * 1024


class LibraryPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryPolicy
        fields = [
            "id",
            "institution",
            "branch",
            "member_type",
            "max_books",
            "loan_days",
            "max_renewals",
            "renewal_days",
            "fine_per_day",
            "grace_days",
            "block_issue_on_library_fines",
            "block_issue_on_fee_dues",
            "max_unpaid_fine_threshold",
            "reservation_hold_hours",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class BookSerializer(serializers.ModelSerializer):
    total_copies = serializers.IntegerField(read_only=True, default=0)
    available_copies = serializers.IntegerField(read_only=True, default=0)
    issue_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Book
        fields = [
            "id",
            "institution",
            "isbn",
            "title",
            "title_bn",
            "authors",
            "category",
            "publisher",
            "edition",
            "publication_year",
            "language",
            "subject",
            "description",
            "cover_image_url",
            "is_reference_only",
            "total_copies",
            "available_copies",
            "issue_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class BookCopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_isbn = serializers.CharField(source="book.isbn", read_only=True)

    class Meta:
        model = BookCopy
        fields = [
            "id",
            "institution",
            "book",
            "book_title",
            "book_isbn",
            "branch",
            "accession_no",
            "barcode",
            "rfid_tag",
            "shelf_location",
            "status",
            "condition_notes",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class LibraryMemberSerializer(serializers.ModelSerializer):
    holder_name = serializers.SerializerMethodField()

    class Meta:
        model = LibraryMember
        fields = [
            "id",
            "institution",
            "member_type",
            "student",
            "staff",
            "holder_name",
            "branch",
            "card_number",
            "rfid_card_uid",
            "status",
            "joined_date",
            "expiry_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def get_holder_name(self, obj: LibraryMember) -> str:
        if obj.student_id and obj.student:
            return obj.student.name_en
        if obj.staff_id and obj.staff:
            return obj.staff.full_name_en
        return ""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        student = attrs.get("student", getattr(self.instance, "student", None))
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        if bool(student) == bool(staff):
            raise serializers.ValidationError("Provide exactly one of 'student' or 'staff'.")
        return attrs


class BookIssueSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    accession_no = serializers.CharField(source="copy.accession_no", read_only=True)
    barcode = serializers.CharField(source="copy.barcode", read_only=True)
    card_number = serializers.CharField(source="member.card_number", read_only=True)

    class Meta:
        model = BookIssue
        fields = [
            "id",
            "institution",
            "copy",
            "book_title",
            "accession_no",
            "barcode",
            "member",
            "card_number",
            "issued_by",
            "returned_to",
            "issue_date",
            "due_date",
            "return_date",
            "renewal_count",
            "status",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BookIssueCreateSerializer(serializers.Serializer):
    member_id = serializers.UUIDField(required=False, allow_null=True)
    card_number = serializers.CharField(required=False, allow_blank=True, default="")
    rfid_card_uid = serializers.CharField(required=False, allow_blank=True, default="")
    copy_id = serializers.UUIDField(required=False, allow_null=True)
    accession_no = serializers.CharField(required=False, allow_blank=True, default="")
    barcode = serializers.CharField(required=False, allow_blank=True, default="")
    rfid_tag = serializers.CharField(required=False, allow_blank=True, default="")
    due_date = serializers.DateField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class BookReturnSerializer(serializers.Serializer):
    issue_id = serializers.UUIDField(required=False, allow_null=True)
    accession_no = serializers.CharField(required=False, allow_blank=True, default="")
    barcode = serializers.CharField(required=False, allow_blank=True, default="")
    rfid_tag = serializers.CharField(required=False, allow_blank=True, default="")
    return_date = serializers.DateField(required=False, allow_null=True)
    mark_damaged = serializers.BooleanField(required=False, default=False)
    mark_lost = serializers.BooleanField(required=False, default=False)
    damage_fine_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class BookRenewSerializer(serializers.Serializer):
    issue_id = serializers.UUIDField()
    extra_days = serializers.IntegerField(required=False, min_value=1, max_value=90)


class ReservationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    card_number = serializers.CharField(source="member.card_number", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "institution",
            "book",
            "book_title",
            "member",
            "card_number",
            "queue_position",
            "status",
            "reserved_at",
            "notified_at",
            "expires_at",
            "fulfilled_copy",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "queue_position",
            "status",
            "reserved_at",
            "notified_at",
            "expires_at",
            "fulfilled_copy",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "member": {"required": False},
        }


class LibraryFineSerializer(serializers.ModelSerializer):
    card_number = serializers.CharField(source="member.card_number", read_only=True)
    book_title = serializers.CharField(source="issue.copy.book.title", read_only=True)

    class Meta:
        model = LibraryFine
        fields = [
            "id",
            "institution",
            "issue",
            "book_title",
            "member",
            "card_number",
            "reason",
            "overdue_days",
            "amount",
            "paid_amount",
            "status",
            "paid_at",
            "payment_reference",
            "waived_by",
            "waive_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FinePaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_reference = serializers.CharField(required=False, allow_blank=True, default="")


class FineWaiveSerializer(serializers.Serializer):
    waive_reason = serializers.CharField(required=False, allow_blank=True, default="")


class EBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = EBook
        fields = [
            "id",
            "institution",
            "title",
            "title_bn",
            "authors",
            "category",
            "language",
            "book",
            "subject",
            "file",
            "external_url",
            "is_public_to_members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def validate_file(self, value: Any) -> Any:
        if value is None:
            return value
        ext = os.path.splitext(getattr(value, "name", ""))[1].lower()
        if ext not in ALLOWED_EBOOK_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported e-book format '{ext}'. Allowed: {sorted(ALLOWED_EBOOK_EXTENSIONS)}."
            )
        if getattr(value, "size", 0) > MAX_EBOOK_SIZE_BYTES:
            raise serializers.ValidationError("E-book file size exceeds 50 MB limit.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        file_obj = attrs.get("file", getattr(self.instance, "file", None))
        external_url = attrs.get("external_url", getattr(self.instance, "external_url", ""))
        if not file_obj and not external_url:
            raise serializers.ValidationError("Provide either an uploaded file or an external_url.")
        return attrs


class CatalogImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    branch = serializers.UUIDField(required=False, allow_null=True)


class CatalogImportResponseSerializer(serializers.Serializer):
    created_books = serializers.IntegerField()
    created_copies = serializers.IntegerField()
    skipped = serializers.IntegerField()
    row_errors = serializers.ListField(child=serializers.DictField())


class MemberHistoryResponseSerializer(serializers.Serializer):
    member = LibraryMemberSerializer()
    active_issues = BookIssueSerializer(many=True)
    past_issues = BookIssueSerializer(many=True)
    reservations = ReservationSerializer(many=True)
    fines = LibraryFineSerializer(many=True)
    unpaid_fine_total = serializers.DecimalField(max_digits=12, decimal_places=2)


__all__ = [
    "BookCopySerializer",
    "BookCopyStatus",
    "BookIssueCreateSerializer",
    "BookIssueSerializer",
    "BookRenewSerializer",
    "BookReturnSerializer",
    "BookSerializer",
    "CatalogImportResponseSerializer",
    "CatalogImportSerializer",
    "EBookSerializer",
    "FinePaymentSerializer",
    "FineWaiveSerializer",
    "LibraryFineSerializer",
    "LibraryMemberSerializer",
    "LibraryPolicySerializer",
    "MemberHistoryResponseSerializer",
    "ReservationSerializer",
]
