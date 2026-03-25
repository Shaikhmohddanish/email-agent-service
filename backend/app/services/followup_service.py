import logging
from datetime import datetime, timedelta, timezone
from app.db.repository import Repository
from app.services.gmail_service import GmailService
from app.services.ai_service import generate_followup
from app.services.thread_service import build_thread_context
from app.utils.email_formatter import build_email_html
from app.config import FOLLOWUP_WAIT_HOURS

logger = logging.getLogger(__name__)


def check_and_send_followups(repo: Repository, gmail: GmailService):
    """Check WAITING threads and send follow-ups if no reply after threshold."""
    waiting = repo.get_waiting_threads()

    if not waiting.data:
        logger.info("No waiting threads to follow up on")
        return

    now = datetime.now(timezone.utc)
    threshold = timedelta(hours=FOLLOWUP_WAIT_HOURS)

    for thread in waiting.data:
        last_msg_at = thread.get("last_message_at")
        if not last_msg_at:
            continue

        last_msg_time = datetime.fromisoformat(last_msg_at.replace('Z', '+00:00'))
        if now - last_msg_time < threshold:
            continue

        # Time for a follow-up
        vendor = thread.get("vendors", {})
        if not vendor:
            continue

        followup_count = (thread.get("followup_count", 0) or 0) + 1
        context = build_thread_context(repo, thread["id"])

        # Generate follow-up
        body = generate_followup(vendor.get("name", ""), followup_count, context)
        html = build_email_html(vendor.get("name", ""), body, "")

        try:
            # Send via Gmail
            sent = gmail.send_email(
                to=vendor["email"],
                subject=f"Re: Payment Reminder - {vendor.get('company_name', '')}",
                html_body=html,
                thread_id=thread.get("gmail_thread_id"),
            )

            # Update thread
            repo.update_thread(thread["id"], {
                "followup_count": followup_count,
                "last_message_at": now.isoformat(),
                "status": "WAITING",
            })

            # Save message
            repo.create_message({
                "thread_id": thread["id"],
                "sender": "AI",
                "content": body,
                "gmail_message_id": sent.get("id", ""),
            })

            # Log activity
            repo.log_activity(
                thread.get("vendor_id", ""),
                "FOLLOWUP_SENT",
                f"Follow-up #{followup_count} sent to {vendor['email']}"
            )

            logger.info(f"Follow-up #{followup_count} sent to {vendor['email']}")

        except Exception as e:
            logger.error(f"Failed to send follow-up to {vendor.get('email')}: {e}")
