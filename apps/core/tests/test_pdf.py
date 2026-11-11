"""Tests for Bangla PDF generation engine and certificate templates."""

import pytest

from apps.core.pdf import (
    ensure_bengali_fonts_registered,
    generate_student_id_card_pdf,
    generate_testimonial_pdf,
    generate_transfer_certificate_pdf,
)


@pytest.mark.django_db
class TestBanglaPDFGeneration:
    def test_bengali_font_registration(self):
        font_name = ensure_bengali_fonts_registered()
        assert font_name in ["Kalpurush", "Helvetica"]

    def test_generate_transfer_certificate_pdf(self):
        institution_data = {
            "name_bn": "ঢাকা মডেল হাই স্কুল অ্যান্ড কলেজ",
            "name_en": "Dhaka Model High School & College",
            "eiin": "134567",
            "address": "মিরপুর-১০, ঢাকা-১২১৬",
            "phone": "+8801711000000",
        }
        student_data = {
            "name_bn": "মোহাম্মদ রাকিবুল হাসান",
            "name_en": "Md. Rakibul Hasan",
            "student_id": "2026100001",
            "dob": "2010-05-15",
            "birth_reg_no": "20101234567890123",
            "blood_group": "A+",
            "emergency_contact_phone": "+8801711223344",
        }
        enrollment_data = {
            "class_name": "Class 10",
            "section_name": "Section A",
            "roll_no": 5,
            "session_name": "2026",
        }
        tc_data = {
            "tc_number": "TC-2026-00001",
            "issue_date": "2026-11-11",
            "reason": "অভিভাবকের বদলিজনিত কারণে",
            "conduct_remarks": "উত্তম ও সন্তোষজনক",
            "dues_cleared": True,
        }

        pdf_bytes = generate_transfer_certificate_pdf(
            institution_data=institution_data,
            student_data=student_data,
            enrollment_data=enrollment_data,
            tc_data=tc_data,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_testimonial_pdf(self):
        institution_data = {
            "name_bn": "ঢাকা মডেল হাই স্কুল অ্যান্ড কলেজ",
            "name_en": "Dhaka Model High School & College",
            "eiin": "134567",
            "address": "মিরপুর-১০, ঢাকা-১২১৬",
        }
        student_data = {
            "name_bn": "ফাতিমা আক্তার",
            "name_en": "Fatima Akter",
            "student_id": "2026100002",
        }
        enrollment_data = {
            "class_name": "Class 10",
            "section_name": "Section B",
            "roll_no": 1,
            "session_name": "2026",
        }
        testimonial_data = {
            "certificate_no": "TST-2026-00001",
            "issue_date": "2026-11-11",
            "exam_name": "এসএসসি (SSC)",
            "passing_year": 2026,
            "gpa": "5.00",
            "character": "উত্তম",
        }

        pdf_bytes = generate_testimonial_pdf(
            institution_data=institution_data,
            student_data=student_data,
            enrollment_data=enrollment_data,
            testimonial_data=testimonial_data,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_student_id_card_pdf(self):
        institution_data = {
            "name_bn": "ঢাকা মডেল হাই স্কুল অ্যান্ড কলেজ",
            "name_en": "Dhaka Model High School & College",
        }
        student_data = {
            "name_bn": "তানভীর আহমেদ",
            "name_en": "Tanvir Ahmed",
            "student_id": "2026090015",
            "blood_group": "B+",
            "emergency_contact_phone": "+8801811223344",
        }
        enrollment_data = {
            "class_name": "Class 9",
            "section_name": "Padma",
            "roll_no": 15,
        }
        id_card_data = {
            "card_no": "IDC-2026-0015",
        }

        pdf_bytes = generate_student_id_card_pdf(
            institution_data=institution_data,
            student_data=student_data,
            enrollment_data=enrollment_data,
            id_card_data=id_card_data,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
