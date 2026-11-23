"""Serializers for Student Management."""

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
from apps.guardians.models import StudentGuardian
from apps.institutions.models import AcademicSession
from apps.students.models import (
    EnrollmentStatus,
    PreviousSchool,
    PromotionBatch,
    PromotionItem,
    Student,
    StudentDocument,
    StudentEnrollment,
    StudentIDCard,
    Testimonial,
    TransferCertificate,
)
from apps.students.services.intake import generate_next_student_id
from apps.students.services.student_service import create_portal_user_for_student


class StudentEnrollmentBriefSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="class_level.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    shift_name = serializers.CharField(source="shift.name", read_only=True, default=None)
    student_name_en = serializers.CharField(source="student.name_en", read_only=True, default="")
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True, default="")
    student_id_number = serializers.CharField(
        source="student.student_id", read_only=True, default=""
    )
    gender = serializers.CharField(source="student.gender", read_only=True, default="M")
    avatar_url = serializers.SerializerMethodField(read_only=True)

    def get_avatar_url(self, obj: StudentEnrollment) -> str | None:
        if obj.student and getattr(obj.student, "photo", None):
            try:
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(obj.student.photo.url)
                return obj.student.photo.url
            except Exception:
                return None
        return None

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "student_name_en",
            "student_name_bn",
            "student_id_number",
            "gender",
            "avatar_url",
            "session",
            "session_name",
            "class_level",
            "class_name",
            "section",
            "section_name",
            "group",
            "group_name",
            "shift",
            "shift_name",
            "roll_no",
            "enrollment_date",
            "status",
        ]


class StudentEnrollmentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "session",
            "class_level",
            "section",
            "group",
            "shift",
            "roll_no",
            "enrollment_date",
            "status",
        ]
        extra_kwargs = {
            "enrollment_date": {"required": False},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        from django.utils import timezone

        if not attrs.get("enrollment_date"):
            attrs["enrollment_date"] = timezone.localdate()

        section = attrs.get("section")
        class_level = attrs.get("class_level")
        if section and class_level and section.class_level_id != class_level.id:
            raise serializers.ValidationError(
                {
                    "section": f"Section '{section.name}' does not belong to class '{class_level.name}'."
                }
            )

        return attrs


class StudentLinkedGuardianSerializer(serializers.ModelSerializer):
    """Serializer for a guardian linked to a student with demographic details."""

    guardian_id = serializers.UUIDField(source="guardian.id", read_only=True)
    name_en = serializers.CharField(source="guardian.name_en", read_only=True)
    name_bn = serializers.CharField(source="guardian.name_bn", read_only=True)
    phone = serializers.CharField(source="guardian.phone", read_only=True)
    alt_phone = serializers.CharField(source="guardian.alt_phone", read_only=True)
    email = serializers.EmailField(source="guardian.email", read_only=True)
    nid = serializers.CharField(source="guardian.nid", read_only=True)
    occupation = serializers.CharField(source="guardian.occupation", read_only=True)
    present_address = serializers.CharField(source="guardian.present_address", read_only=True)
    photo = serializers.FileField(source="guardian.photo", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            "id",
            "guardian_id",
            "name_en",
            "name_bn",
            "relation",
            "phone",
            "alt_phone",
            "email",
            "nid",
            "occupation",
            "present_address",
            "photo",
            "is_primary",
            "can_pickup",
            "receives_sms",
            "financial_responsible",
            "created_at",
        ]


class StudentListSerializer(serializers.ModelSerializer):
    active_enrollment = serializers.SerializerMethodField()
    is_enrolled_in_active_session = serializers.SerializerMethodField()
    active_session_name = serializers.SerializerMethodField()
    has_app_account = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(source="user.id", read_only=True, default=None)
    guardians = StudentLinkedGuardianSerializer(
        source="guardian_relations", many=True, read_only=True
    )

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "phone",
            "photo",
            "gender",
            "blood_group",
            "religion",
            "status",
            "admission_date",
            "active_enrollment",
            "is_enrolled_in_active_session",
            "active_session_name",
            "has_app_account",
            "user_id",
            "guardians",
        ]

    def _resolve_scoped_enrollment(self, obj: Student) -> tuple[Any, bool, str | None]:
        request = self.context.get("request")
        session_id = None
        if request:
            session_id = request.query_params.get("session") or request.headers.get(
                "X-Academic-Session"
            )
            if session_id == "all":
                session_id = None

        active_session = None
        if not session_id and obj.institution_id:
            active_session = AcademicSession.objects.filter(
                institution_id=obj.institution_id, is_current=True, is_deleted=False
            ).first()
            if active_session:
                session_id = str(active_session.id)
        elif session_id:
            active_session = AcademicSession.objects.filter(id=session_id, is_deleted=False).first()

        qs = obj.enrollments.filter(
            status=EnrollmentStatus.ACTIVE, is_deleted=False
        ).select_related("class_level", "section", "session")
        if session_id:
            enrollment = qs.filter(session_id=session_id).first()
            is_enrolled = enrollment is not None
        else:
            enrollment = qs.first()
            is_enrolled = enrollment is not None

        session_name = (
            active_session.name
            if active_session
            else (enrollment.session.name if enrollment and enrollment.session else None)
        )
        return enrollment, is_enrolled, session_name

    def get_has_app_account(self, obj: Student) -> bool:
        return obj.user_id is not None

    def get_active_enrollment(self, obj: Student) -> dict[str, Any] | None:
        enrollment, _, _ = self._resolve_scoped_enrollment(obj)
        if not enrollment:
            return None
        return StudentEnrollmentBriefSerializer(enrollment, context=self.context).data

    def get_is_enrolled_in_active_session(self, obj: Student) -> bool:
        _, is_enrolled, _ = self._resolve_scoped_enrollment(obj)
        return is_enrolled

    def get_active_session_name(self, obj: Student) -> str | None:
        _, _, session_name = self._resolve_scoped_enrollment(obj)
        return session_name


class PreviousSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreviousSchool
        fields = [
            "id",
            "school_name",
            "board",
            "last_class_passed",
            "tc_number",
            "tc_date",
            "gpa_obtained",
        ]


class StudentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDocument
        fields = [
            "id",
            "document_type",
            "title",
            "file",
            "is_verified",
            "verified_at",
            "verified_by",
            "created_at",
        ]
        read_only_fields = ["is_verified", "verified_at", "verified_by", "created_at"]


class StudentIDCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentIDCard
        fields = [
            "id",
            "card_no",
            "qr_payload",
            "rfid_uid",
            "issue_date",
            "expiry_date",
            "is_active",
            "printed_at",
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    enrollments = StudentEnrollmentBriefSerializer(many=True, read_only=True)
    active_enrollment = serializers.SerializerMethodField()
    is_enrolled_in_active_session = serializers.SerializerMethodField()
    active_session_name = serializers.SerializerMethodField()
    previous_school = PreviousSchoolSerializer(read_only=True)
    documents = StudentDocumentSerializer(many=True, read_only=True)
    id_cards = StudentIDCardSerializer(many=True, read_only=True)
    guardians = StudentLinkedGuardianSerializer(
        source="guardian_relations", many=True, read_only=True
    )
    has_app_account = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(source="user.id", read_only=True, default=None)
    login_phone = serializers.CharField(source="user.phone", read_only=True, default=None)

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "phone",
            "has_app_account",
            "user_id",
            "login_phone",
            "dob",
            "gender",
            "blood_group",
            "religion",
            "birth_reg_no",
            "photo",
            "present_address",
            "permanent_address",
            "status",
            "admission_date",
            "is_orphan",
            "has_disability",
            "disability_details",
            "quota_category",
            "has_stipend",
            "emergency_contact_name",
            "emergency_contact_phone",
            "enrollments",
            "active_enrollment",
            "is_enrolled_in_active_session",
            "active_session_name",
            "previous_school",
            "documents",
            "id_cards",
            "guardians",
            "created_at",
            "updated_at",
        ]

    def _resolve_scoped_enrollment(self, obj: Student) -> tuple[Any, bool, str | None]:
        request = self.context.get("request")
        session_id = None
        if request:
            session_id = request.query_params.get("session") or request.headers.get(
                "X-Academic-Session"
            )
            if session_id == "all":
                session_id = None

        active_session = None
        if not session_id and obj.institution_id:
            active_session = AcademicSession.objects.filter(
                institution_id=obj.institution_id, is_current=True, is_deleted=False
            ).first()
            if active_session:
                session_id = str(active_session.id)
        elif session_id:
            active_session = AcademicSession.objects.filter(id=session_id, is_deleted=False).first()

        qs = obj.enrollments.filter(
            status=EnrollmentStatus.ACTIVE, is_deleted=False
        ).select_related("class_level", "section", "session")
        if session_id:
            enrollment = qs.filter(session_id=session_id).first()
            is_enrolled = enrollment is not None
        else:
            enrollment = qs.first()
            is_enrolled = enrollment is not None

        session_name = (
            active_session.name
            if active_session
            else (enrollment.session.name if enrollment and enrollment.session else None)
        )
        return enrollment, is_enrolled, session_name

    def get_has_app_account(self, obj: Student) -> bool:
        return obj.user_id is not None

    def get_active_enrollment(self, obj: Student) -> dict[str, Any] | None:
        enrollment, _, _ = self._resolve_scoped_enrollment(obj)
        if not enrollment:
            return None
        return StudentEnrollmentBriefSerializer(enrollment, context=self.context).data

    def get_is_enrolled_in_active_session(self, obj: Student) -> bool:
        _, is_enrolled, _ = self._resolve_scoped_enrollment(obj)
        return is_enrolled

    def get_active_session_name(self, obj: Student) -> str | None:
        _, _, session_name = self._resolve_scoped_enrollment(obj)
        return session_name

    def to_representation(self, instance: Student) -> dict[str, Any]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        # Mask sensitive birth_reg_no and phone if user is not staff/admin
        if request and request.user and not (request.user.is_staff or request.user.is_superuser):
            if not request.user.has_perm("students.manage"):
                if data.get("birth_reg_no") and len(data["birth_reg_no"]) == 17:
                    data["birth_reg_no"] = (
                        data["birth_reg_no"][:4] + "*********" + data["birth_reg_no"][-4:]
                    )
                if (
                    data.get("emergency_contact_phone")
                    and len(data["emergency_contact_phone"]) >= 10
                ):
                    data["emergency_contact_phone"] = (
                        data["emergency_contact_phone"][:4]
                        + "****"
                        + data["emergency_contact_phone"][-3:]
                    )
        return data


