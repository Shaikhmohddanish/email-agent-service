# Email Agent Service

AI-powered vendor due tracking and email automation system. Automatically sends payment reminder emails to vendors, tracks their responses, classifies replies using AI, and manages follow-ups.

## Tech Stack

- **Backend**: Python FastAPI + APScheduler
- **Frontend**: React (Vite)
- **Database & Auth**: Supabase (PostgreSQL + Auth)
- **AI**: OpenAI GPT-4o-mini (email generation, reply classification, date extraction)
- **Email**: Gmail API (OAuth2)
- **File Storage**: Cloudinary (CSV/Excel archival)

## Features

- CSV and Excel file upload for vendor dues import
- Per-branch/project email reminders with AI-generated content
- Automated reply classification (PAID, WILL_PAY, DISPUTE, QUESTION)
- Promised payment date tracking per project
- Follow-up escalation (gentle → firm → urgent)
- Activity logging and dashboard stats
- Single admin user authentication via Supabase

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Supabase project
- Gmail API credentials (`credentials.json`)
- OpenAI API key

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
OPENAI_API_KEY=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
COMPANY_NAME=
CC_EMAILS=
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Gmail OAuth

On first run, a browser window will open for Gmail OAuth authorization. This generates `backend/token.json` automatically.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # REST API endpoints
│   │   ├── auth/middleware.py     # JWT verification via Supabase
│   │   ├── db/
│   │   │   ├── repository.py     # Database CRUD operations
│   │   │   └── supabase_client.py
│   │   ├── services/
│   │   │   ├── ai_service.py     # OpenAI integration
│   │   │   ├── csv_service.py    # CSV/Excel parsing + Cloudinary
│   │   │   ├── gmail_service.py  # Gmail API integration
│   │   │   ├── scheduler_service.py  # Daily automation job
│   │   │   ├── thread_service.py
│   │   │   └── followup_service.py
│   │   ├── utils/
│   │   │   ├── email_formatter.py
│   │   │   └── logger.py
│   │   ├── config.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Layout.jsx
│   │   ├── context/AuthContext.jsx
│   │   ├── lib/
│   │   │   ├── api.js
│   │   │   └── supabase.js
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CsvUpload.jsx
│   │   │   ├── VendorDetail.jsx
│   │   │   ├── Activities.jsx
│   │   │   └── Login.jsx
│   │   ├── App.jsx
│   │   └── index.css
│   └── package.json
├── sample_data.csv
└── .env
```

## License

Private — All rights reserved.
