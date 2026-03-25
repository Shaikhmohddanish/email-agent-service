import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.auth.middleware import get_current_user_id
from app.db.supabase_client import supabase_admin, supabase
from app.db.repository import Repository
from app.services.csv_service import process_csv
from app.services.gmail_service import GmailService
from app.services.ai_service import generate_reminder_email, generate_reply
from app.services.thread_service import build_thread_context
from app.services.scheduler_service import run_scheduler_job
from app.utils.email_formatter import build_dues_table_html, build_email_html
from app.config import COMPANY_NAME

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Lazy-init Gmail service
_gmail_service = None


def get_gmail():
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service


def get_repo():
    """Get repository with service role client (bypasses RLS for backend ops)."""
    return Repository(supabase_admin or supabase)


# ── Request Models ───────────────────────────────────────────

class ManualReplyRequest(BaseModel):
    content: str
    thread_id: str


class ManualEmailRequest(BaseModel):
    subject: Optional[str] = None
    custom_body: Optional[str] = None


# ── CSV Upload ───────────────────────────────────────────────

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    allowed_extensions = ('.csv', '.xlsx', '.xls')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only CSV and Excel (.xlsx, .xls) files are accepted")

    content = await file.read()
    repo = get_repo()
    result = process_csv(content, user_id, repo, filename=file.filename)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to process CSV"))

    return result


# ── Vendors ──────────────────────────────────────────────────

@router.get("/vendors")
async def list_vendors(user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    result = repo.get_vendors()
    return {"data": result.data}


@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str, user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    try:
        result = repo.get_vendor(vendor_id)
        return {"data": result.data}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Vendor not found")


# ── Manual Email Send ────────────────────────────────────────

@router.post("/send-email/{vendor_id}")
async def send_email(vendor_id: str, body: ManualEmailRequest = None, user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    gmail = get_gmail()

    try:
        vendor = repo.get_vendor(vendor_id)
    except:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor_data = vendor.data
    dues = vendor_data.get("dues", [])
    pending_dues = [d for d in dues if d.get("status") == "PENDING"]

    if not pending_dues:
        raise HTTPException(status_code=400, detail="No pending dues for this vendor")

    # Generate email
    if body and body.custom_body:
        email_body = body.custom_body
    else:
        email_body = generate_reminder_email(vendor_data["name"], vendor_data.get("company_name", ""), pending_dues)

    dues_table = build_dues_table_html(pending_dues)
    html = build_email_html(vendor_data["name"], email_body, dues_table)

    subject = body.subject if body and body.subject else f"Payment Reminder - {vendor_data.get('company_name', vendor_data['name'])} - {COMPANY_NAME}"

    # Send
    sent = gmail.send_email(to=vendor_data["email"], subject=subject, html_body=html)

    # Create thread
    thread = repo.create_thread({
        "vendor_id": vendor_id,
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
            "content": email_body,
            "gmail_message_id": sent.get("id", ""),
        })

    repo.log_activity(vendor_id, "MANUAL_EMAIL", f"Manual email sent to {vendor_data['email']}")

    return {"success": True, "thread_id": thread.data[0]["id"] if thread.data else None}


# ── Manual Reply ─────────────────────────────────────────────

@router.post("/send-reply/{thread_id}")
async def send_reply(thread_id: str, body: ManualReplyRequest, user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    gmail = get_gmail()

    try:
        thread = repo.get_thread(thread_id)
    except:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread_data = thread.data
    vendor = thread_data.get("vendors", {})

    html = build_email_html(vendor.get("name", ""), body.content, "")

    sent = gmail.send_email(
        to=vendor["email"],
        subject=f"Re: {thread_data.get('subject', '')}",
        html_body=html,
        thread_id=thread_data.get("gmail_thread_id"),
    )

    repo.create_message({
        "thread_id": thread_id,
        "sender": "HUMAN",
        "content": body.content,
        "gmail_message_id": sent.get("id", ""),
    })

    repo.update_thread(thread_id, {
        "status": "WAITING",
        "last_message_at": datetime.now(timezone.utc).isoformat(),
    })

    repo.log_activity(thread_data.get("vendor_id", ""), "MANUAL_REPLY", f"Manual reply sent")

    return {"success": True}


# ── Threads ──────────────────────────────────────────────────

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    try:
        result = repo.get_thread(thread_id)
        return {"data": result.data}
    except:
        raise HTTPException(status_code=404, detail="Thread not found")


# ── Activities ───────────────────────────────────────────────

@router.get("/activities")
async def list_activities(limit: int = 50, user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    result = repo.get_activities(limit=limit)
    return {"data": result.data}


# ── Dashboard Stats ──────────────────────────────────────────

@router.get("/dashboard/stats")
async def dashboard_stats(user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    stats = repo.get_dashboard_stats()
    return {"data": stats}


# ── Trigger Scheduler ────────────────────────────────────────

@router.post("/trigger-scheduler")
async def trigger_scheduler(user_id: str = Depends(get_current_user_id)):
    repo = get_repo()
    gmail = get_gmail()
    run_scheduler_job(repo, gmail)
    return {"success": True, "message": "Scheduler job completed"}
