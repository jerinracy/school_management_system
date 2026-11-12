"""Accounting module DRF serializers."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.accounting.models import (
    Account,
    CashbookClosing,
    FiscalYear,
    JournalEntry,
    JournalEntryItem,
)


class FiscalYearSerializer(serializers.ModelSerializer):
    """FiscalYear serializer."""

    class Meta:
        model = FiscalYear
        fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "is_closed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        inst = getattr(self, "instance", None)
        start = attrs.get("start_date") or (getattr(inst, "start_date", None) if inst else None)
        end = attrs.get("end_date") or (getattr(inst, "end_date", None) if inst else None)
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_date": "End date must be strictly after start date."}
            )
        return attrs


class AccountSerializer(serializers.ModelSerializer):
    """Hierarchical Chart of Accounts serializer."""

    parent_code = serializers.CharField(source="parent.account_code", read_only=True)
    parent_name = serializers.CharField(source="parent.name_en", read_only=True)
    normal_balance_type = serializers.CharField(source="normal_balance", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "account_code",
            "name_en",
            "name_bn",
            "account_type",
            "subtype",
            "parent",
            "parent_code",
            "parent_name",
            "is_group",
            "is_system",
            "opening_balance",
            "current_balance",
            "normal_balance_type",
            "bank_name",
            "bank_account_number",
            "bank_branch",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_balance",
            "is_system",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        parent = attrs.get("parent")
        if parent and not parent.is_group:
            raise serializers.ValidationError(
                {"parent": "Parent account must be a group/header account."}
            )
        return attrs


class JournalEntryItemSerializer(serializers.ModelSerializer):
    """Journal entry line item serializer."""

    account_code = serializers.CharField(source="account.account_code", read_only=True)
    account_name = serializers.CharField(source="account.name_en", read_only=True)

    class Meta:
        model = JournalEntryItem
        fields = [
            "id",
            "account",
            "account_code",
            "account_name",
            "debit",
            "credit",
            "narration",
        ]
        read_only_fields = ["id"]


class JournalEntrySerializer(serializers.ModelSerializer):
    """Journal entry header & items serializer with double-entry validation."""

    items = JournalEntryItemSerializer(many=True, required=False)
    fiscal_year_name = serializers.CharField(source="fiscal_year.name", read_only=True)
    posted_by_name = serializers.CharField(source="posted_by.get_full_name", read_only=True)
    voided_by_name = serializers.CharField(source="voided_by.get_full_name", read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "voucher_no",
            "voucher_type",
            "fiscal_year",
            "fiscal_year_name",
            "date",
            "narration",
            "status",
            "total_debit",
            "total_credit",
            "cheque_no",
            "payment_reference",
            "attachment",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "voided_at",
            "voided_by",
            "voided_by_name",
            "void_reason",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "voucher_no",
            "status",
            "total_debit",
            "total_credit",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "voided_at",
            "voided_by",
            "voided_by_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        initial_items = self.initial_data.get("items")
        if self.instance is None and (not initial_items or len(initial_items) < 2):
            raise serializers.ValidationError(
                {"items": "A journal entry must contain at least 2 line items."}
            )

        if initial_items:
            tot_debit = Decimal("0.00")
            tot_credit = Decimal("0.00")
            for idx, item in enumerate(initial_items):
                d = Decimal(str(item.get("debit", 0) or 0))
                c = Decimal(str(item.get("credit", 0) or 0))
                if d < 0 or c < 0:
                    raise serializers.ValidationError(
                        {"items": f"Line {idx + 1}: Negative amounts are not allowed."}
                    )
                if d == 0 and c == 0:
                    raise serializers.ValidationError(
                        {"items": f"Line {idx + 1}: Debit or credit must be greater than zero."}
                    )
                if d > 0 and c > 0:
                    raise serializers.ValidationError(
                        {
                            "items": f"Line {idx + 1}: A single line cannot have both debit and credit."
                        }
                    )
                tot_debit += d
                tot_credit += c

            if tot_debit != tot_credit:
                raise serializers.ValidationError(
                    {
                        "items": f"Double-entry violation: Total debits (৳{tot_debit}) must equal total credits (৳{tot_credit})."
                    }
                )
            if tot_debit <= 0:
                raise serializers.ValidationError(
                    {"items": "Voucher total amount must be greater than zero."}
                )

        return attrs

    def create(self, validated_data: dict[str, Any]) -> JournalEntry:
        from apps.accounting.services.voucher_service import create_journal_entry

        items_data = self.initial_data.get("items", [])
        request = self.context.get("request")
        user = request.user if request and hasattr(request, "user") else None
        institution = validated_data.pop("institution", None)
        if not institution and request:
            institution = getattr(request, "institution", None) or (
                getattr(request.user, "institution", None) if hasattr(request, "user") else None
            )

        validated_data.pop("items", None)

        return create_journal_entry(
            institution=institution,
            voucher_type=str(validated_data.get("voucher_type", "")),
            date=validated_data.get("date"),
            narration=validated_data.get("narration", ""),
            items=items_data,
            fiscal_year=validated_data.get("fiscal_year"),
            cheque_no=validated_data.get("cheque_no", ""),
            payment_reference=validated_data.get("payment_reference"),
            attachment=validated_data.get("attachment"),
            created_by=user,
        )


class CashbookClosingSerializer(serializers.ModelSerializer):
    """Daily cashbook closing reconciliation serializer."""

    account_name = serializers.CharField(source="account.name_en", read_only=True)
    closed_by_name = serializers.CharField(source="closed_by.get_full_name", read_only=True)

    class Meta:
        model = CashbookClosing
        fields = [
            "id",
            "account",
            "account_name",
            "date",
            "opening_balance",
            "total_receipts",
            "total_payments",
            "closing_balance",
            "physical_count",
            "discrepancy",
            "note",
            "closed_by",
            "closed_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "opening_balance",
            "total_receipts",
            "total_payments",
            "closing_balance",
            "discrepancy",
            "closed_by",
            "closed_by_name",
            "created_at",
        ]


class DailyCashbookQuerySerializer(serializers.Serializer):
    """Query parameters serializer for daily cashbook."""

    date = serializers.DateField(required=False)
    account_id = serializers.UUIDField(required=False)


class FinancialReportQuerySerializer(serializers.Serializer):
    """Query parameters serializer for P&L, Balance Sheet, and Trial Balance."""

    as_of_date = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    fiscal_year_id = serializers.UUIDField(required=False)
