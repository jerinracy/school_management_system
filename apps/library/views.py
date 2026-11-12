"""DRF ViewSets for Library Management."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, F, Q, QuerySet, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin
from apps.institutions.models import Branch
from apps.library.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    BookIssue,
    BookIssueStatus,
    EBook,
    LibraryFine,
    LibraryFineStatus,
    LibraryMember,
    LibraryPolicy,
    Reservation,
)
from apps.library.permissions import (
    CanManageLibrary,
    CanManageOrIssueLibrary,
    CanReadLibraryPortal,
    CanReserveLibraryBook,
    has_library_staff_permission,
    resolve_guardian_ward_ids,
    resolve_staff_for_user,
    resolve_student_for_user,
)
from apps.library.serializers import (
    BookCopySerializer,
    BookIssueCreateSerializer,
    BookIssueSerializer,
    BookRenewSerializer,
    BookReturnSerializer,
    BookSerializer,
    CatalogImportResponseSerializer,
    CatalogImportSerializer,
    EBookSerializer,
    FinePaymentSerializer,
    FineWaiveSerializer,
    LibraryFineSerializer,
    LibraryMemberSerializer,
    LibraryPolicySerializer,
    MemberHistoryResponseSerializer,
    ReservationSerializer,
)
from apps.library.services import (
    cancel_reservation,
    import_books_from_xlsx,
    issue_book,
    record_fine_payment,
    renew_book,
    reserve_book,
    resolve_copy_for_circulation,
    return_book,
    waive_fine,
)


def _ensure_same_tenant(institution_id: Any, obj: Any, field_name: str) -> None:
    if obj is not None and getattr(obj, "institution_id", None) != institution_id:
        raise DRFValidationError({field_name: f"Selected {field_name} belongs to another tenant."})


def _visible_member_filter(user: User) -> Q:
    student = resolve_student_for_user(user)
    if student is not None:
        return Q(member__student=student)
    staff = resolve_staff_for_user(user)
    if staff is not None:
        return Q(member__staff=staff)
    ward_ids = resolve_guardian_ward_ids(user)
    if ward_ids:
        return Q(member__student_id__in=ward_ids)
    return Q(pk__isnull=True)


def _resolve_self_member(user: User) -> LibraryMember | None:
    if not user.institution_id:
        return None
    student = resolve_student_for_user(user)
    if student is not None:
        return LibraryMember.objects.filter(
            institution_id=user.institution_id, student=student, is_deleted=False
        ).first()
    staff = resolve_staff_for_user(user)
    if staff is not None:
        return LibraryMember.objects.filter(
            institution_id=user.institution_id, staff=staff, is_deleted=False
        ).first()
    return None


@extend_schema_view(
    list=extend_schema(summary="List Library Policies"),
    retrieve=extend_schema(summary="Get Library Policy"),
    create=extend_schema(summary="Create Library Policy"),
    partial_update=extend_schema(summary="Update Library Policy"),
    destroy=extend_schema(summary="Delete Library Policy"),
)
class LibraryPolicyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage borrowing, renewal, and fine policies."""

    queryset = LibraryPolicy.objects.select_related("branch").all()
    serializer_class = LibraryPolicySerializer
    permission_classes = [IsAuthenticated, CanManageLibrary]
    filterset_fields = ["branch", "member_type"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageLibrary()]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="Search Library Book Catalog"),
    retrieve=extend_schema(summary="Get Book Details"),
    create=extend_schema(summary="Add Book to Catalog"),
    partial_update=extend_schema(summary="Update Book"),
    destroy=extend_schema(summary="Delete Book"),
)
class BookViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Catalog search, popular books, and Excel bulk import."""

    queryset = Book.objects.select_related("subject").all()
    serializer_class = BookSerializer
    filterset_fields = ["category", "language", "subject", "is_reference_only"]
    search_fields = ["isbn", "title", "title_bn", "authors", "publisher", "category"]
    ordering_fields = ["title", "publication_year", "created_at", "issue_count"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageLibrary()]

    def get_queryset(self) -> QuerySet[Book]:
        qs = super().get_queryset().filter(is_deleted=False)
        return qs.annotate(
            total_copies=Count("copies", filter=Q(copies__is_deleted=False), distinct=True),
            available_copies=Count(
                "copies",
                filter=Q(copies__is_deleted=False, copies__status=BookCopyStatus.AVAILABLE),
                distinct=True,
            ),
            issue_count=Count("copies__issues", distinct=True),
        ).order_by("title")

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("subject"), "subject"
        )
        super().perform_create(serializer)

    def perform_update(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("subject"), "subject"
        )
        serializer.save()

    @extend_schema(summary="List Most Popular Books", responses={200: BookSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def popular(self, request: Request) -> Response:
        base_qs: Any = self.get_queryset()
        qs = base_qs.filter(issue_count__gt=0).order_by("-issue_count", "title")[:20]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Import Books & Copies from Excel (.xlsx)",
        request=CatalogImportSerializer,
        responses={200: CatalogImportResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="import-xlsx",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated, CanManageLibrary],
    )
    def import_xlsx(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = CatalogImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        branch_id = serializer.validated_data.get("branch")
        branch = None
        if branch_id:
            branch = Branch.objects.filter(id=branch_id, institution=user.institution).first()
            if branch is None:
                raise DRFValidationError({"branch": "Branch not found in this institution."})
        try:
            summary = import_books_from_xlsx(
                institution=user.institution,
                file_bytes=uploaded.read(),
                branch=branch,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(summary, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Book Copies"),
    retrieve=extend_schema(summary="Get Book Copy"),
    create=extend_schema(summary="Add Book Copy"),
    partial_update=extend_schema(summary="Update Book Copy"),
    destroy=extend_schema(summary="Delete Book Copy"),
)
class BookCopyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Physical copy inventory with barcode/RFID scan lookup."""

    queryset = BookCopy.objects.select_related("book", "branch").all()
    serializer_class = BookCopySerializer
    filterset_fields = ["book", "branch", "status"]
    search_fields = ["accession_no", "barcode", "rfid_tag", "shelf_location", "book__title"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageLibrary()]

    def get_queryset(self) -> QuerySet[BookCopy]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("book"), "book")
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        super().perform_create(serializer)

    @extend_schema(
        summary="Lookup Book Copy by Barcode, RFID, or Accession Number",
        parameters=[
            OpenApiParameter("accession_no", str, required=False),
            OpenApiParameter("barcode", str, required=False),
            OpenApiParameter("rfid_tag", str, required=False),
        ],
        responses={200: BookCopySerializer},
    )
    @action(detail=False, methods=["get"])
    def lookup(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        try:
            copy = resolve_copy_for_circulation(
                institution=user.institution,
                accession_no=request.query_params.get("accession_no") or None,
                barcode=request.query_params.get("barcode") or None,
                rfid_tag=request.query_params.get("rfid_tag") or None,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(copy).data)


@extend_schema_view(
    list=extend_schema(summary="List Library Members"),
    retrieve=extend_schema(summary="Get Library Member"),
    create=extend_schema(summary="Create Library Member"),
    partial_update=extend_schema(summary="Update Library Member"),
    destroy=extend_schema(summary="Delete Library Member"),
)
class LibraryMemberViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Library membership cards and member borrowing/fine history."""

    queryset = LibraryMember.objects.select_related("student", "staff", "branch").all()
    serializer_class = LibraryMemberSerializer
    filterset_fields = ["member_type", "status", "branch"]
    search_fields = [
        "card_number",
        "rfid_card_uid",
        "student__student_id",
        "student__name_en",
        "staff__employee_id",
        "staff__full_name_en",
    ]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageLibrary()]

    def get_queryset(self) -> QuerySet[LibraryMember]:
        qs = super().get_queryset().filter(is_deleted=False)
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_library_staff_permission(self.request, self):
            return qs
        student = resolve_student_for_user(user)
        if student is not None:
            return qs.filter(student=student)
        staff = resolve_staff_for_user(user)
        if staff is not None:
            return qs.filter(staff=staff)
        ward_ids = resolve_guardian_ward_ids(user)
        if ward_ids:
            return qs.filter(student_id__in=ward_ids)
        return qs.none()

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("student"), "student"
        )
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("staff"), "staff")
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        super().perform_create(serializer)

    @extend_schema(
        summary="Get Member Borrowing, Reservation, and Fine History",
        responses={200: MemberHistoryResponseSerializer},
    )
    @action(detail=True, methods=["get"])
    def history(self, request: Request, pk: str | None = None) -> Response:
        member = self.get_object()
        issues = BookIssue.objects.select_related("copy", "copy__book", "member").filter(
            institution_id=member.institution_id,
            member=member,
        )
        active_issues = issues.filter(status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE])
        past_issues = issues.filter(status__in=[BookIssueStatus.RETURNED, BookIssueStatus.LOST])
        reservations = Reservation.objects.select_related("book", "member").filter(
            institution_id=member.institution_id,
            member=member,
        )
        fines = LibraryFine.objects.select_related("issue", "issue__copy__book", "member").filter(
            institution_id=member.institution_id,
            member=member,
        )
        unpaid_total = fines.filter(
            status__in=[LibraryFineStatus.UNPAID, LibraryFineStatus.PARTIALLY_PAID]
        ).aggregate(total=Sum(F("amount") - F("paid_amount")))["total"] or Decimal("0.00")

        payload = {
            "member": LibraryMemberSerializer(member).data,
            "active_issues": BookIssueSerializer(active_issues, many=True).data,
            "past_issues": BookIssueSerializer(past_issues, many=True).data,
            "reservations": ReservationSerializer(reservations, many=True).data,
            "fines": LibraryFineSerializer(fines, many=True).data,
            "unpaid_fine_total": unpaid_total,
        }
        return Response(payload)


@extend_schema_view(
    list=extend_schema(summary="List Book Issues"),
    retrieve=extend_schema(summary="Get Book Issue"),
)
class BookIssueViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Circulation endpoints: issue, return, renew, and overdue list."""

    queryset = BookIssue.objects.select_related("copy", "copy__book", "member").all()
    serializer_class = BookIssueSerializer
    filterset_fields = ["status", "member", "copy"]
    search_fields = [
        "copy__accession_no",
        "copy__barcode",
        "copy__book__title",
        "member__card_number",
    ]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageOrIssueLibrary()]

    def get_queryset(self) -> QuerySet[BookIssue]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_library_staff_permission(self.request, self):
            return qs
        return qs.filter(_visible_member_filter(user))

    @extend_schema(
        summary="Issue a Book Copy (Barcode / RFID / Accession Scan)",
        request=BookIssueCreateSerializer,
        responses={201: BookIssueSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanManageOrIssueLibrary],
    )
    def issue(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = BookIssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            record = issue_book(
                institution=user.institution,
                actor=user,
                member_id=data.get("member_id"),
                card_number=data.get("card_number") or None,
                rfid_card_uid=data.get("rfid_card_uid") or None,
                copy_id=data.get("copy_id"),
                accession_no=data.get("accession_no") or None,
                barcode=data.get("barcode") or None,
                rfid_tag=data.get("rfid_tag") or None,
                due_date=data.get("due_date"),
                remarks=data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(BookIssueSerializer(record).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Return a Book Copy (Barcode / RFID / Accession Scan)",
        request=BookReturnSerializer,
        responses={200: BookIssueSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="return",
        permission_classes=[IsAuthenticated, CanManageOrIssueLibrary],
    )
    def return_copy(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = BookReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            record = return_book(
                institution=user.institution,
                actor=user,
                issue_id=data.get("issue_id"),
                accession_no=data.get("accession_no") or None,
                barcode=data.get("barcode") or None,
                rfid_tag=data.get("rfid_tag") or None,
                return_date=data.get("return_date"),
                mark_damaged=data.get("mark_damaged", False),
                mark_lost=data.get("mark_lost", False),
                damage_fine_amount=data.get("damage_fine_amount"),
                remarks=data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(BookIssueSerializer(record).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Renew an Active Book Issue",
        request=BookRenewSerializer,
        responses={200: BookIssueSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanManageOrIssueLibrary],
    )
    def renew(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = BookRenewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            record = renew_book(
                institution=user.institution,
                issue_id=data["issue_id"],
                extra_days=data.get("extra_days"),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(BookIssueSerializer(record).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List Overdue Book Issues", responses={200: BookIssueSerializer(many=True)}
    )
    @action(detail=False, methods=["get"])
    def overdue(self, request: Request) -> Response:
        today = timezone.localdate()
        qs = self.get_queryset().filter(
            status__in=[BookIssueStatus.ISSUED, BookIssueStatus.OVERDUE],
            due_date__lt=today,
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List Book Reservations"),
    retrieve=extend_schema(summary="Get Reservation"),
    create=extend_schema(summary="Reserve a Book"),
)
class ReservationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """FIFO book reservations."""

    queryset = Reservation.objects.select_related("book", "member", "fulfilled_copy").all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated, CanReserveLibraryBook]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["book", "member", "status"]

    def get_queryset(self) -> QuerySet[Reservation]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_library_staff_permission(self.request, self):
            return qs
        return qs.filter(_visible_member_filter(user))

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data["book"]
        _ensure_same_tenant(user.institution_id, book, "book")

        if has_library_staff_permission(request, self) and serializer.validated_data.get("member"):
            member = serializer.validated_data["member"]
            _ensure_same_tenant(user.institution_id, member, "member")
        else:
            member = _resolve_self_member(user)
            if member is None:
                raise PermissionDenied("No active library membership linked to your account.")

        try:
            reservation = reserve_book(
                institution=user.institution,
                book=book,
                member=member,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(reservation).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Cancel Reservation", request=None, responses={200: ReservationSerializer}
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        reservation = self.get_object()
        if not has_library_staff_permission(request, self):
            self_member = _resolve_self_member(user)
            if self_member is None or reservation.member_id != self_member.id:
                raise PermissionDenied("You may only cancel your own reservation.")
        try:
            updated = cancel_reservation(institution=user.institution, reservation=reservation)
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)


@extend_schema_view(
    list=extend_schema(summary="List Library Fines"),
    retrieve=extend_schema(summary="Get Library Fine"),
)
class LibraryFineViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Library fine records, payments, and waivers."""

    queryset = LibraryFine.objects.select_related("issue", "issue__copy__book", "member").all()
    serializer_class = LibraryFineSerializer
    filterset_fields = ["member", "status", "reason"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageOrIssueLibrary()]

    def get_queryset(self) -> QuerySet[LibraryFine]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_library_staff_permission(self.request, self):
            return qs
        return qs.filter(_visible_member_filter(user))

    @extend_schema(
        summary="Record Library Fine Payment",
        request=FinePaymentSerializer,
        responses={200: LibraryFineSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanManageOrIssueLibrary],
    )
    def pay(self, request: Request, pk: str | None = None) -> Response:
        fine = self.get_object()
        serializer = FinePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = record_fine_payment(
                fine=fine,
                amount=serializer.validated_data["amount"],
                payment_reference=serializer.validated_data.get("payment_reference", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)

    @extend_schema(
        summary="Waive Library Fine",
        request=FineWaiveSerializer,
        responses={200: LibraryFineSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanManageLibrary],
    )
    def waive(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        fine = self.get_object()
        serializer = FineWaiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = waive_fine(
                fine=fine,
                actor=user,
                waive_reason=serializer.validated_data.get("waive_reason", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)


@extend_schema_view(
    list=extend_schema(summary="List Digital Resources & E-Books"),
    retrieve=extend_schema(summary="Get E-Book Details"),
    create=extend_schema(summary="Upload or Link E-Book"),
    partial_update=extend_schema(summary="Update E-Book"),
    destroy=extend_schema(summary="Delete E-Book"),
)
class EBookViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Digital library resources and e-books."""

    queryset = EBook.objects.select_related("book", "subject").all()
    serializer_class = EBookSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["category", "language", "book", "subject", "is_public_to_members"]
    search_fields = ["title", "title_bn", "authors", "category"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadLibraryPortal()]
        return [IsAuthenticated(), CanManageLibrary()]

    def get_queryset(self) -> QuerySet[EBook]:
        qs = super().get_queryset().filter(is_deleted=False)
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_library_staff_permission(self.request, self):
            return qs
        return qs.filter(is_public_to_members=True)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("book"), "book")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("subject"), "subject"
        )
        super().perform_create(serializer)
