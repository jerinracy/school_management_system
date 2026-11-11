"""Service for managing grading scales and grade tier lookups."""

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.institutions.models import Institution
from apps.results.models import GradeTier, GradingScale, ScaleType

# Bangladesh Ministry of Education Standard GPA 5.0 Grade Tiers
# (Letter, Grade Point, Min %, Max %, Remarks EN, Remarks BN)
BD_GPA_5_TIERS = [
    ("A+", Decimal("5.00"), Decimal("80.00"), Decimal("100.00"), "Outstanding", "অসাধারণ"),
    ("A", Decimal("4.00"), Decimal("70.00"), Decimal("79.99"), "Excellent", "চমৎকার"),
    ("A-", Decimal("3.50"), Decimal("60.00"), Decimal("69.99"), "Very Good", "খুব ভালো"),
    ("B", Decimal("3.00"), Decimal("50.00"), Decimal("59.99"), "Good", "ভালো"),
    ("C", Decimal("2.00"), Decimal("40.00"), Decimal("49.99"), "Satisfactory", "সন্তোষজনক"),
    ("D", Decimal("1.00"), Decimal("33.00"), Decimal("39.99"), "Pass", "উত্তীর্ণ"),
    ("F", Decimal("0.00"), Decimal("0.00"), Decimal("32.99"), "Fail", "ব্যর্থ"),
]


@transaction.atomic
def seed_default_bd_grading_scale(institution: Institution) -> GradingScale:
    """Create or retrieve the standard Bangladesh National Curriculum GPA 5.0 grading scale."""
    scale, created = GradingScale.objects.get_or_create(
        institution=institution,
        name="BD National Curriculum (GPA 5.0)",
        defaults={
            "scale_type": ScaleType.GPA_5,
            "max_gpa": Decimal("5.00"),
            "pass_gpa": Decimal("1.00"),
            "is_default": True,
            "description": "Standard grading system prescribed by the Ministry of Education, Bangladesh.",
        },
    )

    # Populate standard grade tiers if not already present
    if created or not scale.tiers.filter(is_deleted=False).exists():
        for letter, gp, min_pct, max_pct, rem_en, rem_bn in BD_GPA_5_TIERS:
            GradeTier.objects.update_or_create(
                institution=institution,
                scale=scale,
                letter_grade=letter,
                defaults={
                    "grade_point": gp,
                    "min_percentage": min_pct,
                    "max_percentage": max_pct,
                    "remarks_en": rem_en,
                    "remarks_bn": rem_bn,
                },
            )

    return scale


def get_default_grading_scale(institution: Institution) -> GradingScale:
    """Retrieve the active default grading scale for the institution, or seed one."""
    scale = (
        GradingScale.objects.filter(institution=institution, is_default=True, is_deleted=False)
        .prefetch_related("tiers")
        .first()
    )
    if not scale:
        scale = (
            GradingScale.objects.filter(institution=institution, is_deleted=False)
            .prefetch_related("tiers")
            .first()
        )
    if not scale:
        scale = seed_default_bd_grading_scale(institution)
    return scale


def resolve_grade_for_percentage(scale: GradingScale, percentage: Decimal) -> dict[str, Any]:
    """Map a numerical mark percentage to its grade point, letter grade, and remarks."""
    pct = Decimal(str(percentage)).quantize(Decimal("0.01"))

    # Handle boundary edge cases
    if pct > Decimal("100.00"):
        pct = Decimal("100.00")
    elif pct < Decimal("0.00"):
        pct = Decimal("0.00")

    tiers = list(scale.tiers.filter(is_deleted=False).order_by("-grade_point", "-min_percentage"))

    for tier in tiers:
        if tier.min_percentage <= pct <= tier.max_percentage:
            return {
                "grade_point": tier.grade_point,
                "letter_grade": tier.letter_grade,
                "remarks_en": tier.remarks_en,
                "remarks_bn": tier.remarks_bn,
            }

    # Fallback to failing grade
    f_tier = next((t for t in tiers if t.grade_point == Decimal("0.00")), None)
    if f_tier:
        return {
            "grade_point": f_tier.grade_point,
            "letter_grade": f_tier.letter_grade,
            "remarks_en": f_tier.remarks_en,
            "remarks_bn": f_tier.remarks_bn,
        }

    return {
        "grade_point": Decimal("0.00"),
        "letter_grade": "F",
        "remarks_en": "Fail",
        "remarks_bn": "ব্যর্থ",
    }


def resolve_grade_for_gpa(scale: GradingScale, gpa: Decimal) -> str:
    """Map a final calculated GPA to its corresponding letter grade in the scale."""
    val = Decimal(str(gpa)).quantize(Decimal("0.01"))
    if val >= Decimal("5.00"):
        return "A+"
    if val >= Decimal("4.00"):
        return "A"
    if val >= Decimal("3.50"):
        return "A-"
    if val >= Decimal("3.00"):
        return "B"
    if val >= Decimal("2.00"):
        return "C"
    if val >= Decimal("1.00"):
        return "D"
    return "F"
