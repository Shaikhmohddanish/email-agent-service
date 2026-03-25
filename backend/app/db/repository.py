from datetime import datetime
from typing import Optional
from supabase import Client


class Repository:
    """Data access layer for all database operations."""

    def __init__(self, client: Client):
        self.client = client

    # ── Vendors ──────────────────────────────────────────────

    def get_vendors(self):
        return self.client.table("vendors").select("*, dues(*)").order("created_at", desc=True).execute()

    def get_vendor(self, vendor_id: str):
        return self.client.table("vendors").select("*, dues(*), email_threads(*, messages(*))").eq("id", vendor_id).single().execute()

    def upsert_vendor(self, data: dict):
        return self.client.table("vendors").upsert(data, on_conflict="user_id,email").execute()

    def delete_vendor(self, vendor_id: str):
        return self.client.table("vendors").delete().eq("id", vendor_id).execute()

    # ── Dues ─────────────────────────────────────────────────

    def get_dues_by_vendor(self, vendor_id: str):
        return self.client.table("dues").select("*").eq("vendor_id", vendor_id).order("due_date").execute()

    def upsert_due(self, data: dict):
        return self.client.table("dues").upsert(data, on_conflict="vendor_id,branch_name").execute()

    def update_due(self, due_id: str, data: dict):
        return self.client.table("dues").update(data).eq("id", due_id).execute()

    def get_overdue_dues(self, threshold_days: int = 30):
        """Get all PENDING dues that are overdue beyond threshold, with vendor info."""
        return self.client.table("dues").select("*, vendors(*)").eq("status", "PENDING").gte("days_overdue", threshold_days).execute()

    # ── Email Threads ────────────────────────────────────────

    def get_threads_by_vendor(self, vendor_id: str):
        return self.client.table("email_threads").select("*, messages(*)").eq("vendor_id", vendor_id).order("created_at", desc=True).execute()

    def get_threads_by_due(self, due_id: str):
        """Get threads linked to a specific due/project."""
        return self.client.table("email_threads").select("*, messages(*)").eq("due_id", due_id).execute()

    def get_thread(self, thread_id: str):
        return self.client.table("email_threads").select("*, messages(*), vendors(*)").eq("id", thread_id).single().execute()

    def get_threads_by_status(self, status: str):
        return self.client.table("email_threads").select("*, messages(*), vendors(*)").eq("status", status).execute()

    def get_waiting_threads(self):
        return self.client.table("email_threads").select("*, messages(*), vendors(*)").eq("status", "WAITING").execute()

    def create_thread(self, data: dict):
        return self.client.table("email_threads").insert(data).execute()

    def update_thread(self, thread_id: str, data: dict):
        return self.client.table("email_threads").update(data).eq("id", thread_id).execute()

    # ── Messages ─────────────────────────────────────────────

    def get_messages_by_thread(self, thread_id: str):
        return self.client.table("messages").select("*").eq("thread_id", thread_id).order("sent_at").execute()

    def create_message(self, data: dict):
        return self.client.table("messages").insert(data).execute()

    # ── Activities ───────────────────────────────────────────

    def get_activities(self, limit: int = 50):
        return self.client.table("activities").select("*, vendors(name, company_name)").order("created_at", desc=True).limit(limit).execute()

    def get_activities_by_vendor(self, vendor_id: str):
        return self.client.table("activities").select("*").eq("vendor_id", vendor_id).order("created_at", desc=True).execute()

    def log_activity(self, vendor_id: str, action: str, details: str = ""):
        return self.client.table("activities").insert({
            "vendor_id": vendor_id,
            "action": action,
            "details": details,
        }).execute()

    # ── Dashboard Stats ──────────────────────────────────────

    def get_dashboard_stats(self):
        vendors = self.client.table("vendors").select("id", count="exact").execute()
        dues = self.client.table("dues").select("amount, status").execute()
        threads = self.client.table("email_threads").select("status").execute()

        total_due = sum(float(d["amount"]) for d in dues.data) if dues.data else 0
        pending_due = sum(float(d["amount"]) for d in dues.data if d["status"] == "PENDING") if dues.data else 0

        thread_counts = {}
        if threads.data:
            for t in threads.data:
                s = t["status"]
                thread_counts[s] = thread_counts.get(s, 0) + 1

        return {
            "total_vendors": vendors.count or 0,
            "total_due": total_due,
            "pending_due": pending_due,
            "thread_counts": thread_counts,
        }
