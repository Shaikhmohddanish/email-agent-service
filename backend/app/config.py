import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=True)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Company Info
COMPANY_NAME = os.getenv("COMPANY_NAME", "Hirani Group")
CC_EMAILS = os.getenv("CC_EMAILS", "admin@hiranigroup.com").split(",")

# Gmail
GMAIL_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
GMAIL_TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'token.json')
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
]

# Scheduler
SCHEDULER_INTERVAL_HOURS = 24
OVERDUE_THRESHOLD_DAYS = 30
FOLLOWUP_WAIT_HOURS = 48

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
