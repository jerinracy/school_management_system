"""Excel (.xlsx) bulk catalog and copy import service using openpyxl."""

import io
from decimal import Decimal, InvalidOperation
from typing import Any

import openpyxl
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.library.models import Book, BookCopy


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _parse_int(val: Any) -> int | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _parse_decimal(val: Any) -> Decimal:
    if val is None or str(val).strip() == "":
        return Decimal("0.00")
    try:
        dec = Decimal(str(val).strip())
        return max(Decimal("0.00"), dec)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _import_single_catalog_row(
    *,
    institution: Any,
    branch: Any,
    row: tuple[Any, ...],
    idx: dict[str, int],
) -> tuple[bool, bool]:
    """Import one Excel row inside a savepoint, returning (book_created, copy_created)."""

    def col(key: str) -> Any:
        pos = idx.get(key)
        if pos is None or pos >= len(row):
            return None
        return row[pos]

    title = _clean_str(col("title"))
    authors = _clean_str(col("authors"))
    if not title or not authors:
        raise ValidationError("Both title and authors are required.")

    isbn = _clean_str(col("isbn"))
    accession_no = _clean_str(col("accession_no"))
    book_created = False
    copy_created = False

    with transaction.atomic():
        book = None
        if isbn:
            book = Book.objects.filter(institution=institution, isbn=isbn, is_deleted=False).first()
        if book is None:
            book = Book.objects.filter(
                institution=institution,
                title__iexact=title,
                authors__iexact=authors,
                is_deleted=False,
            ).first()
        if book is None:
            book = Book.objects.create(
                institution=institution,
                isbn=isbn,
                title=title,
                title_bn=_clean_str(col("title_bn")),
                authors=authors,
                category=_clean_str(col("category")),
                publisher=_clean_str(col("publisher")),
                edition=_clean_str(col("edition")),
                publication_year=_parse_int(col("publication_year")),
                language=_clean_str(col("language")) or "en",
            )
            book_created = True

        if accession_no:
            if BookCopy.objects.filter(
                institution=institution, accession_no=accession_no, is_deleted=False
            ).exists():
                raise ValidationError(f"Duplicate accession_no '{accession_no}'.")
            BookCopy.objects.create(
                institution=institution,
                book=book,
                branch=branch,
                accession_no=accession_no,
                barcode=_clean_str(col("barcode")),
                rfid_tag=_clean_str(col("rfid_tag")),
                shelf_location=_clean_str(col("shelf_location")),
                price=_parse_decimal(col("price")),
            )
            copy_created = True

    return book_created, copy_created


def import_books_from_xlsx(
    *,
    institution: Any,
    file_bytes: bytes,
    branch: Any = None,
) -> dict[str, Any]:
    """Import Book and optional BookCopy records from an Excel (.xlsx) workbook."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise ValidationError(f"Invalid Excel (.xlsx) file: {exc}") from exc

    sheet = wb.active
    if sheet is None:
        raise ValidationError("Workbook has no active sheet.")

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValidationError("Excel sheet is empty.")

    headers = [_clean_str(h).lower() for h in rows[0]]
    if "title" not in headers or "authors" not in headers:
        raise ValidationError("Excel header must include 'title' and 'authors' columns.")

    idx = {name: i for i, name in enumerate(headers) if name}
    created_books = 0
    created_copies = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for row_num, row in enumerate(rows[1:], start=2):
        if not any(_clean_str(c) for c in row):
            continue
        try:
            book_created, copy_created = _import_single_catalog_row(
                institution=institution,
                branch=branch,
                row=row,
                idx=idx,
            )
            created_books += int(book_created)
            created_copies += int(copy_created)
        except Exception as exc:
            errors.append({"row": row_num, "error": str(exc)})
            skipped += 1

    return {
        "created_books": created_books,
        "created_copies": created_copies,
        "skipped": skipped,
        "row_errors": errors,
    }
