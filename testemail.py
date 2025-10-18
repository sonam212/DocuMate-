# testemail.py
import os
from dotenv import load_dotenv
load_dotenv()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# --- Email Config ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")   # from environment
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # from environment

def send_reminder_email(to_email, username, doc_title, doc_filename, reminder_date, reminder_type, expiry_date):
    subject = f"Reminder: {doc_title} ({reminder_type})"
    body = f"""
    Hello {username},

    This is a test reminder for your document '{doc_title}' ({doc_filename}).

    Reminder date: {reminder_date}
    Expiry date: {expiry_date}

    Please confirm you can receive this test email.

    - DocuMate
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

# --- Run a test ---
if __name__ == "__main__":
    send_reminder_email(
        "sonamsthakur3@gmail.com",   # 👈 put your real email here
        "Test User",
        "Test Document",
        "test.pdf",
        date(2025, 9, 22),
        "30_days_before",
        date(2025, 9, 22)
    )
