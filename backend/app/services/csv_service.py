import io
import logging
from datetime import date, datetime
import pandas as pd
import cloudinary
import cloudinary.uploader
from app.db.repository import Repository
from app.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = ['vendor_name', 'vendor_email', 'company_name', 'branch_name', 'amount', 'due_date']

# Configure Cloudinary
if CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )


def upload_to_cloudinary(file_content: bytes, filename: str) -> str:
    """Upload CSV file to Cloudinary and return the URL."""
    if not CLOUDINARY_CLOUD_NAME:
        logger.warning("Cloudinary not configured, skipping file upload")
        return ""

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        public_id = f"email_agent/csv/{timestamp}_{filename.replace('.csv', '')}"

        result = cloudinary.uploader.upload(
            file_content,
            resource_type="raw",
            public_id=public_id,
            folder="email_agent/csv",
        )
        url = result.get("secure_url", "")
        logger.info(f"CSV archived to Cloudinary: {url}")
        return url
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return ""


def process_csv(file_content: bytes, user_id: str, repo: Repository, filename: str = "upload.csv") -> dict:
    """Parse CSV or Excel file, archive to Cloudinary, and upsert vendors + dues."""

    # Step 1: Archive CSV to Cloudinary
    cloudinary_url = upload_to_cloudinary(file_content, filename)

    # Step 2: Parse file (CSV or Excel)
    try:
        lower_name = filename.lower()
        if lower_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            df = pd.read_csv(io.BytesIO(file_content))
    except Exception as e:
        logger.error(f"Failed to parse file: {e}")
        return {"success": False, "error": f"Failed to parse file: {e}"}

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # Validate columns
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        return {"success": False, "error": f"Missing columns: {', '.join(missing)}"}

    vendors_processed = 0
    dues_processed = 0
    errors = []

    for _, row in df.iterrows():
        try:
            # Upsert vendor
            vendor_data = {
                "user_id": user_id,
                "name": str(row['vendor_name']).strip(),
                "email": str(row['vendor_email']).strip().lower(),
                "company_name": str(row.get('company_name', '')).strip(),
                "phone": str(row.get('phone', '')).strip() if 'phone' in row else None,
            }
            vendor_result = repo.upsert_vendor(vendor_data)

            if vendor_result.data:
                vendor_id = vendor_result.data[0]['id']
                vendors_processed += 1

                # Calculate days overdue
                try:
                    due_dt = pd.to_datetime(row['due_date']).date()
                    days_overdue = max(0, (date.today() - due_dt).days)
                except:
                    due_dt = None
                    days_overdue = 0

                # Upsert due
                due_data = {
                    "vendor_id": vendor_id,
                    "branch_name": str(row['branch_name']).strip(),
                    "amount": float(row['amount']),
                    "due_date": due_dt.isoformat() if due_dt else None,
                    "days_overdue": days_overdue,
                    "status": "PENDING",
                }
                repo.upsert_due(due_data)
                dues_processed += 1

                # Log activity
                repo.log_activity(vendor_id, "CSV_IMPORT", f"Imported due: {row['branch_name']} - ₹{float(row['amount']):,.2f}")

        except Exception as e:
            errors.append(f"Row {_ + 1}: {str(e)}")
            logger.error(f"Error processing CSV row: {e}")

    result = {
        "success": True,
        "vendors_processed": vendors_processed,
        "dues_processed": dues_processed,
        "cloudinary_url": cloudinary_url,
    }
    if errors:
        result["errors"] = errors

    logger.info(f"CSV processed: {vendors_processed} vendors, {dues_processed} dues. Archived: {cloudinary_url}")
    return result
