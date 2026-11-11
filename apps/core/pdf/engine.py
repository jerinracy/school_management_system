"""ReportLab PDF generation engine with Unicode Bengali font support."""

import io
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, SimpleDocTemplate

_FONTS_REGISTERED = False
BENGALI_FONT_NAME = "Kalpurush"
BENGALI_FONT_FALLBACKS = [
    Path(__file__).resolve().parent.parent / "fonts" / "Kalpurush.ttf",
    Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"),
    Path("/home/sifat/.local/share/fonts/fonts-bangla/kalpurush/kalpurush.ttf"),
]


def ensure_bengali_fonts_registered() -> str:
    """Register Bengali TrueType font with ReportLab if not already registered.

    Returns the name of the registered font.
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return BENGALI_FONT_NAME

    font_path: Path | None = None
    for candidate in BENGALI_FONT_FALLBACKS:
        if candidate.exists():
            font_path = candidate
            break

    if font_path and font_path.exists():
        pdfmetrics.registerFont(TTFont(BENGALI_FONT_NAME, str(font_path)))
        _FONTS_REGISTERED = True
        return BENGALI_FONT_NAME

    # Fallback to Helvetica if no TTF font is accessible
    return "Helvetica"


def get_bengali_stylesheet() -> dict[str, ParagraphStyle]:
    """Return a stylesheet pre-configured with Bengali font and clean styling."""
    font_name = ensure_bengali_fonts_registered()
    base_styles = getSampleStyleSheet()

    primary_color = HexColor("#1E3A8A")  # Deep blue
    text_color = HexColor("#1F2937")  # Slate 800
    muted_color = HexColor("#4B5563")  # Slate 600

    styles = {
        "Title": ParagraphStyle(
            "BengaliTitle",
            parent=base_styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=24,
            textColor=primary_color,
            alignment=1,  # Center
            spaceAfter=6,
        ),
        "Subtitle": ParagraphStyle(
            "BengaliSubtitle",
            parent=base_styles["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=16,
            textColor=muted_color,
            alignment=1,
            spaceAfter=12,
        ),
        "DocHeader": ParagraphStyle(
            "BengaliDocHeader",
            parent=base_styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=18,
            textColor=primary_color,
            alignment=1,
            spaceBefore=8,
            spaceAfter=14,
        ),
        "Body": ParagraphStyle(
            "BengaliBody",
            parent=base_styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=15,
            textColor=text_color,
            spaceAfter=6,
        ),
        "Label": ParagraphStyle(
            "BengaliLabel",
            parent=base_styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=primary_color,
        ),
        "Value": ParagraphStyle(
            "BengaliValue",
            parent=base_styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=text_color,
        ),
        "Footer": ParagraphStyle(
            "BengaliFooter",
            parent=base_styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=muted_color,
            alignment=1,
        ),
    }
    return styles


def render_story_to_pdf(
    story: list[Flowable],
    pagesize: tuple[float, float] = A4,
    margin: float = 36.0,
    **doc_kwargs: Any,
) -> bytes:
    """Render a Platypus story into raw PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        **doc_kwargs,
    )
    doc.build(story)
    return buffer.getvalue()
