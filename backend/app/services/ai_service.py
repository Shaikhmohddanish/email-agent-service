import logging
from datetime import datetime
from openai import OpenAI
from app.config import OPENAI_API_KEY, COMPANY_NAME

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_reminder_email(vendor_name: str, company_name: str, dues: list) -> str:
    """Generate a professional payment reminder email body using AI."""
    if not client:
        # Fallback if no OpenAI key
        return f"We would like to bring to your attention the outstanding payments for your account. Please find the details below and arrange payment at the earliest."

    dues_text = "\n".join([
        f"- {d['branch_name']}: ₹{float(d['amount']):,.2f} (overdue {d['days_overdue']} days, due {d['due_date']})"
        for d in dues
    ])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional accounts executive at {COMPANY_NAME}. Write polite but firm payment reminder emails. Be concise. Do not include greeting or closing — just the body paragraph(s). Use professional Indian business English."
                },
                {
                    "role": "user",
                    "content": f"Write a payment reminder email body for {vendor_name} ({company_name}). Their outstanding dues:\n{dues_text}"
                }
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI email generation failed: {e}")
        return f"We would like to bring to your attention the outstanding payments for your account. Please find the details below and arrange payment at the earliest."


def classify_reply(reply_text: str, thread_context: str = "") -> str:
    """Classify a vendor reply into categories."""
    if not client:
        return "NEEDS_HUMAN"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Classify the vendor's reply into exactly one category:
- PAID: Vendor confirms payment has been made
- WILL_PAY: Vendor promises to pay by a certain date
- DISPUTE: Vendor disputes the amount or claims
- QUESTION: Vendor asks a question about the invoice/amount
- NEEDS_HUMAN: Cannot classify or needs manual attention

Respond with ONLY the category name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Thread context:\n{thread_context}\n\nLatest reply:\n{reply_text}"
                }
            ],
            max_tokens=20,
            temperature=0,
        )
        classification = response.choices[0].message.content.strip().upper()
        if classification in ("PAID", "WILL_PAY", "DISPUTE", "QUESTION", "NEEDS_HUMAN"):
            return classification
        return "NEEDS_HUMAN"
    except Exception as e:
        logger.error(f"OpenAI classification failed: {e}")
        return "NEEDS_HUMAN"


def generate_reply(vendor_name: str, thread_context: str, classification: str) -> str:
    """Generate a contextual reply based on thread history and classification."""
    if not client:
        return ""

    prompts = {
        "PAID": "Thank them and confirm you'll verify the payment. Ask for transaction reference if not provided.",
        "WILL_PAY": "Acknowledge their commitment. Politely confirm the expected payment date.",
        "DISPUTE": "Acknowledge the dispute professionally. Offer to connect them with the accounts team.",
        "QUESTION": "Answer their question professionally based on the thread context.",
    }

    instruction = prompts.get(classification, "Respond professionally and suggest connecting with a human representative.")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional accounts executive at {COMPANY_NAME}. {instruction} Be concise. No greeting or closing."
                },
                {
                    "role": "user",
                    "content": f"Vendor: {vendor_name}\nThread so far:\n{thread_context}\n\nGenerate an appropriate reply."
                }
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI reply generation failed: {e}")
        return ""


def generate_followup(vendor_name: str, followup_count: int, thread_context: str) -> str:
    """Generate a follow-up email with escalating tone."""
    if not client:
        return "This is a follow-up regarding our previous communication about outstanding payments. We request your immediate attention."

    tone = "gentle reminder" if followup_count == 1 else "firm follow-up" if followup_count == 2 else "urgent escalation"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional accounts executive at {COMPANY_NAME}. Write a {tone} follow-up email. This is follow-up #{followup_count}. Be concise. No greeting or closing."
                },
                {
                    "role": "user",
                    "content": f"Vendor: {vendor_name}\nPrevious thread:\n{thread_context}\n\nWrite follow-up #{followup_count}."
                }
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI followup generation failed: {e}")
        return "This is a follow-up regarding our previous communication about outstanding payments. We request your immediate attention."


def extract_promised_date(reply_text: str) -> dict | None:
    """Extract a promised payment date from vendor's reply using AI.
    
    Returns dict like {"date": "2026-03-28", "note": "Vendor says will pay by March 28"} or None.
    """
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Extract the promised payment date from this vendor reply.
Respond in JSON format ONLY: {"date": "YYYY-MM-DD", "note": "brief summary"}
If no specific date is mentioned, respond with: null
Use the current year 2026 if no year is given. Today is """ + datetime.now().strftime("%Y-%m-%d") + "."
                },
                {
                    "role": "user",
                    "content": reply_text,
                }
            ],
            max_tokens=100,
            temperature=0,
        )
        result_text = response.choices[0].message.content.strip()
        if result_text.lower() == "null" or not result_text:
            return None

        import json
        # Strip markdown code fences if present
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        parsed = json.loads(result_text)
        if parsed and parsed.get("date"):
            return parsed
        return None
    except Exception as e:
        logger.error(f"OpenAI date extraction failed: {e}")
        return None
