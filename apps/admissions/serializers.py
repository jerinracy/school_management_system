"""Serializers for admission circulars, applications, tests, and merit lists."""

from typing import Any

from rest_framework import serializers

from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTest,
    AdmissionTestResult,
    Application,
    ApplicationDocument,
    ApplicationPayment,
    ApplicationStatus,
    CircularStatus,
    LotteryDraw,
    MeritList,
    MeritListEntry,
    QuotaRule,
)
from apps.admissions.services.application_workflow import (
    check_duplicate_application,
    generate_application_number,
    validate_applicant_eligibility,
)
from apps.core.utils.phone import normalize_bd_phone


class AdmissionCircularSerializer(serializers.ModelSerializer):
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    applications_count = serializers.IntegerField(source="applications.count", read_only=True)

    class Meta:
        model = AdmissionCircular
        fields = [
            "id",
            "session",
            "session_name",
            "class_level",
            "class_level_name",
            "title",
            "seats_available",
            "application_fee",
            "form_open_date",
            "form_close_date",
            "instructions",
            "eligibility_criteria",
            "status",
            "applications_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = self.context["request"].user.institution
        session = attrs.get("session") or (
            self.instance.session if isinstance(self.instance, AdmissionCircular) else None
        )
        class_level = attrs.get("class_level") or (
            self.instance.class_level if isinstance(self.instance, AdmissionCircular) else None
        )
        if session and session.institution_id != institution.id:
            raise serializers.ValidationError(
                {"session": "Session must belong to your institution."}
            )
        if class_level and class_level.institution_id != institution.id:
            raise serializers.ValidationError(
                {"class_level": "Class level must belong to your institution."}
            )
        return attrs


class AdmissionCircularPublicSerializer(serializers.ModelSerializer):
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = AdmissionCircular
        fields = [
            "id",
            "session_name",
            "class_level_name",
            "title",
            "seats_available",
            "application_fee",
            "form_open_date",
            "form_close_date",
            "instructions",
            "eligibility_criteria",
        ]


class QuotaRuleSerializer(serializers.ModelSerializer):
    quota_type_display = serializers.CharField(source="get_quota_type_display", read_only=True)

    class Meta:
        model = QuotaRule
        fields = [
            "id",
            "circular",
            "quota_type",
            "quota_type_display",
            "name",
            "reserved_percentage",
            "reserved_seats",
            "priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "application",
            "document_type",
            "file",
            "is_verified",
            "verified_at",
            "created_at",
        ]
        read_only_fields = ["id", "verified_at", "created_at"]


class ApplicationPaymentSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ApplicationPayment
        fields = [
            "id",
            "application",
            "amount",
            "payment_method",
            "payment_method_display",
            "transaction_id",
            "status",
            "status_display",
            "paid_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    quota_type_display = serializers.CharField(source="get_quota_type_display", read_only=True)
    class_level_name = serializers.CharField(source="circular.class_level.name", read_only=True)
    session_name = serializers.CharField(source="circular.session.name", read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    payments = ApplicationPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "circular",
            "class_level_name",
            "session_name",
            "application_no",
            "name_bn",
            "name_en",
            "dob",
            "gender",
            "birth_reg_no",
            "religion",
            "blood_group",
            "photo",
            "guardian_name",
            "guardian_phone",
            "guardian_nid",
            "guardian_relation",
            "present_address",
            "permanent_address",
            "previous_school",
            "previous_gpa",
            "quota_type",
            "quota_type_display",
            "quota_rule",
            "status",
            "status_display",
            "submitted_at",
            "notes",
            "documents",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "application_no", "submitted_at", "created_at", "updated_at"]


class ApplicationCreatePublicSerializer(serializers.ModelSerializer):
    circular_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "circular_id",
            "application_no",
            "name_bn",
            "name_en",
            "dob",
            "gender",
            "birth_reg_no",
            "religion",
            "blood_group",
            "photo",
            "guardian_name",
            "guardian_phone",
            "guardian_nid",
            "guardian_relation",
            "present_address",
            "permanent_address",
            "previous_school",
            "previous_gpa",
            "quota_type",
            "status",
        ]
        read_only_fields = ["id", "application_no", "status"]

    def validate_guardian_phone(self, value: str) -> str:
        try:
            return normalize_bd_phone(value)
        except Exception as err:
            raise serializers.ValidationError(str(err)) from None

    def validate_birth_reg_no(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isdigit() or len(cleaned) != 17:
            raise serializers.ValidationError(
                "Bangladesh Birth Registration Certificate Number must be exactly 17 digits."
            )
        return cleaned

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        circular_id = attrs.pop("circular_id")
        try:
            circular = AdmissionCircular.objects.get(
                id=circular_id, status=CircularStatus.PUBLISHED
            )
        except AdmissionCircular.DoesNotExist:
            raise serializers.ValidationError(
                {"circular_id": "Published admission circular not found."}
            ) from None

        attrs["circular"] = circular
        attrs["institution"] = circular.institution

        # Eligibility check
        validate_applicant_eligibility(
            circular=circular,
            dob=attrs["dob"],
            previous_gpa=attrs.get("previous_gpa"),
        )

        # Duplicate check
        check_duplicate_application(
            circular=circular,
            birth_reg_no=attrs["birth_reg_no"],
            dob=attrs["dob"],
        )

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Application:
        circular = validated_data["circular"]
        validated_data["application_no"] = generate_application_number(circular)
        validated_data["status"] = ApplicationStatus.DRAFT
        return super().create(validated_data)


class ApplicationTrackInputSerializer(serializers.Serializer):
    application_no = serializers.CharField(max_length=32)
    guardian_phone = serializers.CharField(max_length=20)

    def validate_guardian_phone(self, value: str) -> str:
        try:
            return normalize_bd_phone(value)
        except Exception as err:
            raise serializers.ValidationError(str(err)) from None


class ApplicationTransitionSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=ApplicationStatus.choices)
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class AdmissionTestSerializer(serializers.ModelSerializer):
    circular_title = serializers.CharField(source="circular.title", read_only=True)

    class Meta:
        model = AdmissionTest
        fields = [
            "id",
            "circular",
            "circular_title",
            "title",
            "test_date",
            "venue",
            "total_marks",
            "pass_marks",
            "instructions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdmissionTestResultSerializer(serializers.ModelSerializer):
    application_no = serializers.CharField(source="application.application_no", read_only=True)
    applicant_name = serializers.CharField(source="application.name_en", read_only=True)
    test_title = serializers.CharField(source="test.title", read_only=True)

    class Meta:
        model = AdmissionTestResult
        fields = [
            "id",
            "test",
            "test_title",
            "application",
            "application_no",
            "applicant_name",
            "marks_obtained",
            "is_passed",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        test = attrs.get("test") or (
            self.instance.test if isinstance(self.instance, AdmissionTestResult) else None
        )
        marks = attrs.get("marks_obtained")
        if test and marks is not None:
            attrs["is_passed"] = marks >= test.pass_marks
        return attrs


class LotteryDrawInputSerializer(serializers.Serializer):
    circular_id = serializers.UUIDField()
    total_to_select = serializers.IntegerField(min_value=1)
    seed = serializers.IntegerField(required=False, allow_null=True)
    auto_advance_status = serializers.BooleanField(default=False)


class LotteryDrawSerializer(serializers.ModelSerializer):
    circular_title = serializers.CharField(source="circular.title", read_only=True)

    class Meta:
        model = LotteryDraw
        fields = [
            "id",
            "circular",
            "circular_title",
            "seed",
            "draw_date",
            "total_candidates",
            "selected_candidates_count",
            "drawn_order",
            "is_confirmed",
        ]
        read_only_fields = ["id", "draw_date"]


class MeritListEntrySerializer(serializers.ModelSerializer):
    application_no = serializers.CharField(source="application.application_no", read_only=True)
    applicant_name_en = serializers.CharField(source="application.name_en", read_only=True)
    applicant_name_bn = serializers.CharField(source="application.name_bn", read_only=True)
    merit_type_display = serializers.CharField(source="get_merit_type_display", read_only=True)

    class Meta:
        model = MeritListEntry
        fields = [
            "id",
            "application",
            "application_no",
            "applicant_name_en",
            "applicant_name_bn",
            "rank",
            "merit_type",
            "merit_type_display",
            "score",
            "is_selected",
        ]


class MeritListSerializer(serializers.ModelSerializer):
    circular_title = serializers.CharField(source="circular.title", read_only=True)
    entries = MeritListEntrySerializer(many=True, read_only=True)

    class Meta:
        model = MeritList
        fields = [
            "id",
            "circular",
            "circular_title",
            "title",
            "selection_criteria",
            "is_published",
            "published_at",
            "entries",
            "created_at",
        ]
        read_only_fields = ["id", "published_at", "created_at"]


class MeritListGenerateInputSerializer(serializers.Serializer):
    circular_id = serializers.UUIDField()
    selection_criteria = serializers.ChoiceField(
        choices=["test_score", "lottery", "gpa"],
        default="test_score",
    )
    title = serializers.CharField(default="1st Merit List")
    auto_publish = serializers.BooleanField(default=False)