class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(max_length=32, required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    give_app_access = serializers.BooleanField(required=False, default=False, write_only=True)
    initial_password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "phone",
            "dob",
            "gender",
            "blood_group",
            "religion",
            "birth_reg_no",
            "photo",
            "present_address",
            "permanent_address",
            "status",
            "admission_date",
            "is_orphan",
            "has_disability",
            "disability_details",
            "quota_category",
            "has_stipend",
            "emergency_contact_name",
            "emergency_contact_phone",
            "give_app_access",
            "initial_password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data: dict[str, Any]) -> Student:
        give_app_access = validated_data.pop("give_app_access", False)
        initial_password = validated_data.pop("initial_password", None)

        if not validated_data.get("student_id"):
            institution = validated_data.get("institution")
            current_year = str(timezone.localdate().year)
            if institution:
                validated_data["student_id"] = generate_next_student_id(
                    institution_id=institution.id,
                    session_year=current_year,
                    class_order=1,
                )
            else:
                validated_data["student_id"] = f"{current_year}010001"

        student = super().create(validated_data)

        if give_app_access:
            create_portal_user_for_student(
                student,
                phone=student.phone,
                password=initial_password,
            )

        return student

    @transaction.atomic
    def update(self, instance: Student, validated_data: dict[str, Any]) -> Student:
        give_app_access = validated_data.pop("give_app_access", False)
        initial_password = validated_data.pop("initial_password", None)

        old_phone = instance.phone
        student = super().update(instance, validated_data)

        # Sync phone with linked user if phone changed and user exists
        if student.user and student.phone and student.phone != old_phone:
            user = student.user
            user.phone = student.phone
            user.save(update_fields=["phone"])

        # Create portal user if requested and not yet linked
        if give_app_access and not student.user:
            create_portal_user_for_student(
                student,
                phone=student.phone,
                password=initial_password,
            )

        return student

    def validate_phone(self, value: str | None) -> str | None:
        if value:
            return normalize_bd_phone(value)
        return value

    def validate_birth_reg_no(self, value: str | None) -> str | None:
        if value:
            cleaned = value.strip()
            if len(cleaned) != 17 or not cleaned.isdigit():
                raise serializers.ValidationError(
                    "Bangladeshi Birth Registration Number must be exactly 17 digits."
                )
            return cleaned
        return value

    def validate_emergency_contact_phone(self, value: str | None) -> str:
        if value:
            return normalize_bd_phone(value)
        return ""


class StudentAssignLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=6, required=True)

    def validate_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value


class AdmitFromApplicationSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    roll_no = serializers.IntegerField(min_value=1)
    session_id = serializers.UUIDField(required=False)
    student_id = serializers.CharField(max_length=32, required=False)


class AutoAssignRollsSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    strategy = serializers.ChoiceField(
        choices=["name_en", "name_bn", "student_id"], default="name_en"
    )


class PromotionItemSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)
    target_class_name = serializers.CharField(source="target_class.name", read_only=True)
    target_section_name = serializers.CharField(source="target_section.name", read_only=True)

    class Meta:
        model = PromotionItem
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name",
            "from_enrollment",
            "target_class",
            "target_class_name",
            "target_section",
            "target_section_name",
            "target_roll_no",
            "action",
            "gpa",
            "remarks",
        ]


class PromotionBatchSerializer(serializers.ModelSerializer):
    from_session_name = serializers.CharField(source="from_session.name", read_only=True)
    to_session_name = serializers.CharField(source="to_session.name", read_only=True)
    from_class_name = serializers.CharField(source="from_class.name", read_only=True)
    to_class_name = serializers.CharField(source="to_class.name", read_only=True)
    items = PromotionItemSerializer(many=True, read_only=True)

    class Meta:
        model = PromotionBatch
        fields = [
            "id",
            "from_session",
            "from_session_name",
            "to_session",
            "to_session_name",
            "from_class",
            "from_class_name",
            "to_class",
            "to_class_name",
            "status",
            "total_students",
            "promoted_count",
            "retained_count",
            "applied_at",
            "created_at",
            "items",
        ]


class PromotionPreviewRequestSerializer(serializers.Serializer):
    from_session_id = serializers.UUIDField()
    to_session_id = serializers.UUIDField()
    from_class_id = serializers.UUIDField()
    to_class_id = serializers.UUIDField()
    default_target_section_id = serializers.UUIDField(required=False)
    passing_gpa_threshold = serializers.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("2.00")
    )
    student_overrides = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )


class TransferCertificateSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)

    class Meta:
        model = TransferCertificate
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name_en",
            "student_name_bn",
            "enrollment",
            "tc_number",
            "issue_date",
            "reason",
            "conduct_remarks",
            "dues_cleared",
            "pdf_file",
            "created_at",
        ]
        read_only_fields = ["tc_number", "pdf_file", "created_at"]


class IssueTCSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    reason = serializers.CharField()
    conduct_remarks = serializers.CharField(default="Satisfactory")
    dues_cleared = serializers.BooleanField(default=True)


class TestimonialSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name_en",
            "enrollment",
            "certificate_no",
            "issue_date",
            "exam_name",
            "passing_year",
            "gpa",
            "character",
            "pdf_file",
            "created_at",
        ]
        read_only_fields = ["certificate_no", "pdf_file", "created_at"]


class IssueTestimonialSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    exam_name = serializers.CharField()
    passing_year = serializers.IntegerField(min_value=2000, max_value=2100)
    gpa = serializers.DecimalField(max_digits=4, decimal_places=2)
    character = serializers.CharField(default="Good")


class BulkImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    dry_run = serializers.BooleanField(default=True)
