from app.config import COMPANY_NAME


def build_dues_table_html(dues: list) -> str:
    """Build an HTML table of overdue amounts by branch."""
    rows = ""
    total = 0
    for d in dues:
        amount = float(d["amount"])
        total += amount
        rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{d.get('branch_name', 'N/A')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: right;">₹{amount:,.2f}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; text-align: center;">{d.get('days_overdue', 0)} days</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{d.get('due_date', 'N/A')}</td>
        </tr>"""

    return f"""
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
        <thead>
            <tr style="background-color: #f8f9fa;">
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Branch</th>
                <th style="padding: 10px 12px; text-align: right; border-bottom: 2px solid #dee2e6;">Amount</th>
                <th style="padding: 10px 12px; text-align: center; border-bottom: 2px solid #dee2e6;">Overdue</th>
                <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Due Date</th>
            </tr>
        </thead>
        <tbody>
            {rows}
            <tr style="font-weight: bold; background-color: #f8f9fa;">
                <td style="padding: 10px 12px;">Total</td>
                <td style="padding: 10px 12px; text-align: right;">₹{total:,.2f}</td>
                <td colspan="2"></td>
            </tr>
        </tbody>
    </table>
    """


def build_email_html(vendor_name: str, body: str, dues_table: str) -> str:
    """Wrap email body in a professional HTML template."""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 700px; margin: 0 auto;">
        <div style="padding: 20px;">
            <p>Dear {vendor_name},</p>
            <p>{body}</p>
            <div style="margin: 20px 0;">
                {dues_table}
            </div>
            <p>We request you to kindly arrange the payment at the earliest.</p>
            <p style="margin-top: 30px;">
                Regards,<br/>
                <strong>{COMPANY_NAME}</strong>
            </p>
        </div>
    </body>
    </html>
    """
