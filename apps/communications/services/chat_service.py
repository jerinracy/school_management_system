"""Teacher-Guardian chat thread and message service."""

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.communications.models import ChatMessage, ChatThread

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.guardians.models import Guardian
    from apps.institutions.models import Institution
    from apps.staff.models import Staff
    from apps.students.models import Student

logger = logging.getLogger(__name__)


def get_or_create_chat_thread(
    institution: "Institution",
    teacher: "Staff",
    guardian: "Guardian",
    student: "Student | None" = None,
    subject: str = "",
) -> tuple[ChatThread, bool]:
    """Retrieve or initialize a chat thread between a teacher and a guardian."""
    thread, created = ChatThread.objects.get_or_create(
        institution=institution,
        teacher=teacher,
        guardian=guardian,
        student=student,
        defaults={"subject": subject},
    )
    return thread, created


def send_chat_message(
    thread: ChatThread,
    sender: "User",
    content: str,
) -> ChatMessage:
    """Send a message inside an active chat thread and update thread activity timestamp."""
    if thread.is_closed:
        raise ValueError("Cannot send message to a closed thread.")

    msg = ChatMessage.objects.create(
        institution=thread.institution,
        thread=thread,
        sender=sender,
        content=content.strip(),
    )

    thread.last_message_at = timezone.now()
    thread.save(update_fields=["last_message_at"])
    return msg
