"""Chart of Accounts management and balance calculations."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Sum

from apps.accounting.models import (
    Account,
    AccountSubtype,
    AccountType,
    VoucherStatus,
)

if TYPE_CHECKING:
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)

DEFAULT_COA = [
    # 1000 - ASSETS
    {
        "code": "1000",
        "name_en": "Assets",
        "name_bn": "সম্পদ",
        "type": AccountType.ASSET,
        "is_group": True,
        "parent": None,
    },
    {
        "code": "1010",
        "name_en": "Cash in Hand",
        "name_bn": "নগদ টাকা (ক্যাশিয়ার ড্রয়ার)",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.CASH,
        "is_group": False,
        "parent": "1000",
    },
    {
        "code": "1020",
        "name_en": "Bank Accounts",
        "name_bn": "ব্যাংক হিসাব",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.BANK,
        "is_group": True,
        "parent": "1000",
    },
    {
        "code": "1021",
        "name_en": "Sonali Bank PLC (Current A/C)",
        "name_bn": "সোনালী ব্যাংক পিএলসি",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.BANK,
        "is_group": False,
        "parent": "1020",
        "bank": "Sonali Bank PLC",
    },
    {
        "code": "1022",
        "name_en": "Dutch-Bangla Bank PLC",
        "name_bn": "ডাচ-বাংলা ব্যাংক পিএলসি",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.BANK,
        "is_group": False,
        "parent": "1020",
        "bank": "Dutch-Bangla Bank PLC",
    },
    {
        "code": "1030",
        "name_en": "MFS & Online Gateways",
        "name_bn": "অনলাইন পেমেন্ট গেটওয়ে",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.MFS,
        "is_group": True,
        "parent": "1000",
    },
    {
        "code": "1031",
        "name_en": "bKash Merchant Account",
        "name_bn": "বিকাশ মার্চেন্ট হিসাব",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.MFS,
        "is_group": False,
        "parent": "1030",
    },
    {
        "code": "1032",
        "name_en": "Nagad Merchant Account",
        "name_bn": "নগদ মার্চেন্ট হিসাব",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.MFS,
        "is_group": False,
        "parent": "1030",
    },
    {
        "code": "1033",
        "name_en": "SSLCommerz Settlement Account",
        "name_bn": "এসএসএলকমার্জ হিসাব",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.MFS,
        "is_group": False,
        "parent": "1030",
    },
    {
        "code": "1040",
        "name_en": "Accounts Receivable",
        "name_bn": "প্রাপ্য হিসাব (বকেয়া ফি)",
        "type": AccountType.ASSET,
        "subtype": AccountSubtype.RECEIVABLE,
        "is_group": False,
        "parent": "1000",
    },
    # 2000 - LIABILITIES
    {
        "code": "2000",
        "name_en": "Liabilities",
        "name_bn": "দায়",
        "type": AccountType.LIABILITY,
        "is_group": True,
        "parent": None,
    },
    {
        "code": "2010",
        "name_en": "Student Advance Balances",
        "name_bn": "শিক্ষার্থী অগ্রিম জমা",
        "type": AccountType.LIABILITY,
        "subtype": AccountSubtype.CURRENT_LIABILITY,
        "is_group": False,
        "parent": "2000",
    },
    {
        "code": "2020",
        "name_en": "Caution Money & Security Deposits",
        "name_bn": "জামানত ও সিকিউরিটি ডিপোজিট",
        "type": AccountType.LIABILITY,
        "subtype": AccountSubtype.CURRENT_LIABILITY,
        "is_group": False,
        "parent": "2000",
    },
    {
        "code": "2030",
        "name_en": "Accounts Payable",
        "name_bn": "প্রদেয় হিসাব",
        "type": AccountType.LIABILITY,
        "subtype": AccountSubtype.PAYABLE,
        "is_group": False,
        "parent": "2000",
    },
    # 3000 - EQUITY / FUND BALANCES
    {
        "code": "3000",
        "name_en": "Equity & Fund Balances",
        "name_bn": "মূলধন ও তহবিল",
        "type": AccountType.EQUITY,
        "is_group": True,
        "parent": None,
    },
    {
        "code": "3010",
        "name_en": "General Operating Fund",
        "name_bn": "সাধারণ অপারেটিং তহবিল",
        "type": AccountType.EQUITY,
        "subtype": AccountSubtype.GENERAL_FUND,
        "is_group": False,
        "parent": "3000",
    },
    {
        "code": "3020",
        "name_en": "Development & Building Fund",
        "name_bn": "উন্নয়ন ও ভবন নির্মাণ তহবিল",
        "type": AccountType.EQUITY,
        "subtype": AccountSubtype.DEVELOPMENT_FUND,
        "is_group": False,
        "parent": "3000",
    },
    {
        "code": "3030",
        "name_en": "Poor & Scholarship Fund",
        "name_bn": "দরিদ্র ও বৃত্তি তহবিল",
        "type": AccountType.EQUITY,
        "subtype": AccountSubtype.SCHOLARSHIP_FUND,
        "is_group": False,
        "parent": "3000",
    },
    # 4000 - INCOME / REVENUE
    {
        "code": "4000",
        "name_en": "Income & Revenue",
        "name_bn": "আয় ও রাজস্ব",
        "type": AccountType.INCOME,
        "is_group": True,
        "parent": None,
    },
    {
        "code": "4010",
        "name_en": "Tuition Fees",
        "name_bn": "মাসিক বেতন / টিউশন ফি",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.TUITION_FEE,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4020",
        "name_en": "Admission Fees",
        "name_bn": "ভর্তি ফি",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.ADMISSION_FEE,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4030",
        "name_en": "Examination Fees",
        "name_bn": "পরীক্ষার ফি",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.EXAM_FEE,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4040",
        "name_en": "Session Charges",
        "name_bn": "সেশন চার্জ",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.OTHER_INCOME,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4050",
        "name_en": "Laboratory & Computer Fees",
        "name_bn": "ল্যাবরেটরি ও আইসিটি ফি",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.OTHER_INCOME,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4060",
        "name_en": "Transport Fees",
        "name_bn": "পরিবহন ফি",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.OTHER_INCOME,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4070",
        "name_en": "Govt MPO Subsidies & Grants",
        "name_bn": "সরকারি এমপিও অনুদান",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.OTHER_INCOME,
        "is_group": False,
        "parent": "4000",
    },
    {
        "code": "4080",
        "name_en": "Bank Interest & Misc Income",
        "name_bn": "ব্যাংক সুদ ও অন্যান্য আয়",
        "type": AccountType.INCOME,
        "subtype": AccountSubtype.OTHER_INCOME,
        "is_group": False,
        "parent": "4000",
    },
    # 5000 - EXPENSES
    {
        "code": "5000",
        "name_en": "Expenses",
        "name_bn": "ব্যয়",
        "type": AccountType.EXPENSE,
        "is_group": True,
        "parent": None,
    },
    {
        "code": "5010",
        "name_en": "Staff Salaries & Allowances",
        "name_bn": "শিক্ষক-কর্মচারী বেতন ও ভাতা",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.SALARY_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5020",
        "name_en": "Utilities (Electricity, Water, Internet)",
        "name_bn": "ইউটিলিটি বিল (বিদ্যুৎ, পানি, ইন্টারনেট)",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.UTILITY_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5030",
        "name_en": "Exam & Evaluation Expenses",
        "name_bn": "পরীক্ষা ও মূল্যায়ন খরচ",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.EXAM_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5040",
        "name_en": "Repairs & Maintenance",
        "name_bn": "মেরামত ও রক্ষণাবেক্ষণ",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.MAINTENANCE_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5050",
        "name_en": "Printing & Office Stationery",
        "name_bn": "মুদ্রণ ও স্টেশনারি",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.ADMIN_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5060",
        "name_en": "Sports & Cultural Activities",
        "name_bn": "ক্রীড়া ও সাংস্কৃতিক কার্যক্রম",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.OTHER_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
    {
        "code": "5070",
        "name_en": "Bank Charges & Gateway Fees",
        "name_bn": "ব্যাংক চার্জ ও গেটওয়ে ফি",
        "type": AccountType.EXPENSE,
        "subtype": AccountSubtype.OTHER_EXPENSE,
        "is_group": False,
        "parent": "5000",
    },
]


def seed_default_chart_of_accounts(institution: "Institution") -> list[Account]:
    """Seed the standard hierarchical Chart of Accounts for a school institution."""
    created_accounts: list[Account] = []
    account_map: dict[str, Account] = {}

    with transaction.atomic():
        for item in DEFAULT_COA:
            parent_acc = account_map.get(str(item["parent"])) if item.get("parent") else None
            acc, created = Account.objects.get_or_create(
                institution=institution,
                account_code=item["code"],
                defaults={
                    "name_en": item["name_en"],
                    "name_bn": item["name_bn"],
                    "account_type": item["type"],
                    "subtype": item.get("subtype", ""),
                    "is_group": item["is_group"],
                    "is_system": True,
                    "parent": parent_acc,
                    "bank_name": item.get("bank", ""),
                },
            )
            account_map[str(item["code"])] = acc
            created_accounts.append(acc)

    logger.info("Seeded %d default accounts for %s", len(created_accounts), institution)
    return created_accounts


def recalculate_account_balances(institution: "Institution") -> None:
    """Recalculate running balances of all accounts from posted voucher line items."""
    accounts = Account.objects.filter(institution=institution, is_group=False)
    with transaction.atomic():
        for acc in accounts:
            debits_sum = acc.journal_items.filter(entry__status=VoucherStatus.POSTED).aggregate(
                total=Sum("debit")
            )["total"] or Decimal("0.00")
            credits_sum = acc.journal_items.filter(entry__status=VoucherStatus.POSTED).aggregate(
                total=Sum("credit")
            )["total"] or Decimal("0.00")

            # Standard accounting equation balance:
            # Assets & Expenses increase with Debits: Balance = Opening + Debit - Credit
            # Liabilities, Equity & Income increase with Credits: Balance = Opening + Credit - Debit
            if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                acc.current_balance = acc.opening_balance + debits_sum - credits_sum
            else:
                acc.current_balance = acc.opening_balance + credits_sum - debits_sum

            acc.save(update_fields=["current_balance"])
