"""DRF Serializers for fee management, invoicing, waivers, and fines."""

from decimal import Decimal

from rest_framework import serializers

from apps.fees.models import (
    AdvanceBalance,
    AdvanceTransaction,
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FineRule,
    Invoice,
    InvoiceLine,
    InvoiceType,
    MoneyReceipt,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    Refund,
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


class PaymentAllocationSerializer(serializers.ModelSerializer):
    fee_head_name = serializers.CharField(
        source="invoice_line.fee_head.name_en", read_only=True, default=""
    )

    class Meta:
        model = PaymentAllocation
        fields = [
            "id",
            "invoice",
            "invoice_line",
            "fee_head_name",
            "allocated_amount",
            "created_at",
        ]
        read_only_fields = fields


class MoneyReceiptSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True, default="")
    issued_by_name = serializers.CharField(
        source="issued_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = MoneyReceipt
        fields = [
            "id",
            "institution",
            "receipt_number",
            "payment",
            "student",
            "student_name_en",
            "student_name_bn",
            "total_amount",
            "issued_at",
            "issued_by",
            "issued_by_name",
            "pdf_receipt",
            "is_cancelled",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = ["id", "institution", "pdf_receipt", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True, default=None
    )
    received_by_name = serializers.CharField(
        source="received_by.get_full_name", read_only=True, default=None
    )
    receipt_number = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "institution",
            "student",
            "student_name_en",
            "invoice",
            "invoice_number",
            "payment_method",
            "amount",
            "status",
            "transaction_id",
            "gateway_order_id",
            "idempotency_key",
            "payment_date",
            "received_by",
            "received_by_name",
            "gateway_payload",
            "notes",
            "receipt_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def get_receipt_number(self, obj: Payment) -> str | None:
        receipt = getattr(obj, "receipt", None)
        return receipt.receipt_number if receipt else None


class PaymentDetailSerializer(PaymentSerializer):
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    receipt = MoneyReceiptSerializer(read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ["allocations", "receipt"]


class CounterPaymentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=True)
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.ChoiceField(
        choices=[
            PaymentMethod.CASH,
            PaymentMethod.BANK,
            PaymentMethod.CARD,
            PaymentMethod.BKASH,
            PaymentMethod.NAGAD,
            PaymentMethod.ROCKET,
        ],
        default=PaymentMethod.CASH,
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")
    bank_name = serializers.CharField(required=False, allow_blank=True, default="")
    cheque_no = serializers.CharField(required=False, allow_blank=True, default="")
    cheque_date = serializers.DateField(required=False, allow_null=True)
    pos_approval_code = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class OnlinePaymentInitiateSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField(required=True)
    payment_method = serializers.ChoiceField(
        choices=[
            PaymentMethod.BKASH,
            PaymentMethod.NAGAD,
            PaymentMethod.SSLCOMMERZ,
            PaymentMethod.AAMARPAY,
        ]
    )
    success_url = serializers.URLField(required=False, allow_blank=True, default="")
    fail_url = serializers.URLField(required=False, allow_blank=True, default="")
    cancel_url = serializers.URLField(required=False, allow_blank=True, default="")


class OnlinePaymentInitiateResponseSerializer(serializers.Serializer):
    payment_id = serializers.CharField()
    gateway_url = serializers.URLField()
    session_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class OnlinePaymentVerifySerializer(serializers.Serializer):
    payment_id = serializers.UUIDField(required=True)
    val_id = serializers.CharField(required=False, allow_blank=True, default="")
    payment_id_gateway = serializers.CharField(required=False, allow_blank=True, default="")
    payment_ref_id = serializers.CharField(required=False, allow_blank=True, default="")
    merchant_trans_id = serializers.CharField(required=False, allow_blank=True, default="")


class AdvanceTransactionSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True, default=None
    )

    class Meta:
        model = AdvanceTransaction
        fields = [
            "id",
            "advance_balance",
            "payment",
            "invoice",
            "invoice_number",
            "amount",
            "balance_after",
            "transaction_type",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class AdvanceBalanceSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True, default="")
    transactions = AdvanceTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = AdvanceBalance
        fields = [
            "id",
            "institution",
            "student",
            "student_name_en",
            "student_name_bn",
            "current_balance",
            "transactions",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "current_balance", "transactions", "updated_at"]


class ApplyAdvanceSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class RefundSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name", read_only=True, default=None
    )
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Refund
        fields = [
            "id",
            "institution",
            "payment",
            "student",
            "student_name_en",
            "amount",
            "reason",
            "status",
            "requested_by",
            "requested_by_name",
            "approved_by",
            "approved_by_name",
            "processed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "requested_by",
            "approved_by",
            "processed_at",
            "created_at",
            "updated_at",
        ]


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(required=True, min_length=3)


class RefundRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=True, min_length=3)


class DailyCollectionReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()
    by_method = serializers.DictField()
