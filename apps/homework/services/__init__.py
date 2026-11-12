"""Homework & Learning Management services."""

from apps.homework.services.curriculum_service import (
    get_subject_syllabus_summary,
    update_syllabus_topic_progress,
)
from apps.homework.services.homework_service import (
    attach_files_to_homework,
    close_homework,
    grade_submission,
    publish_homework,
    send_due_soon_reminders,
    submit_homework,
)
from apps.homework.services.quiz_service import (
    recalculate_quiz_total_marks,
    start_quiz_attempt,
    submit_quiz_attempt,
)
from apps.homework.services.storage_service import (
    build_attachment_file_response,
    generate_signed_download_token,
    get_signed_file_download_url,
    scan_uploaded_file,
    validate_and_scan_upload,
    validate_uploaded_file,
    verify_signed_download_token,
)

__all__ = [
    "attach_files_to_homework",
    "build_attachment_file_response",
    "close_homework",
    "generate_signed_download_token",
    "get_signed_file_download_url",
    "get_subject_syllabus_summary",
    "grade_submission",
    "publish_homework",
    "recalculate_quiz_total_marks",
    "scan_uploaded_file",
    "send_due_soon_reminders",
    "start_quiz_attempt",
    "submit_homework",
    "submit_quiz_attempt",
    "update_syllabus_topic_progress",
    "validate_and_scan_upload",
    "validate_uploaded_file",
    "verify_signed_download_token",
]
