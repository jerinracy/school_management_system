"""PDF generation utilities and templates for Bengali documents."""

from apps.core.pdf.engine import ensure_bengali_fonts_registered, render_story_to_pdf
from apps.core.pdf.templates import (
    generate_student_id_card_pdf,
    generate_testimonial_pdf,
    generate_transfer_certificate_pdf,
)

__all__ = [
    "ensure_bengali_fonts_registered",
    "render_story_to_pdf",
    "generate_transfer_certificate_pdf",
    "generate_testimonial_pdf",
    "generate_student_id_card_pdf",
]
