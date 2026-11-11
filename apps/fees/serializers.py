"""DRF Serializers for fee management, invoicing, waivers, and fines."""

from rest_framework import serializers

from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FineRule,
    Invoice,
    InvoiceLine,
    InvoiceType,
    StudentFeeAssignment,
    StudentWaiver,
    WaiverRule,
)


class FeeHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeHead
        fields = [
            "id",
            "institution",
            "code",
            "name_en",
            "name_bn",
            "fee_type",
            "recurrence",
            "is_optional",
            "is_refundable",
            "is_active",
            "account_code",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class FeeStructureItemSerializer(serializers.ModelSerializer):
    fee_head_name = serializers.CharField(source="fee_head.name_en", read_only=True)
    fee_head_code = serializers.CharField(source="fee_head.code", read_only=True)

    class Meta:
        model = FeeStructureItem
        fields = [
            "id",
            "fee_structure",
            "fee_head",
            "fee_head_name",
            "fee_head_code",
            "amount",
            "due_day",
            "applicable_months",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "fee_structure", "created_at", "updated_at"]


class FeeStructureSerializer(serializers.ModelSerializer):
    items = FeeStructureItemSerializer(many=True, read_only=True)
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = FeeStructure
        fields = [
            "id",
            "institution",
            "session",
            "session_name",
            "class_level",
            "class_level_name",
            "group",
            "name",
            "is_active",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class StudentFeeAssignmentSerializer(serializers.ModelSerializer):
    fee_head_name = serializers.CharField(source="fee_head.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)

    class Meta:
        model = StudentFeeAssignment
        fields = [
            "id",
            "institution",
            "student",
            "student_code",
            "student_name",
            "enrollment",
            "fee_head",
            "fee_head_name",
            "custom_amount",
            "is_exempt",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class WaiverRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaiverRule
        fields = [
            "id",
            "institution",
            "name",
            "category",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "applicable_fee_heads",
            "is_active",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class StudentWaiverSerializer(serializers.ModelSerializer):
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    waiver_rule_name = serializers.CharField(source="waiver_rule.name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.username", read_only=True)

    class Meta:
        model = StudentWaiver
        fields = [
            "id",
            "institution",
            "student",
            "student_code",
            "student_name",
            "enrollment",
            "waiver_rule",
            "waiver_rule_name",
            "title",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "applicable_fee_heads",
            "status",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "rejection_reason",
            "valid_from",
            "valid_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class WaiverRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class FineRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FineRule
        fields = [
            "id",
            "institution",
            "name",
            "fine_type",
            "grace_period_days",
            "amount",
            "max_fine_amount",
            "slab_config",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    fee_head_code = serializers.CharField(source="fee_head.code", read_only=True)
    fee_head_name = serializers.CharField(source="fee_head.name_en", read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "fee_head",
            "fee_head_code",
            "fee_head_name",
            "description",
            "amount",
            "waiver_amount",
            "fine_amount",
            "payable_amount",
            "paid_amount",
        ]
        read_only_fields = ["id"]


class InvoiceSerializer(serializers.ModelSerializer):
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "institution",
            "invoice_number",
            "student",
            "student_code",
            "student_name",
            "enrollment",
            "session",
            "session_name",
            "invoice_type",
            "title",
            "billing_month",
            "billing_year",
            "subtotal_amount",
            "waiver_amount",
            "fine_amount",
            "total_payable",
            "paid_amount",
            "due_amount",
            "status",
            "issue_date",
            "due_date",
            "paid_date",
            "pdf_receipt",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "invoice_number",
            "subtotal_amount",
            "waiver_amount",
            "fine_amount",
            "total_payable",
            "paid_amount",
            "due_amount",
            "pdf_receipt",
            "created_at",
            "updated_at",
        ]


class InvoiceDetailSerializer(InvoiceSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta(InvoiceSerializer.Meta):
        fields = InvoiceSerializer.Meta.fields + ["lines"]


class InvoiceSingleGenerateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=True)
    session_id = serializers.UUIDField(required=True)
    invoice_type = serializers.ChoiceField(choices=InvoiceType.choices, default=InvoiceType.MONTHLY)
    billing_month = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=12
    )
    billing_year = serializers.IntegerField(default=2026)
    fee_structure_id = serializers.UUIDField(required=False, allow_null=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    as_issued = serializers.BooleanField(default=True)


class InvoiceBulkPreviewSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    class_level_id = serializers.UUIDField(required=True)
    section_id = serializers.UUIDField(required=False, allow_null=True)
    billing_month = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=12
    )
    billing_year = serializers.IntegerField(default=2026)
    invoice_type = serializers.ChoiceField(choices=InvoiceType.choices, default=InvoiceType.MONTHLY)


class InvoiceBulkPreviewResponseSerializer(serializers.Serializer):
    class_level_id = serializers.CharField()
    class_level_name = serializers.CharField()
    section_id = serializers.CharField(allow_null=True)
    billing_month = serializers.IntegerField(allow_null=True)
    billing_year = serializers.IntegerField()
    total_active_students = serializers.IntegerField()
    already_invoiced_count = serializers.IntegerField()
    new_invoices_to_create = serializers.IntegerField()
    has_fee_structure = serializers.BooleanField()
    estimated_total_bdt = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceBulkGenerateSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    class_level_id = serializers.UUIDField(required=True)
    section_id = serializers.UUIDField(required=False, allow_null=True)
    billing_month = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=12
    )
    billing_year = serializers.IntegerField(default=2026)
    invoice_type = serializers.ChoiceField(choices=InvoiceType.choices, default=InvoiceType.MONTHLY)
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    as_issued = serializers.BooleanField(default=True)


class InvoiceBulkGenerateResponseSerializer(serializers.Serializer):
    class_level_id = serializers.CharField()
    total_active_students = serializers.IntegerField()
    created_count = serializers.IntegerField()
    skipped_duplicate_count = serializers.IntegerField()
    total_billed_bdt = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_invoice_ids = serializers.ListField(child=serializers.CharField())


class InvoiceCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3)


class DueListItemSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_name_en = serializers.CharField()
    student_name_bn = serializers.CharField()
    roll_no = serializers.IntegerField(allow_null=True)
    class_name = serializers.CharField()
    section_name = serializers.CharField()
    unpaid_invoice_count = serializers.IntegerField()
    total_due_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    oldest_overdue_date = serializers.DateField(allow_null=True)
