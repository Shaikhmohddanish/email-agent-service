import logging
from app.db.repository import Repository

logger = logging.getLogger(__name__)


def build_thread_context(repo: Repository, thread_id: str, max_messages: int = 10) -> str:
    """Build a readable context string from thread messages for AI."""
    messages = repo.get_messages_by_thread(thread_id)

    if not messages.data:
        return ""

    recent = messages.data[-max_messages:]
    context_parts = []

    for msg in recent:
        sender_label = {
            "AI": "Us",
            "HUMAN": "Us (manual)",
            "VENDOR": "Vendor"
        }.get(msg["sender"], msg["sender"])

        context_parts.append(f"[{sender_label}]: {msg['content'][:500]}")

    return "\n\n".join(context_parts)
