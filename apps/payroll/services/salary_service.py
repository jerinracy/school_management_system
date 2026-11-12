"""Salary component and structure seeding/management services."""

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.institutions.models import Institution
from apps.payroll.models import (
    CalculationType,
    ComponentType,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)

DEFAULT_COMPONENTS: list[dict] = [
    {
        "code": "BASIC",
        "name_en": "Basic Salary",
        "name_bn": "মূল বেতন",
        "component_type": ComponentType.EARNING,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("0.00"),
        "is_taxable": True,
        "is_system": True,
        "display_order": 1,
    },
    {
        "code": "HRA",
        "name_en": "House Rent Allowance",
        "name_bn": "বাড়ি ভাড়া ভাতা",
        "component_type": ComponentType.EARNING,
        "calculation_type": CalculationType.PERCENTAGE_OF_BASIC,
        "default_value": Decimal("40.00"),
        "is_taxable": True,
        "is_system": True,
        "display_order": 2,
    },
    {
        "code": "MED",
        "name_en": "Medical Allowance",
        "name_bn": "চিকিৎসা ভাতা",
        "component_type": ComponentType.EARNING,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("1500.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 3,
    },
    {
        "code": "CONV",
        "name_en": "Conveyance Allowance",
        "name_bn": "যাতায়াত ভাতা",
        "component_type": ComponentType.EARNING,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("1000.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 4,
    },
    {
        "code": "PF_EMP",
        "name_en": "Provident Fund (Employee)",
        "name_bn": "ভবিষ্যৎ তহবিল (কর্মী)",
        "component_type": ComponentType.DEDUCTION,
        "calculation_type": CalculationType.PERCENTAGE_OF_BASIC,
        "default_value": Decimal("10.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 10,
    },
    {
        "code": "TDS",
        "name_en": "Income Tax (TDS)",
        "name_bn": "উৎসে আয়কর",
        "component_type": ComponentType.DEDUCTION,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("0.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 11,
    },
    {
        "code": "ABSENCE",
        "name_en": "Absence / LWP Deduction",
        "name_bn": "অনুপস্থিতি কর্তন",
        "component_type": ComponentType.DEDUCTION,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("0.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 12,
    },
    {
        "code": "LOAN_REC",
        "name_en": "Loan / Advance Recovery",
        "name_bn": "ঋণ / অগ্রিম কর্তন",
        "component_type": ComponentType.DEDUCTION,
        "calculation_type": CalculationType.FIXED,
        "default_value": Decimal("0.00"),
        "is_taxable": False,
        "is_system": True,
        "display_order": 13,
    },
]


@transaction.atomic
def seed_default_salary_components(institution: Institution) -> dict[str, SalaryComponent]:
    """Idempotently seed standard Bangladeshi school salary components for an institution."""
    result: dict[str, SalaryComponent] = {}
    for spec in DEFAULT_COMPONENTS:
        comp, _ = SalaryComponent.objects.get_or_create(
            institution=institution,
            code=spec["code"],
            is_deleted=False,
            defaults={
                "name_en": spec["name_en"],
                "name_bn": spec["name_bn"],
                "component_type": spec["component_type"],
                "calculation_type": spec["calculation_type"],
                "default_value": spec["default_value"],
                "is_taxable": spec["is_taxable"],
                "is_system": spec["is_system"],
                "display_order": spec["display_order"],
                "is_active": True,
            },
        )
        result[comp.code] = comp
    return result


@transaction.atomic
def seed_default_salary_structures(institution: Institution) -> list[SalaryStructure]:
    """Seed standard Bangladeshi school salary structure templates."""
    components = seed_default_salary_components(institution)

    templates: list[dict[str, Any]] = [
        {
            "code": "TEACHER_STD",
            "name": "Standard Teacher Salary Structure",
            "name_bn": "আদর্শ শিক্ষক বেতন কাঠামো",
            "description": "Basic + 40% House Rent + BDT 1,500 Medical + BDT 1,000 Conveyance.",
            "lines": [
                ("HRA", CalculationType.PERCENTAGE_OF_BASIC, Decimal("40.00")),
                ("MED", CalculationType.FIXED, Decimal("1500.00")),
                ("CONV", CalculationType.FIXED, Decimal("1000.00")),
            ],
        },
        {
            "code": "MPO_TEACHER",
            "name": "MPO Enlisted Teacher Structure",
            "name_bn": "এমপিওভুক্ত শিক্ষক বেতন কাঠামো",
            "description": "MPO-aligned allowances with institutional top-up support.",
            "lines": [
                ("HRA", CalculationType.FIXED, Decimal("1000.00")),
                ("MED", CalculationType.FIXED, Decimal("500.00")),
            ],
        },
        {
            "code": "ADMIN_STAFF",
            "name": "Administrative & Support Staff Structure",
            "name_bn": "প্রশাসনিক ও সহায়ক কর্মচারী কাঠামো",
            "description": "Basic + 40% House Rent + BDT 1,500 Medical.",
            "lines": [
                ("HRA", CalculationType.PERCENTAGE_OF_BASIC, Decimal("40.00")),
                ("MED", CalculationType.FIXED, Decimal("1500.00")),
            ],
        },
    ]

    structures: list[SalaryStructure] = []
    for tpl in templates:
        structure, _ = SalaryStructure.objects.get_or_create(
            institution=institution,
            code=tpl["code"],
            is_deleted=False,
            defaults={
                "name": tpl["name"],
                "name_bn": tpl["name_bn"],
                "description": tpl["description"],
                "is_active": True,
            },
        )
        for comp_code, calc_type, val in tpl["lines"]:
            comp = components[comp_code]
            SalaryStructureLine.objects.get_or_create(
                institution=institution,
                structure=structure,
                component=comp,
                defaults={
                    "calculation_type": calc_type,
                    "value": val,
                },
            )
        structures.append(structure)
    return structures
