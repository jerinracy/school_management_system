"""Unit tests for Payment Gateways (SSLCommerz, bKash, Nagad, aamarPay) and IPN reconciliation."""

from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import UserType
from apps.accounts.test_helpers import make_user
from apps.fees.gateways import (
    AamarPayAdapter,
    BKashAdapter,
    NagadAdapter,
    SSLCommerzAdapter,
    get_gateway_adapter,
)
from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecurrenceType,
)
from apps.fees.services import (
    complete_online_payment,
    generate_single_student_invoice,
    initiate_online_payment,
)
from apps.fees.tasks import reconcile_pending_payments_task
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def gateway_test_fixture(db: None) -> dict:
    client = APIClient()
    inst = Institution.objects.create(name_en="Gateway Test School", name_bn="গেটওয়ে টেস্ট স্কুল")
    branch = Branch.objects.create(institution=inst, name="Campus 1")
    session = AcademicSession.objects.create(
        institution=inst,
        name="Session 2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Day",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 8", code="C8", order=8)
    section = Section.objects.create(
        institution=inst,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )

    admin_user = make_user(
        username="gw_admin",
        institution=inst,
        phone="+8801722003344",
    )
    admin_user.is_superuser = True
    admin_user.save()

    student_user = make_user(
        username="gw_student",
        institution=inst,
        phone="+8801722998877",
        user_type=UserType.STUDENT,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-GW-001",
        name_en="Karim Sheikh",
        name_bn="করিম শেখ",
        admission_date="2026-01-01",
        dob="2011-04-12",
    )
    student_user.student_profile = student  # type: ignore[attr-defined]
    student_user.save()
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        roll_no=5,
        enrollment_date="2026-01-01",
    )

    fee_head = FeeHead.objects.create(
        institution=inst,
        code="TUITION_8",
        name_en="Tuition Class 8",
        name_bn="বেতন অষ্টম শ্রেণি",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    structure = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=class_level,
        name="Class 8 Fees",
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=structure,
        fee_head=fee_head,
        amount=Decimal("1200.00"),
    )

    invoice = generate_single_student_invoice(
        student=student,
        session=session,
        invoice_type=InvoiceType.MONTHLY,
        billing_year=2026,
        billing_month=4,
        fee_structure=structure,
        due_date=date(2026, 4, 25),
        as_issued=True,
    )

    return {
        "client": client,
        "inst": inst,
        "admin_user": admin_user,
        "student": student,
        "invoice": invoice,
    }


@pytest.mark.django_db
def test_sslcommerz_adapter_flow(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    invoice: Invoice = data["invoice"]
    adapter = get_gateway_adapter(PaymentMethod.SSLCOMMERZ)
    assert isinstance(adapter, SSLCommerzAdapter)

    # 1. Mock SSLCommerz Session Creation
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "status": "SUCCESS",
        "sessionkey": "SSL_SESSION_KEY_12345",
        "GatewayPageURL": "https://sandbox.sslcommerz.com/gwprocess/v4/gw.php?Q=SSL_SESSION_KEY_12345",
    }

    with patch("requests.post", return_value=mock_post_resp):
        res = initiate_online_payment(
            invoice=invoice,
            payment_method=PaymentMethod.SSLCOMMERZ,
            urls={"success_url": "https://school.edu.bd/success"},
            payer_user=data["admin_user"],
        )

    assert "gateway_url" in res
    assert res["session_id"] == "SSL_SESSION_KEY_12345"

    payment = Payment.objects.get(id=res["payment_id"])
    assert payment.status == PaymentStatus.PENDING

    # 2. Mock SSLCommerz Validation
    mock_val_resp = MagicMock()
    mock_val_resp.status_code = 200
    mock_val_resp.json.return_value = {
        "status": "VALID",
        "val_id": "VALID_SSL_9999",
        "tran_id": payment.gateway_order_id,
        "amount": "1200.00",
        "currency": "BDT",
        "bank_tran_id": "BANK_TRX_8888",
    }

    with patch("requests.get", return_value=mock_val_resp):
        completed = complete_online_payment(payment, {"val_id": "VALID_SSL_9999"})

    assert completed.status == PaymentStatus.SUCCESSFUL
    assert completed.transaction_id == "BANK_TRX_8888"

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_amount == Decimal("1200.00")
    assert invoice.due_amount == Decimal("0.00")


