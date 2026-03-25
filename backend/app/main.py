import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils.logger import setup_logger
from app.api.routes import router
from app.db.supabase_client import supabase_admin, supabase
from app.db.repository import Repository
from app.services.gmail_service import GmailService
from app.services.scheduler_service import run_scheduler_job
from app.config import SCHEDULER_INTERVAL_HOURS

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def scheduled_job():
    """Wrapper for the scheduled job."""
    try:
        repo = Repository(supabase_admin or supabase)
        gmail = GmailService()
        run_scheduler_job(repo, gmail)
    except Exception as e:
        logger.error(f"Scheduled job error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Email Agent Backend...")
    scheduler.add_job(
        scheduled_job,
        'interval',
        hours=SCHEDULER_INTERVAL_HOURS,
        id='email_agent_job',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — runs every {SCHEDULER_INTERVAL_HOURS} hours")
    yield
    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Email Agent API",
    description="AI-Powered Vendor Due Tracking & Email Automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "email-agent"}
