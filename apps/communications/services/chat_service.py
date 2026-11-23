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
    guardian: "Guardian | None" = None,
    student: "Student | None" = None,
    subject: str = "",
    thread_type: str = ChatThread.ThreadType.TEACHER_GUARDIAN,
) -> tuple[ChatThread, bool]:
    """Retrieve or initialize a chat thread between a teacher and a guardian or student."""
    if not guardian and student:
        thread_type = ChatThread.ThreadType.TEACHER_STUDENT

    thread, created = ChatThread.objects.get_or_create(
        institution=institution,
        teacher=teacher,
        guardian=guardian,
        student=student,
        defaults={"subject": subject, "thread_type": thread_type},
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

    # Resolve recipient user for real-time notification / webhook
    recipient_user = None
    teacher_user_id = getattr(getattr(thread, "teacher", None), "user_id", None)

    if sender.id == teacher_user_id:
        if thread.thread_type == ChatThread.ThreadType.TEACHER_STUDENT or (
            thread.student and not thread.guardian
        ):
            recipient_user = getattr(thread.student, "user", None)
            if not recipient_user and thread.student and thread.student.phone:
                from apps.accounts.models import User

                recipient_user = User.objects.filter(
                    phone=thread.student.phone, institution=thread.institution
                ).first()
        elif thread.guardian:
            recipient_user = getattr(thread.guardian, "user", None)
            if not recipient_user and thread.guardian.phone:
                from apps.accounts.models import User

                recipient_user = User.objects.filter(
                    phone=thread.guardian.phone, institution=thread.institution
                ).first()
    else:
        recipient_user = getattr(thread.teacher, "user", None)

    if recipient_user:
        try:
            from apps.communications.services.push_service import send_push_notification

            sender_name = (
                getattr(sender, "full_name", "")
                or getattr(sender, "username", "")
                or getattr(sender, "phone", "Teacher")
            )
            send_push_notification(
                institution=thread.institution,
                user=recipient_user,
                title=str(sender_name),
                body=content.strip()[:120],
                data={
                    "type": "chat",
                    "thread_id": str(thread.id),
                    "sender_id": str(sender.id),
                    "thread_type": str(thread.thread_type),
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to dispatch push notification for chat message %s: %s", msg.id, exc
            )

    return msg
