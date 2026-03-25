import logging
from datetime import datetime, timezone, date
from app.db.repository import Repository
from app.services.gmail_service import GmailService
from app.services.ai_service import generate_reminder_email, classify_reply, generate_reply, extract_promised_date
from app.services.thread_service import build_thread_context
from app.services.followup_service import check_and_send_followups
from app.utils.email_formatter import build_dues_table_html, build_email_html
from app.config import OVERDUE_THRESHOLD_DAYS, COMPANY_NAME

logger = logging.getLogger(__name__)


def run_scheduler_job(repo: Repository, gmail: GmailService):
    """Main scheduler job — runs every 24 hours."""
    logger.info("=" * 60)
    logger.info("SCHEDULER JOB STARTED")
    logger.info("=" * 60)

    try:
        # Step 1: Send initial emails per-branch to overdue dues without threads
        send_initial_emails(repo, gmail)

        # Step 2: Check for replies on WAITING threads
        check_replies(repo, gmail)

        # Step 3: Send follow-ups where needed
        check_and_send_followups(repo, gmail)

        logger.info("SCHEDULER JOB COMPLETED")

    except Exception as e:
        logger.error(f"Scheduler job failed: {e}")


def send_initial_emails(repo: Repository, gmail: GmailService):
    """Send per-branch emails to overdue dues not yet contacted."""
    overdue_result = repo.get_overdue_dues(OVERDUE_THRESHOLD_DAYS)
    if not overdue_result.data:
        logger.info("No overdue dues found")
        return

    for due in overdue_result.data:
        vendor = due.get("vendors", {})
        if not vendor or not vendor.get("email"):
            continue

        # Skip if vendor already promised to pay and the date is in the future
        if due.get("promised_date"):
            try:
                promised = date.fromisoformat(due["promised_date"])
                if promised >= date.today():
                    logger.info(f"Skipping {vendor['name']} - {due['branch_name']}: promised to pay by {promised}")
                    continue
            except (ValueError, TypeError):
                pass

        # Check if there's already an active thread for this specific due
        existing_threads = repo.get_threads_by_due(due["id"])
        active_threads = [t for t in (existing_threads.data or []) if t["status"] not in ("CLOSED",)]
        if active_threads:
            continue

        # Generate and send email for this specific branch/project
        try:
            single_due_list = [due]
            body = generate_reminder_email(vendor["name"], vendor.get("company_name", ""), single_due_list)
            dues_table = build_dues_table_html(single_due_list)
            html = build_email_html(vendor["name"], body, dues_table)

            subject = f"Payment Reminder - {due['branch_name']} - {vendor.get('company_name', vendor['name'])} - {COMPANY_NAME}"
            sent = gmail.send_email(to=vendor["email"], subject=subject, html_body=html)

            # Create thread record linked to this specific due
            thread = repo.create_thread({
                "vendor_id": vendor["id"],
                "due_id": due["id"],
                "gmail_thread_id": sent.get("threadId", ""),
                "subject": subject,
                "status": "WAITING",
                "last_message_at": datetime.now(timezone.utc).isoformat(),
            })

            # Save message
            if thread.data:
                repo.create_message({
                    "thread_id": thread.data[0]["id"],
                    "sender": "AI",
                    "content": body,
                    "gmail_message_id": sent.get("id", ""),
                })

            # Log
            repo.log_activity(vendor["id"], "EMAIL_SENT", f"Reminder sent for {due['branch_name']} to {vendor['email']}")
            logger.info(f"Email sent to {vendor['email']} for branch: {due['branch_name']}")

        except Exception as e:
            logger.error(f"Failed to send email to {vendor.get('email')} for {due.get('branch_name')}: {e}")
            repo.log_activity(vendor["id"], "EMAIL_FAILED", str(e))


def check_replies(repo: Repository, gmail: GmailService):
    """Check WAITING threads for new replies from vendors."""
    waiting = repo.get_waiting_threads()
    if not waiting.data:
        return

    for thread in waiting.data:
        gmail_thread_id = thread.get("gmail_thread_id")
        if not gmail_thread_id:
            continue

        # Get known message IDs
        messages = thread.get("messages", [])
        known_ids = [m["gmail_message_id"] for m in messages if m.get("gmail_message_id")]

        # Check for new messages
        new_messages = gmail.check_for_replies(gmail_thread_id, known_ids)

        for msg in new_messages:
            # Save vendor message
            repo.create_message({
                "thread_id": thread["id"],
                "sender": "VENDOR",
                "content": msg["body"][:5000],
                "gmail_message_id": msg["gmail_message_id"],
            })

            # Classify reply
            context = build_thread_context(repo, thread["id"])
            classification = classify_reply(msg["body"], context)

            # Determine new thread status
            if classification == "PAID":
                new_status = "CLOSED"
            elif classification == "WILL_PAY":
                new_status = "REPLIED"
            elif classification == "NEEDS_HUMAN":
                new_status = "NEEDS_HUMAN"
            else:
                new_status = "WAITING"

            repo.update_thread(thread["id"], {
                "status": new_status,
                "last_message_at": datetime.now(timezone.utc).isoformat(),
            })

            # Handle WILL_PAY: extract promised date and update the due
            if classification == "WILL_PAY":
                _handle_will_pay(repo, thread, msg["body"])

            # Handle PAID: mark the due as paid
            if classification == "PAID":
                _handle_paid(repo, thread)

            # Auto-reply ONLY to DISPUTE and QUESTION (not WILL_PAY or PAID)
            if classification in ("DISPUTE", "QUESTION"):
                vendor = thread.get("vendors", {})
                reply_body = generate_reply(vendor.get("name", ""), context, classification)
                if reply_body:
                    html = build_email_html(vendor.get("name", ""), reply_body, "")
                    try:
                        sent = gmail.send_email(
                            to=vendor["email"],
                            subject=f"Re: {thread.get('subject', '')}",
                            html_body=html,
                            thread_id=gmail_thread_id,
                        )
                        repo.create_message({
                            "thread_id": thread["id"],
                            "sender": "AI",
                            "content": reply_body,
                            "gmail_message_id": sent.get("id", ""),
                        })
                        repo.update_thread(thread["id"], {
                            "status": "WAITING",
                            "last_message_at": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception as e:
                        logger.error(f"Auto-reply failed: {e}")

            repo.log_activity(
                thread.get("vendor_id", ""),
                f"REPLY_{classification}",
                f"Vendor replied. Classification: {classification}"
            )
            logger.info(f"Reply processed for thread {thread['id']}: {classification}")


def _handle_will_pay(repo: Repository, thread: dict, reply_text: str):
    """Extract promised date from vendor reply and update the due record."""
    due_id = thread.get("due_id")
    if not due_id:
        logger.warning(f"Thread {thread['id']} has no due_id, cannot update promised date")
        return

    promised = extract_promised_date(reply_text)
    if promised:
        update_data = {
            "promised_date": promised["date"],
            "promised_note": promised.get("note", ""),
        }
        repo.update_due(due_id, update_data)
        logger.info(f"Updated due {due_id} with promised_date={promised['date']}")
    else:
        # Still mark it with a note even if no specific date extracted
        repo.update_due(due_id, {
            "promised_note": "Vendor indicated willingness to pay (no specific date extracted)"
        })


def _handle_paid(repo: Repository, thread: dict):
    """Mark the linked due as PAID when vendor confirms payment."""
    due_id = thread.get("due_id")
    if not due_id:
        return

    repo.update_due(due_id, {"status": "PAID"})
    logger.info(f"Marked due {due_id} as PAID")