@pytest.mark.django_db
def test_bkash_adapter_flow(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    invoice: Invoice = data["invoice"]
    adapter = get_gateway_adapter(PaymentMethod.BKASH)
    assert isinstance(adapter, BKashAdapter)

    mock_create_resp = MagicMock()
    mock_create_resp.status_code = 200
    mock_create_resp.json.return_value = {
        "statusCode": "0000",
        "paymentID": "BKASH_PAY_ID_001",
        "bkashURL": "https://sandbox.payment.bkash.com/redirect/BKASH_PAY_ID_001",
    }

    with patch("requests.post", return_value=mock_create_resp):
        res = initiate_online_payment(
            invoice=invoice,
            payment_method=PaymentMethod.BKASH,
            payer_user=data["admin_user"],
        )

    assert res["session_id"] == "BKASH_PAY_ID_001"
    payment = Payment.objects.get(id=res["payment_id"])

    completed = complete_online_payment(
        payment,
        {"paymentID": "BKASH_PAY_ID_001", "status": "success", "trxID": "BKASH_TRX_9999"},
    )

    assert completed.status == PaymentStatus.SUCCESSFUL
    assert completed.transaction_id == "BKASH_TRX_9999"


@pytest.mark.django_db
def test_nagad_adapter_flow(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    invoice: Invoice = data["invoice"]
    adapter = get_gateway_adapter(PaymentMethod.NAGAD)
    assert isinstance(adapter, NagadAdapter)

    mock_init_resp = MagicMock()
    mock_init_resp.status_code = 200
    mock_init_resp.json.return_value = {
        "status": "Success",
        "callBackUrl": "https://sandbox.nagad.com.bd/checkout?order=NAGAD_ORD_123",
        "paymentReferenceId": "NAGAD_REF_123",
    }

    with patch("requests.post", return_value=mock_init_resp):
        res = initiate_online_payment(
            invoice=invoice,
            payment_method=PaymentMethod.NAGAD,
            payer_user=data["admin_user"],
        )

    payment = Payment.objects.get(id=res["payment_id"])

    completed = complete_online_payment(
        payment,
        {
            "payment_ref_id": "NAGAD_REF_123",
            "status": "Success",
            "issuer_payment_ref": "NAGAD_TRX_7777",
        },
    )

    assert completed.status == PaymentStatus.SUCCESSFUL
    assert completed.transaction_id == "NAGAD_TRX_7777"


@pytest.mark.django_db
def test_aamarpay_adapter_flow(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    invoice: Invoice = data["invoice"]
    adapter = get_gateway_adapter(PaymentMethod.AAMARPAY)
    assert isinstance(adapter, AamarPayAdapter)

    mock_init_resp = MagicMock()
    mock_init_resp.status_code = 200
    mock_init_resp.json.return_value = {
        "result": "true",
        "payment_url": "https://sandbox.aamarpay.com/paynow?track=AAMAR_TRACK_123",
    }

    with patch("requests.post", return_value=mock_init_resp):
        res = initiate_online_payment(
            invoice=invoice,
            payment_method=PaymentMethod.AAMARPAY,
            payer_user=data["admin_user"],
        )

    payment = Payment.objects.get(id=res["payment_id"])

    completed = complete_online_payment(
        payment,
        {
            "mer_txnid": payment.gateway_order_id,
            "pay_status": "Successful",
            "pg_txnid": "AAMAR_TRX_6666",
        },
    )

    assert completed.status == PaymentStatus.SUCCESSFUL
    assert completed.transaction_id == "AAMAR_TRX_6666"


@pytest.mark.django_db
def test_gateway_webhook_endpoint(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    client: APIClient = data["client"]

    # Pre-create an initiated payment
    payment = Payment.objects.create(
        institution=data["inst"],
        student=data["student"],
        invoice=data["invoice"],
        amount=Decimal("1200.00"),
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=PaymentStatus.PENDING,
        gateway_order_id="SSL_ORDER_WH_001",
        idempotency_key="WH-KEY-001",
    )

    mock_val = MagicMock()
    mock_val.status_code = 200
    mock_val.json.return_value = {
        "status": "VALID",
        "val_id": "VAL_WH_999",
        "tran_id": "SSL_ORDER_WH_001",
        "amount": "1200.00",
    }

    with patch("requests.get", return_value=mock_val):
        resp = client.post(
            "/api/v1/fees/payments/webhook/sslcommerz/",
            {
                "tran_id": "SSL_ORDER_WH_001",
                "val_id": "VAL_WH_999",
                "status": "VALID",
                "verify_sign": "MOCK_SIGN",
            },
            format="json",
        )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "accepted"}

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCESSFUL


@pytest.mark.django_db
def test_reconcile_pending_payments_task(gateway_test_fixture: dict) -> None:
    data = gateway_test_fixture
    # Create an old pending payment (> 20 mins ago)
    old_time = timezone.now() - timedelta(minutes=25)
    payment = Payment.objects.create(
        institution=data["inst"],
        student=data["student"],
        invoice=data["invoice"],
        amount=Decimal("1200.00"),
        payment_method=PaymentMethod.SSLCOMMERZ,
        status=PaymentStatus.PENDING,
        gateway_order_id="SSL_RECON_001",
        idempotency_key="RECON-001",
    )
    Payment.objects.filter(id=payment.id).update(created_at=old_time)

    mock_val = MagicMock()
    mock_val.status_code = 200
    mock_val.json.return_value = {
        "status": "VALID",
        "val_id": "VAL_RECON_777",
        "tran_id": "SSL_RECON_001",
        "amount": "1200.00",
    }

    with patch("requests.get", return_value=mock_val):
        res = reconcile_pending_payments_task(
            institution_id=str(data["inst"].id),
            older_than_minutes=15,
        )

    assert res["reconciled"] == 1
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCESSFUL
