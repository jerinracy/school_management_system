"""API ViewSets for Guardians, Families, and Authorized Pickups."""

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import TenantScopedMixin
from apps.guardians.models import AuthorizedPickup, Family, Guardian, StudentGuardian
from apps.guardians.permissions import CanManageGuardians, CanViewGuardians, IsGuardianOfStudent
from apps.guardians.serializers import (
    AuthorizedPickupSerializer,
    FamilySerializer,
    GuardianAssignLoginSerializer,
    GuardianDetailSerializer,
    GuardianSerializer,
    LinkSiblingsFamilySerializer,
    LinkStudentActionSerializer,
    MergeGuardianActionSerializer,
    MyChildrenSerializer,
    StudentGuardianSerializer,
    UnlinkStudentActionSerializer,
    VerifyPickupOTPActionSerializer,
)
from apps.guardians.services import (
    create_portal_user_for_guardian,
    generate_family_code,
    generate_pickup_verification_otp,
    link_siblings_to_family,
    link_student_guardian,
    merge_duplicate_guardians,
    register_pickup_person,
    suggest_siblings,
    unlink_student_guardian,
    verify_pickup_otp,
)
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import Student


def _get_request_institution(request: Request) -> Institution:
    user = request.user
    if not hasattr(user, "institution") or user.institution is None:
        raise ValidationError("User has no associated institution.")
    return user.institution


class GuardianViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage master guardian records, student linkage, and parent portal activation."""

    queryset = Guardian.objects.select_related("family", "user").prefetch_related(
        "student_relations__student"
    )
    serializer_class = GuardianSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name_en", "name_bn", "phone", "nid"]
    filterset_fields = ["relation_default", "is_emergency_contact", "family"]
    ordering_fields = ["name_en", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action == "my_children":
            return [permissions.IsAuthenticated()]
        if self.action in ["list", "retrieve", "sibling_suggestions"]:
            return [permissions.IsAuthenticated(), (CanViewGuardians | CanManageGuardians)()]
        return [permissions.IsAuthenticated(), CanManageGuardians()]

    def get_serializer_class(self) -> type[Any]:
        if self.action == "retrieve":
            return GuardianDetailSerializer
        if self.action == "link_student":
            return LinkStudentActionSerializer
        if self.action == "unlink_student":
            return UnlinkStudentActionSerializer
        if self.action == "merge_duplicates":
            return MergeGuardianActionSerializer
        if self.action == "my_children":
            return MyChildrenSerializer
        return GuardianSerializer

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        if self.action in ["link_student", "unlink_student", "merge_duplicates"]:
            return qs

        session_id = self.request.query_params.get("session") or self.request.headers.get(
            "X-Academic-Session"
        )
        if not session_id:
            inst = _get_request_institution(self.request)
            active_session = AcademicSession.objects.filter(
                institution=inst, is_current=True, is_deleted=False
            ).first()
            if active_session:
                session_id = str(active_session.id)

        if session_id and session_id != "all":
            qs = qs.filter(
                student_relations__student__enrollments__session_id=session_id,
                student_relations__student__enrollments__status="active",
                student_relations__student__enrollments__is_deleted=False,
            ).distinct()
        return qs

    def perform_destroy(self, instance: Guardian) -> None:
        if instance.user:
            instance.user.is_active = False
            instance.user.save(update_fields=["is_active"])
        instance.delete()

    @extend_schema(request=LinkStudentActionSerializer, responses={200: StudentGuardianSerializer})
    @action(detail=True, methods=["post"], url_path="link-student")
    def link_student(self, request: Request, pk: str | None = None) -> Response:
        """Establish or update relationship between this guardian and a student."""
        guardian = self.get_object()
        serializer = LinkStudentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inst = _get_request_institution(request)

        student = Student.objects.filter(
            id=serializer.validated_data["student_id"],
            institution=inst,
        ).first()
        if not student:
            raise ValidationError({"student_id": "Student not found in this institution."})

        sg = link_student_guardian(
            institution=inst,
            student=student,
            guardian=guardian,
            relation=serializer.validated_data["relation"],
            is_primary=serializer.validated_data["is_primary"],
            can_pickup=serializer.validated_data["can_pickup"],
            receives_sms=serializer.validated_data["receives_sms"],
            financial_responsible=serializer.validated_data["financial_responsible"],
        )
        return Response(StudentGuardianSerializer(sg).data, status=status.HTTP_200_OK)

    @extend_schema(request=UnlinkStudentActionSerializer, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="unlink-student")
    def unlink_student(self, request: Request, pk: str | None = None) -> Response:
        """Sever relationship between this guardian and a student."""
        guardian = self.get_object()
        serializer = UnlinkStudentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inst = _get_request_institution(request)

        student = Student.objects.filter(
            id=serializer.validated_data["student_id"],
            institution=inst,
        ).first()
        if not student:
            raise ValidationError({"student_id": "Student not found in this institution."})

        success = unlink_student_guardian(
            institution=inst,
            student=student,
            guardian=guardian,
        )
        if not success:
            raise ValidationError({"detail": "Relationship link not found."})

        return Response({"detail": "Student unlinked successfully."}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Assign or Reset Guardian App Login",
        request=GuardianAssignLoginSerializer,
        responses={200: dict},
    )
    @action(detail=True, methods=["post"], url_path="create-portal-account")
    def create_portal_account(self, request: Request, pk: str | None = None) -> Response:
        """Generate, assign, or reset login credentials for the Guardian portal & mobile app."""
        guardian = self.get_object()
        serializer = GuardianAssignLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password")
        phone = serializer.validated_data.get("phone")

        user, _ = create_portal_user_for_guardian(guardian, password=password, phone=phone)
        return Response(
            {
                "detail": "Guardian portal user provisioned and credentials sent via SMS.",
                "user_id": str(user.id),
                "phone": user.phone,
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: MyChildrenSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="my-children")
    def my_children(self, request: Request) -> Response:
        """List all active student wards linked to the logged-in guardian user."""
        user = request.user
        if not user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)

        inst = _get_request_institution(request)
        links = (
            StudentGuardian.objects.filter(
                guardian__user_id=user.id,
                institution=inst,
            )
            .select_related("student", "guardian")
            .prefetch_related(
                "student__enrollments__session",
                "student__enrollments__class_level",
                "student__enrollments__section",
            )
        )

        # Fallback to phone match if guardian record is not directly FK linked to user
        if not links.exists() and hasattr(user, "phone") and user.phone:
            links = (
                StudentGuardian.objects.filter(
                    guardian__phone=user.phone,
                    institution=inst,
                )
                .select_related("student", "guardian")
                .prefetch_related(
                    "student__enrollments__session",
                    "student__enrollments__class_level",
                    "student__enrollments__section",
                )
            )

        results = []
        for link in links:
            s = link.student
            results.append(
                {
                    "id": s.id,
                    "student_id": s.student_id,
                    "name_en": s.name_en,
                    "name_bn": s.name_bn,
                    "gender": s.gender,
                    "blood_group": s.blood_group,
                    "status": s.status,
                    "photo": s.photo,
                    "relation": link.relation,
                    "is_primary": link.is_primary,
                    "can_pickup": link.can_pickup,
                    "receives_sms": link.receives_sms,
                    "financial_responsible": link.financial_responsible,
                    "student": s,
                }
            )

        serializer = MyChildrenSerializer(results, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=MergeGuardianActionSerializer, responses={200: GuardianDetailSerializer})
    @action(detail=False, methods=["post"], url_path="merge-duplicates")
    def merge_duplicates(self, request: Request) -> Response:
        """Merge multiple duplicate guardian records into a designated primary guardian."""
        serializer = MergeGuardianActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inst = _get_request_institution(request)

        primary_id = serializer.validated_data["primary_guardian_id"]
        dup_ids = serializer.validated_data["duplicate_guardian_ids"]

        primary = Guardian.objects.filter(id=primary_id, institution=inst).first()
        if not primary:
            raise ValidationError({"primary_guardian_id": "Primary guardian not found."})

        duplicates = list(
            Guardian.objects.filter(id__in=dup_ids, institution=inst).exclude(id=primary.id)
        )

        merged = merge_duplicate_guardians(
            institution=inst,
            primary_guardian=primary,
            duplicate_guardians=duplicates,
        )
        return Response(GuardianDetailSerializer(merged).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: list[dict]})
    @action(detail=False, methods=["get"], url_path="sibling-suggestions")
    def sibling_suggestions(self, request: Request) -> Response:
        """Find potential sibling relationships via shared phone or NID."""
        guardian_id = request.query_params.get("guardian_id")
        student_id = request.query_params.get("student_id")
        inst = _get_request_institution(request)

        guardian = None
        student = None

        if guardian_id:
            guardian = Guardian.objects.filter(id=guardian_id, institution=inst).first()
        if student_id:
            student = Student.objects.filter(id=student_id, institution=inst).first()

        suggestions = suggest_siblings(
            institution=inst,
            guardian=guardian,
            student=student,
        )
        return Response(suggestions, status=status.HTTP_200_OK)


class FamilyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage household Family groups and sibling links."""

    queryset = Family.objects.all()
    serializer_class = FamilySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["family_code", "name", "primary_contact_phone"]
    ordering_fields = ["family_code", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewGuardians | CanManageGuardians)()]
        return [permissions.IsAuthenticated(), CanManageGuardians()]

    def perform_create(self, serializer: Any) -> None:
        inst = _get_request_institution(self.request)
        family_code = serializer.validated_data.get("family_code")
        if not family_code:
            family_code = generate_family_code(inst)
        serializer.save(institution=inst, family_code=family_code)

    @extend_schema(request=LinkSiblingsFamilySerializer, responses={200: FamilySerializer})
    @action(detail=True, methods=["post"], url_path="link-siblings")
    def link_siblings(self, request: Request, pk: str | None = None) -> Response:
        """Link specified student guardians into this household Family unit."""
        family = self.get_object()
        serializer = LinkSiblingsFamilySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inst = _get_request_institution(request)

        student_ids = serializer.validated_data["student_ids"]
        updated_family = link_siblings_to_family(
            institution=inst,
            family=family,
            student_ids=[str(sid) for sid in student_ids],
        )
        return Response(FamilySerializer(updated_family).data, status=status.HTTP_200_OK)


class AuthorizedPickupViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage authorized pickup persons and OTP verification."""

    queryset = AuthorizedPickup.objects.select_related("student")
    serializer_class = AuthorizedPickupSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "phone", "nid", "relation"]
    filterset_fields = ["student", "is_active", "otp_verified"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [
                permissions.IsAuthenticated(),
                (CanViewGuardians | CanManageGuardians | IsGuardianOfStudent)(),
            ]
        return [
            permissions.IsAuthenticated(),
            (CanManageGuardians | IsGuardianOfStudent)(),
        ]

    def perform_create(self, serializer: Any) -> None:
        inst = _get_request_institution(self.request)
        student = serializer.validated_data["student"]
        if student.institution_id != inst.id:
            raise ValidationError({"student": "Student not found in this institution."})

        pickup = register_pickup_person(
            institution=inst,
            student=student,
            name=serializer.validated_data["name"],
            relation=serializer.validated_data["relation"],
            phone=serializer.validated_data["phone"],
            nid=serializer.validated_data.get("nid", ""),
            photo=serializer.validated_data.get("photo"),
            notes=serializer.validated_data.get("notes", ""),
        )
        serializer.instance = pickup

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["post"], url_path="send-otp")
    def send_otp(self, request: Request, pk: str | None = None) -> Response:
        """Send verification OTP to student's primary guardian."""
        pickup = self.get_object()
        generate_pickup_verification_otp(pickup)
        return Response(
            {"detail": "Verification OTP dispatched to registered guardian mobile."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=VerifyPickupOTPActionSerializer, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="verify-otp")
    def verify_otp(self, request: Request, pk: str | None = None) -> Response:
        """Verify entered OTP code to validate pickup person authorization."""
        pickup = self.get_object()
        serializer = VerifyPickupOTPActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entered_otp = serializer.validated_data["otp"]
        success = verify_pickup_otp(pickup, entered_otp)
        if not success:
            raise ValidationError({"otp": "Invalid or expired OTP code."})

        return Response(
            {"detail": "Pickup authorization verified successfully.", "otp_verified": True},
            status=status.HTTP_200_OK,
        )
