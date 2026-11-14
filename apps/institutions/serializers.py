"""DRF Serializers for institutions."""

from typing import Any

from rest_framework import serializers

from .models import AcademicSession, Branch, Holiday, Institution, Shift, Term
from .services import validate_institution_settings


class InstitutionPublicBrandingSerializer(serializers.ModelSerializer):
    """Publicly accessible branding and institutional identity serializer."""

    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id",
            "name_bn",
            "name_en",
            "eiin",
            "board",
            "type",
            "logo",
            "logo_url",
            "phone",
            "email",
            "website",
            "address_line",
            "district",
            "division",
        ]
        read_only_fields = fields

    def get_logo_url(self, obj: Institution) -> str | None:
        if not obj.logo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url


class InstitutionSerializer(serializers.ModelSerializer):
    """Serializer for Institution profile read and update."""

    class Meta:
        model = Institution
        fields = [
            "id",
            "name_bn",
            "name_en",
            "eiin",
            "mpo_status",
            "board",
            "type",
            "division",
            "district",
            "upazila",
            "address_line",
            "phone",
            "email",
            "website",
            "logo",
            "seal",
            "signature",
            "timezone",
            "currency",
            "weekend_days",
            "settings",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_settings(self, value: dict[str, Any]) -> dict[str, Any]:
        return validate_institution_settings(value)


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch."""

    class Meta:
        model = Branch
        fields = [
            "id",
            "institution",
            "name",
            "code",
            "address",
            "is_main",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class ShiftSerializer(serializers.ModelSerializer):
    """Serializer for Shift."""

    branch_code = serializers.CharField(source="branch.code", read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id",
            "institution",
            "branch",
            "branch_code",
            "name",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_time": "Shift end time must be after start time."}
            )
        return attrs


class TermSerializer(serializers.ModelSerializer):
    """Serializer for Term."""

    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Term
        fields = [
            "id",
            "institution",
            "session",
            "session_name",
            "name",
            "start_date",
            "end_date",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_date": "Term end date must be strictly after start date."}
            )

        session = attrs.get("session", getattr(self.instance, "session", None))
        if session and start and end:
            if start < session.start_date or end > session.end_date:
                raise serializers.ValidationError(
                    "Term dates must fall within the academic session range."
                )
        return attrs


class AcademicSessionSerializer(serializers.ModelSerializer):
    """Serializer for AcademicSession."""

    terms = TermSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicSession
        fields = [
            "id",
            "institution",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "status",
            "terms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "is_current", "status", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_date": "Session end date must be strictly after start date."}
            )
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    """Serializer for Holiday."""

    class Meta:
        model = Holiday
        fields = [
            "id",
            "institution",
            "name",
            "type",
            "start_date",
            "end_date",
            "applies_to_all_branches",
            "branches",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start > end:
            raise serializers.ValidationError(
                {"end_date": "Holiday end date cannot be before start date."}
            )
        return attrs


class SessionCloseSerializer(serializers.Serializer):
    """Serializer for confirming session closure."""

    confirm = serializers.BooleanField(
        required=True,
        help_text="Must be True to confirm irreversible session closure.",
    )
