"""File upload validation, pluggable AV scan hook, and signed download URL helpers."""

import logging
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import FileResponse
from django.utils.module_loading import import_string

from apps.homework.models import AVScanStatus

logger = logging.getLogger(__name__)

SIGNER_SALT = "homework-file-download"
# Standard harmless EICAR test string used to verify antivirus/malware detection in CI without ClamAV.
EICAR_TEST_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def validate_uploaded_file(uploaded_file: Any) -> tuple[str, int, str]:
    """Validate uploaded filename, extension, and size limit; return (filename, size, content_type)."""
    raw_name = getattr(uploaded_file, "name", "") or ""
    safe_name = os.path.basename(raw_name).strip()
    if not safe_name:
        raise ValidationError("Uploaded file must have a valid filename.")

    ext = Path(safe_name).suffix.lower()
    allowed = getattr(
        settings,
        "HOMEWORK_ALLOWED_EXTENSIONS",
        [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".jpg", ".jpeg", ".png", ".zip"],
    )
    if ext not in {e.lower() for e in allowed}:
        raise ValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(allowed))}."
        )

    size_bytes = int(getattr(uploaded_file, "size", 0) or 0)
    if size_bytes <= 0:
        raise ValidationError("Uploaded file cannot be empty.")

    max_mb = int(getattr(settings, "HOMEWORK_MAX_FILE_SIZE_MB", 10))
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(f"File exceeds maximum allowed size of {max_mb} MB.")

    content_type = getattr(uploaded_file, "content_type", "") or "application/octet-stream"
    return safe_name, size_bytes, content_type


def scan_uploaded_file(uploaded_file: Any) -> str:
    """Run configurable antivirus hook (or built-in signature check) on an uploaded file."""
    hook_path = getattr(settings, "HOMEWORK_AV_SCANNER_CALLABLE", None)
    if hook_path:
        scanner = import_string(hook_path)
        result = str(scanner(uploaded_file))
        if result == AVScanStatus.INFECTED:
            raise ValidationError("File rejected by antivirus scanner.")
        return result

    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
    try:
        sample = uploaded_file.read(65536)
        if isinstance(sample, str):
            sample = sample.encode("utf-8", errors="ignore")
        if EICAR_TEST_SIGNATURE in sample:
            logger.warning("Malware signature detected in uploaded file; rejecting upload.")
            raise ValidationError("File rejected by antivirus scan: potential threat detected.")
    finally:
        if pos is not None and hasattr(uploaded_file, "seek"):
            uploaded_file.seek(pos)

    return AVScanStatus.CLEAN


def validate_and_scan_upload(uploaded_file: Any) -> tuple[str, int, str, str]:
    """Validate and virus-scan an uploaded file before storage persistence."""
    safe_name, size_bytes, content_type = validate_uploaded_file(uploaded_file)
    av_status = scan_uploaded_file(uploaded_file)
    return safe_name, size_bytes, content_type, av_status


def generate_signed_download_token(
    attachment_kind: str,
    attachment_id: str,
    institution_id: str,
) -> str:
    """Create a short-lived HMAC signed token authorizing attachment download."""
    signer = TimestampSigner(salt=SIGNER_SALT)
    return signer.sign(f"{attachment_kind}:{attachment_id}:{institution_id}")


def verify_signed_download_token(token: str, max_age: int | None = None) -> dict[str, str]:
    """Validate a signed download token and extract attachment kind, id, and institution_id."""
    ttl = (
        max_age
        if max_age is not None
        else int(getattr(settings, "HOMEWORK_SIGNED_URL_TTL_SECONDS", 900))
    )
    signer = TimestampSigner(salt=SIGNER_SALT)
    try:
        raw = signer.unsign(token, max_age=ttl)
    except SignatureExpired as exc:
        raise ValidationError("Download link has expired. Please request a fresh link.") from exc
    except BadSignature as exc:
        raise ValidationError("Invalid download link signature.") from exc

    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValidationError("Malformed download token.")
    return {"kind": parts[0], "id": parts[1], "institution_id": parts[2]}


def get_signed_file_download_url(
    file_field: Any,
    attachment_kind: str,
    attachment_id: str,
    institution_id: str,
    request: Any = None,
) -> str:
    """Return an S3 presigned URL if using S3 storage, else a signed API download URL."""
    storage = getattr(file_field, "storage", None)
    if storage is not None and (
        hasattr(storage, "bucket_name") or "s3" in storage.__class__.__name__.lower()
    ):
        return str(file_field.url)

    token = generate_signed_download_token(attachment_kind, str(attachment_id), str(institution_id))
    path = f"/api/v1/homework/download/?token={token}"
    if request is not None:
        return str(request.build_absolute_uri(path))
    return path


def build_attachment_file_response(
    file_field: Any,
    filename: str,
    content_type: str = "application/octet-stream",
) -> FileResponse:
    """Stream stored file safely with attachment headers and nosniff protection."""
    handle = file_field.open("rb")
    safe_filename = os.path.basename(filename or "download").replace('"', "")
    response = FileResponse(
        handle,
        content_type=content_type or "application/octet-stream",
        as_attachment=True,
        filename=safe_filename,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
