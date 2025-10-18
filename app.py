import os
from datetime import datetime, date, timedelta
from flask import (
    Flask, request, render_template, redirect, url_for, flash,
    send_from_directory, session, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import calendar
import random

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# --- Email Libraries ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- APScheduler for automatic reminders ---
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# -----------------------
# Configuration from .env
# -----------------------
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Create Flask app instance
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

# File upload limits
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Logging
import logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Add this right after your app configuration (around line 40-50)
@app.context_processor
def inject_today():
    from datetime import date
    return {'today': date.today()}

@app.context_processor
def inject_user():
    is_logged_in = 'user_id' in session
    username = session.get('username') if is_logged_in else None
    return {'is_logged_in': is_logged_in, 'username': username}

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Upload folder setup
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------
# Database Connection Helper
# ------------------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "DocuMate@2025!"),
        database=os.getenv("DB_NAME", "documate"),
    )

# --- STATUS FUNCTION ---
def get_document_status(expiry_date):
    """
    Returns 'active', 'expiring', or 'expired' based on expiry_date and today's date
    """
    if not expiry_date:
        return 'active'  # Documents without expiry are treated as active

    if isinstance(expiry_date, datetime):
        expiry_date = expiry_date.date()

    today = date.today()
    days_left = (expiry_date - today).days

    if days_left < 0:
        return 'expired'
    elif days_left <= 7:
        return 'expiring'
    else:
        return 'active'

# ------------------------
# Reminder creation (avoid duplicates)
# ------------------------
def create_reminders_for_document(document_id, expiry_date, user_id):
    """
    Create reminders for a document based on user preferences.
    Will not insert duplicates for the same document_id + reminder_type.
    Now includes expired reminders for documents that have already passed expiry.
    """
    if not expiry_date:
        return

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM user_notification_preferences WHERE user_id = %s", (user_id,))
        prefs = cursor.fetchone()

        # If no prefs exist, use sensible defaults
        if not prefs:
            prefs_dict = {
                'notify_30_days': True,
                'notify_7_days': True,
                'notify_1_day': True,
                'notify_day_of': True
            }
        else:
            # Convert DB values (0/1) to bool
            prefs_dict = {
                'notify_30_days': bool(prefs.get('notify_30_days')),
                'notify_7_days': bool(prefs.get('notify_7_days')),
                'notify_1_day': bool(prefs.get('notify_1_day')),
                'notify_day_of': bool(prefs.get('notify_day_of'))
            }

        # Helper to insert if not exists
        def insert_if_missing(rem_type, rem_date):
            if rem_date is None:
                return
            cursor.execute("""
                SELECT id FROM reminders WHERE document_id = %s AND reminder_type = %s
            """, (document_id, rem_type))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute("""
                    INSERT INTO reminders (document_id, reminder_date, reminder_type, sent_flag)
                    VALUES (%s, %s, %s, 0)
                """, (document_id, rem_date, rem_type))

        today = date.today()

        # Create future reminders based on preferences
        if prefs_dict.get('notify_30_days'):
            insert_if_missing('30_days_before', expiry_date - timedelta(days=30))
        if prefs_dict.get('notify_7_days'):
            insert_if_missing('7_days_before', expiry_date - timedelta(days=7))
        if prefs_dict.get('notify_1_day'):
            insert_if_missing('1_day_before', expiry_date - timedelta(days=1))
        if prefs_dict.get('notify_day_of'):
            insert_if_missing('day_of', expiry_date)

        # Always create an "expired" reminder for documents that have already expired
        # This will be sent immediately when the document is uploaded (if expired) or when it becomes expired
        if expiry_date < today:
            insert_if_missing('expired', today)  # Send immediately for expired documents

        db.commit()
    except Exception as e:
        print(f"Error creating reminders: {e}")
        db.rollback()
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            db.close()
        except:
            pass

# ------------------------
# Fetch pending reminders
# ------------------------
def fetch_pending_reminders(as_of=None):
    if as_of is None:
        as_of = date.today()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.id AS reminder_id,
                   r.document_id,
                   r.reminder_date,
                   r.reminder_type,
                   r.sent_flag,
                   d.title,
                   d.filename,
                   d.file_path,
                   d.expiry_date,
                   u.id AS user_id,
                   u.username,
                   u.email
            FROM reminders r
            JOIN documents d ON r.document_id = d.id
            JOIN users u     ON d.user_id = u.id
            WHERE r.sent_flag = 0
              AND r.reminder_date <= %s
            ORDER BY r.reminder_date ASC
        """, (as_of,))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print("ERROR fetching reminders:", e)
        return []
    finally:
        try:
            cursor.close()
            db.close()
        except:
            pass

# ------------------------
# Generate OTP
# ------------------------
def generate_otp():
    return str(random.randint(100000, 999999))

# ------------------------
# Send OTP email
# ------------------------
def send_otp_email(email, otp, username):
    subject = "Your DocuMate Verification OTP"
    body_html = f"""
        <p>Hello {username},</p>
        <p>Thank you for registering with DocuMate!</p>
        <p>Your verification code is: <strong>{otp}</strong></p>
        <p>This code will expire in 10 minutes. Please enter it to complete your registration.</p>
        <p>If you did not request this, please ignore this email.</p>
        <p>Best regards,<br/>The DocuMate Team</p>
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        print(f"✅ OTP email sent to {email}")
        return True
    except Exception as e:
        print(f"❌ Error sending OTP email to {email}: {e}")
        return False

# ------------------------
# Send reminder email (HTML)
# ------------------------
def send_reminder_email(to_email, username, doc_title, doc_filename, reminder_date, reminder_type, expiry_date):
    # Normalize expiry_date to date
    if isinstance(expiry_date, str):
        try:
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        except ValueError:
            expiry_date = date.today()
    elif isinstance(expiry_date, datetime):
        expiry_date = expiry_date.date()

    today = date.today()
    days_until_expiry = (expiry_date - today).days

    # Build subject + HTML body based on reminder type
    if reminder_type == 'expired':
        days_expired = abs(days_until_expiry)
        subject = f"Document Expiration Notice: '{doc_title}' Has Expired"
        body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc3545;">Document Expiration Notice</h2>
                <p>Dear {username},</p>

                <p>We regret to inform you that your document <strong>"{doc_title}"</strong> has expired.</p>

                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">Document Details:</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Document:</strong> {doc_title}</li>
                        <li><strong>Filename:</strong> {doc_filename}</li>
                        <li><strong>Expiry Date:</strong> {expiry_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Days Since Expiry:</strong> {days_expired} day{'s' if days_expired != 1 else ''}</li>
                    </ul>
                </div>

                <p><strong>Immediate Action Required:</strong></p>
                <ul>
                    <li>Renew or update the document as soon as possible</li>
                    <li>Check if this affects any legal or official requirements</li>
                    <li>Update your records in DocuMate with the new expiry date</li>
                    <li>Contact relevant authorities or service providers</li>
                </ul>

                <p style="color: #721c24;"><strong>Please address this matter promptly to avoid any complications.</strong></p>

                <p>Best regards,<br/>
                <strong>The DocuMate Team</strong><br/>
                <em>Your Document Management Assistant</em></p>
            </div>
        """
    elif reminder_type == '30_days_before':
        subject = f"Document Expiration Notice: '{doc_title}' Expires in {days_until_expiry} Days"
        body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #17a2b8;">Document Expiration Reminder</h2>
                <p>Dear {username},</p>

                <p>This is a friendly reminder about your upcoming document expiration.</p>

                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0c5460;">Document Details:</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Document:</strong> {doc_title}</li>
                        <li><strong>Filename:</strong> {doc_filename}</li>
                        <li><strong>Expiry Date:</strong> {expiry_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Days Remaining:</strong> {days_until_expiry} days</li>
                    </ul>
                </div>

                <p>You have ample time to prepare. Suggested next steps:</p>
                <ul>
                    <li>Review the document for accuracy and completeness</li>
                    <li>Begin the renewal process if required</li>
                    <li>Add the expiration date to your calendar</li>
                    <li>Check if you need to gather any supporting documents</li>
                </ul>

                <p>Best regards,<br/>
                <strong>The DocuMate Team</strong><br/>
                <em>Your Document Management Assistant</em></p>
            </div>
        """
    elif reminder_type == '7_days_before':
        subject = f"⏰ Reminder: '{doc_title}' Expires in {days_until_expiry} Days"
        body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #ffc107;">Document Expiration Alert</h2>
                <p>Dear {username},</p>

                <p>Your document is approaching its expiration date.</p>

                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">Document Details:</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Document:</strong> {doc_title}</li>
                        <li><strong>Filename:</strong> {doc_filename}</li>
                        <li><strong>Expiry Date:</strong> {expiry_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Days Remaining:</strong> {days_until_expiry} days</li>
                    </ul>
                </div>

                <p>To avoid last-minute issues, consider taking these actions:</p>
                <ul>
                    <li>Renew or update the document</li>
                    <li>Download a copy for your records</li>
                    <li>Verify all information is current and accurate</li>
                    <li>Contact the issuing authority if needed</li>
                </ul>

                <p>Best regards,<br/>
                <strong>The DocuMate Team</strong><br/>
                <em>Your Document Management Assistant</em></p>
            </div>
        """
    elif reminder_type == '1_day_before':
        subject = f"🚨 Action Required: '{doc_title}' Expires Tomorrow"
        body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #fd7e14;">Urgent Document Expiration Notice</h2>
                <p>Dear {username},</p>

                <p><strong>Time is running out!</strong> Your document expires tomorrow.</p>

                <div style="background-color: #ffeaa7; border: 1px solid #fd7e14; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">Document Details:</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Document:</strong> {doc_title}</li>
                        <li><strong>Filename:</strong> {doc_filename}</li>
                        <li><strong>Expiry Date:</strong> {expiry_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Time Remaining:</strong> Tomorrow</li>
                    </ul>
                </div>

                <p><strong>Recommended immediate actions:</strong></p>
                <ul>
                    <li>Renew the document today if possible</li>
                    <li>Download a final copy for your records</li>
                    <li>Verify renewal requirements and deadlines</li>
                    <li>Contact service providers or authorities</li>
                </ul>

                <p style="color: #721c24;"><strong>Don't wait until the last moment!</strong></p>

                <p>Best regards,<br/>
                <strong>The DocuMate Team</strong><br/>
                <em>Your Document Management Assistant</em></p>
            </div>
        """
    else:  # day_of
        subject = f"🚨 FINAL REMINDER: '{doc_title}' Expires Today"
        body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc3545;">FINAL DOCUMENT EXPIRATION NOTICE</h2>
                <p>Dear {username},</p>

                <p><strong>URGENT: Your document expires TODAY!</strong></p>

                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">Document Details:</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Document:</strong> {doc_title}</li>
                        <li><strong>Filename:</strong> {doc_filename}</li>
                        <li><strong>Expiry Date:</strong> {expiry_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Status:</strong> Expires today</li>
                    </ul>
                </div>

                <p><strong>Act immediately to:</strong></p>
                <ul>
                    <li>Renew the document today (if possible)</li>
                    <li>Save a copy for your records</li>
                    <li>Contact relevant authorities or service providers</li>
                    <li>Update your DocuMate records with renewal information</li>
                </ul>

                <p style="color: #721c24; font-size: 16px;"><strong>This is your final reminder. Please take action now to avoid any complications.</strong></p>

                <p>Best regards,<br/>
                <strong>The DocuMate Team</strong><br/>
                <em>Your Document Management Assistant</em></p>
            </div>
        """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"✅ {reminder_type} email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending {reminder_type} email to {to_email}: {e}")
        return False

# ------------------------
# Scheduler job
# ------------------------
def check_and_send_reminders():
    print(f"⏰ [{datetime.now()}] Checking for pending reminders...")
    try:
        reminders = fetch_pending_reminders()
        if not reminders:
            print("✅ No pending reminders found")
            return

        for reminder in reminders:
            try:
                send_reminder_email(
                    reminder['email'],
                    reminder['username'],
                    reminder['title'],
                    reminder['filename'],
                    reminder['reminder_date'],
                    reminder['reminder_type'],
                    reminder['expiry_date']
                )

                db = get_db_connection()
                cursor = db.cursor()
                cursor.execute("UPDATE reminders SET sent_flag = 1 WHERE id = %s", (reminder['reminder_id'],))
                db.commit()
                cursor.close()
                db.close()
                print(f"✅ Sent {reminder['reminder_type']} reminder for '{reminder['title']}' to {reminder['email']}")
            except Exception as e:
                print(f"❌ Error processing reminder {reminder.get('reminder_id')}: {e}")
    except Exception as e:
        print(f"❌ Error in reminder scheduler: {e}")

# Schedule the job to run daily at 9 AM
scheduler.add_job(
    check_and_send_reminders,
    CronTrigger(hour=9, minute=0),
    id='daily_reminders',
    name='Send daily document expiration reminders',
    replace_existing=True
)
if app.debug:
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1, id='test_reminders', replace_existing=True)
    print("✅ Test reminders enabled (every 1 minute)")
print("✅ APScheduler initialized - reminders will run daily at 9:00 AM" + (" and every 30 minutes for testing" if app.debug else ""))

# ------------------------
# Routes
# ------------------------

# Serve Uploaded Files (ownership check)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if "user_id" not in session:
        abort(403)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM documents WHERE filename = %s AND user_id = %s", (filename, session["user_id"]))
        doc = cursor.fetchone()
    except Exception as e:
        print("Error checking file ownership:", e)
        doc = None
    finally:
        try:
            cursor.close()
            db.close()
        except:
            pass

    if not doc:
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Home Page
@app.route("/")
def home():
    username = None
    if "username" in session:
        username = session["username"]
    return render_template("home.html", username=username)

# Upload Page - FINAL FIXED VERSION (keeps your earlier fixes)
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        flash("You must be logged in to upload documents.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    member_id = session.get("active_member_id")

    if request.method == "POST" and "file" in request.files:
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        expiry_date_str = request.form.get("expiry_date") or None
        file = request.files.get("file")

        if not title or not file:
            flash("Title and file are required!", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("upload"))

        timestamp = int(datetime.now().timestamp())
        filename = f"{session['user_id']}_{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        expiry_date = None
        if expiry_date_str:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()

        if member_id is not None:
            cursor.execute("""
                INSERT INTO documents (user_id, member_id, title, description, filename, file_path, uploaded_on, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (session["user_id"], member_id, title, description, filename, file_path, expiry_date))
        else:
            cursor.execute("""
                INSERT INTO documents (user_id, title, description, filename, file_path, uploaded_on, expiry_date)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """, (session["user_id"], title, description, filename, file_path, expiry_date))

        db.commit()

        document_id = cursor.lastrowid

        if expiry_date:
            create_reminders_for_document(document_id, expiry_date, session["user_id"])

        flash("Document uploaded successfully!", "success")
        try:
            cursor.close()
            db.close()
        except:
            pass
        return redirect(url_for("upload"))

    query = request.args.get("q", "").strip()
    search_status = "default"

    if "clear" in request.args:
        query = ""

    if member_id is not None:
        if query:
            cursor.execute("""
                SELECT d.id, d.title, d.description, d.filename, d.uploaded_on, d.expiry_date, u.username
                FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE d.user_id = %s AND d.member_id = %s AND (d.title LIKE %s OR d.description LIKE %s)
                ORDER BY d.uploaded_on DESC
            """, (session["user_id"], member_id, f"%{query}%", f"%{query}%"))
        else:
            cursor.execute("""
                SELECT d.id, d.title, d.description, d.filename, d.uploaded_on, d.expiry_date, u.username
                FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE d.user_id = %s AND d.member_id = %s
                ORDER BY d.uploaded_on DESC
            """, (session["user_id"], member_id))
    else:
        if query:
            cursor.execute("""
                SELECT d.id, d.title, d.description, d.filename, d.uploaded_on, d.expiry_date, u.username
                FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE d.user_id = %s AND (d.title LIKE %s OR d.description LIKE %s)
                ORDER BY d.uploaded_on DESC
            """, (session["user_id"], f"%{query}%", f"%{query}%"))
        else:
            cursor.execute("""
                SELECT d.id, d.title, d.description, d.filename, d.uploaded_on, d.expiry_date, u.username
                FROM documents d
                JOIN users u ON d.user_id = u.id
                WHERE d.user_id = %s
                ORDER BY d.uploaded_on DESC
            """, (session["user_id"],))

    documents = cursor.fetchall()

    if not query:
        search_status = "default"
    else:
        statuses = [get_document_status(doc.get("expiry_date")) for doc in documents]
        if "expired" in statuses:
            search_status = "expired"
        elif "expiring" in statuses:
            search_status = "warning"
        elif "active" in statuses:
            search_status = "valid"

    try:
        cursor.close()
        db.close()
    except:
        pass

    return render_template("upload.html", documents=documents, query=query, search_status=search_status, get_document_status=get_document_status)
# Preview Route---------------
@app.route("/preview/<int:doc_id>")
def preview_document(doc_id):
    if "user_id" not in session:
        flash("You must be logged in to preview documents.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM documents WHERE id = %s AND user_id = %s", (doc_id, session["user_id"]))
    doc = cursor.fetchone()
    cursor.close()
    db.close()

    if not doc:
        flash("Document not found or unauthorized.", "error")
        return redirect(url_for("upload"))

    return render_template("preview.html", document=doc, get_document_status=get_document_status)

# Delete Route-------------------
@app.route("/delete/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    if "user_id" not in session:
        flash("You must be logged in to delete documents.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # ✅ Ensure document belongs to current user
    cursor.execute("SELECT * FROM documents WHERE id = %s AND user_id = %s", (doc_id, session["user_id"]))
    doc = cursor.fetchone()

    if not doc:
        cursor.close()
        db.close()
        flash("Document not found or unauthorized.", "error")
        return redirect(url_for("upload"))

    # ✅ Delete file from disk
    file_path = doc["file_path"]
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    # ✅ Delete related reminders
    cursor.execute("DELETE FROM reminders WHERE document_id = %s", (doc_id,))
    
    # ✅ Delete document
    cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Document deleted successfully.", "success")
    return redirect(url_for("upload"))

# Clear Search Route
@app.route("/clear-search")
def clear_search():
    return redirect(url_for("upload"))

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful! Welcome back, " + user["username"], "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not email or not password:
            flash("All fields are required!", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("register"))

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Email already exists.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("register"))

        # Generate OTP and store pending data in session
        otp = generate_otp()
        session['pending_registration'] = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password)
        }

        # Store OTP in database with expiry
        expiry_time = datetime.now() + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO otp_verifications (email, otp, expiry)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE otp = %s, expiry = %s
        """, (email, otp, expiry_time, otp, expiry_time))
        db.commit()
        cursor.close()
        db.close()

        # Send OTP email
        if send_otp_email(email, otp, username):
            flash("OTP sent to your email. Please verify to complete registration.", "info")
            return redirect(url_for("otp_verify"))
        else:
            flash("Failed to send OTP. Please try again.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

# OTP Verification Page
@app.route("/otp_verify", methods=["GET", "POST"])
def otp_verify():
    if request.method == "POST":
        otp = request.form.get("otp").strip()

        if not otp:
            flash("OTP is required!", "error")
            return redirect(url_for("otp_verify"))

        if 'pending_registration' not in session:
            flash("No pending registration found. Please register again.", "error")
            return redirect(url_for("register"))

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        pending = session['pending_registration']
        email = pending['email']

        # Check OTP
        cursor.execute("""
            SELECT otp, expiry FROM otp_verifications
            WHERE email = %s
        """, (email,))
        otp_record = cursor.fetchone()

        if not otp_record:
            flash("OTP not found. Please try registering again.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("register"))

        if datetime.now() > otp_record['expiry']:
            flash("OTP has expired. Please try registering again.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("register"))

        if otp != otp_record['otp']:
            flash("Invalid OTP. Please try again.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("otp_verify"))

        # Log the successful verification
        app.logger.info(f"OTP verified successfully for email: {email}")

        # OTP is valid, complete registration
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
        """, (pending['username'], pending['email'], pending['password_hash']))
        db.commit()

        # Use the inserted id to create default preferences
        user_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO user_notification_preferences
            (user_id, notify_30_days, notify_7_days, notify_1_day, notify_day_of)
            VALUES (%s, TRUE, TRUE, TRUE, TRUE)
        """, (user_id,))
        db.commit()

        # Clean up OTP record
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        db.commit()

        cursor.close()
        db.close()

        # Clear session
        session.pop('pending_registration', None)

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("otp_verify.html")

# Profile Page
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("You must be logged in to view your profile.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Notification preferences from form (checkboxes)
        notify_30_days = 'notify_30_days' in request.form
        notify_7_days = 'notify_7_days' in request.form
        notify_1_day = 'notify_1_day' in request.form
        notify_day_of = 'notify_day_of' in request.form

        if not username or not email:
            flash("Username and email are required.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("profile"))

        # Fetch current user data for validation
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (session["user_id"],))
        current_user = cursor.fetchone()
        if not current_user:
            flash("User not found.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("login"))

        cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, session["user_id"]))
        if cursor.fetchone():
            flash("Email already registered to another account.", "error")
            cursor.close()
            db.close()
            return redirect(url_for("profile"))

        if new_password:
            if not current_password:
                flash("Current password is required to change password.", "error")
                cursor.close()
                db.close()
                return redirect(url_for("profile"))
            if not check_password_hash(current_user["password_hash"], current_password):
                flash("Current password is incorrect.", "error")
                cursor.close()
                db.close()
                return redirect(url_for("profile"))
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                cursor.close()
                db.close()
                return redirect(url_for("profile"))
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "error")
                cursor.close()
                db.close()
                return redirect(url_for("profile"))
            hashed_password = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s, password_hash = %s 
                WHERE id = %s
            """, (username, email, hashed_password, session["user_id"]))
        else:
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s 
                WHERE id = %s
            """, (username, email, session["user_id"]))

        # Update/insert notification preferences (store as 0/1)
        cursor.execute("""
            INSERT INTO user_notification_preferences 
            (user_id, notify_30_days, notify_7_days, notify_1_day, notify_day_of)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notify_30_days = VALUES(notify_30_days),
                notify_7_days = VALUES(notify_7_days),
                notify_1_day = VALUES(notify_1_day),
                notify_day_of = VALUES(notify_day_of)
        """, (session["user_id"], int(notify_30_days), int(notify_7_days), int(notify_1_day), int(notify_day_of)))

        db.commit()
        session["username"] = username
        flash("Profile and preferences updated successfully.", "success")
        cursor.close()
        db.close()
        return redirect(url_for("profile"))

    # GET request - fetch current user data and preferences
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()

    cursor.execute("SELECT notify_30_days, notify_7_days, notify_1_day, notify_day_of FROM user_notification_preferences WHERE user_id = %s", (session["user_id"],))
    prefs_row = cursor.fetchone()

    if not prefs_row:
        # Provide default boolean prefs for template
        user_prefs = {
            'notify_30_days': True,
            'notify_7_days': True,
            'notify_1_day': True,
            'notify_day_of': True
        }
    else:
        # Convert 0/1 to booleans
        user_prefs = {k: bool(v) for k, v in prefs_row.items()}

    cursor.close()
    db.close()

    return render_template("profile.html", user=user, user_prefs=user_prefs)

# Calendar
@app.route("/calendar")
def calendar_view():
    if "user_id" not in session:
        flash("Please log in to view your calendar.")
        return redirect(url_for("login"))

    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, expiry_date FROM documents
        WHERE user_id = %s AND expiry_date IS NOT NULL
          AND YEAR(expiry_date) = %s AND MONTH(expiry_date) = %s
    """, (session["user_id"], year, month))
    docs = cursor.fetchall()
    cursor.close()
    db.close()

    events = {}
    for d in docs:
        exp = d['expiry_date']
        status = get_document_status(exp)
        if isinstance(exp, datetime):
            exp = exp.date()
        date_str = exp.strftime('%Y-%m-%d')
        events[date_str] = {'label': d['title'], 'status': status}

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)

    def prev_month(y, m):
        return (y-1, 12) if m==1 else (y, m-1)

    def next_month(y, m):
        return (y+1, 1) if m==12 else (y, m+1)

    prev_year, prev_month_num = prev_month(year, month)
    next_year, next_month_num = next_month(year, month)
    month_name = calendar.month_name[month]

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        month_days=month_days,
        events=events,
        prev_year=prev_year,
        prev_month=prev_month_num,
        next_year=next_year,
        next_month=next_month_num,
        today=datetime.today().date()
    )

# Dashboard - (user-scoped counts)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("You must be logged in to view the dashboard.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    today = date.today()

    member_id = session.get("active_member_id")

    if member_id is not None:
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE user_id = %s AND member_id = %s", (session["user_id"], member_id))
        total_documents = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM documents 
            WHERE user_id = %s AND member_id = %s AND expiry_date IS NOT NULL AND expiry_date > %s AND expiry_date <= %s
        """, (session["user_id"], member_id, today, today + timedelta(days=7)))
        expiring_soon = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM documents 
            WHERE user_id = %s AND member_id = %s AND expiry_date IS NOT NULL AND expiry_date < %s
        """, (session["user_id"], member_id, today))
        expired_documents = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT title, uploaded_on, expiry_date 
            FROM documents 
            WHERE user_id = %s AND member_id = %s
            ORDER BY uploaded_on DESC LIMIT 5
        """, (session["user_id"], member_id))
        recent_documents = cursor.fetchall()

        cursor.execute("""
            SELECT d.title, r.reminder_date, r.reminder_type, r.sent_flag
            FROM reminders r
            JOIN documents d ON r.document_id = d.id
            WHERE d.user_id = %s AND d.member_id = %s AND r.reminder_date >= %s
            ORDER BY r.reminder_date ASC LIMIT 10
        """, (session["user_id"], member_id, today))
        upcoming_reminders = cursor.fetchall()
    else:
        # Member ID not set, fallback to no member filter
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE user_id = %s", (session["user_id"],))
        total_documents = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM documents 
            WHERE user_id = %s AND expiry_date IS NOT NULL AND expiry_date > %s AND expiry_date <= %s
        """, (session["user_id"], today, today + timedelta(days=7)))
        expiring_soon = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM documents 
            WHERE user_id = %s AND expiry_date IS NOT NULL AND expiry_date < %s
        """, (session["user_id"], today))
        expired_documents = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT title, uploaded_on, expiry_date 
            FROM documents 
            WHERE user_id = %s
            ORDER BY uploaded_on DESC LIMIT 5
        """, (session["user_id"],))
        recent_documents = cursor.fetchall()

        cursor.execute("""
            SELECT d.title, r.reminder_date, r.reminder_type, r.sent_flag
            FROM reminders r
            JOIN documents d ON r.document_id = d.id
            WHERE d.user_id = %s AND r.reminder_date >= %s
            ORDER BY r.reminder_date ASC LIMIT 10
        """, (session["user_id"], today))
        upcoming_reminders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("dashboard.html",
                           total_documents=total_documents,
                           expiring_soon=expiring_soon,
                           expired_documents=expired_documents,
                           recent_documents=recent_documents,
                           upcoming_reminders=upcoming_reminders,
                           today=today)

#---------------Family_mode------------------------------
@app.route("/family_mode")
def family_mode():
    if "user_id" not in session:
        flash("Please login to access Family Mode.", "error")
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM family_members WHERE user_id = %s", (session["user_id"],))
    members = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("family_mode.html", members=members)

@app.route("/add_member", methods=["POST"])
def add_member():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name")
    relation = request.form.get("relation")

    if not name:
        flash("Name is required!", "error")
        return redirect(url_for("family_mode"))

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("INSERT INTO family_members (user_id, name, relation) VALUES (%s, %s, %s)",
                   (session["user_id"], name, relation))
    db.commit()
    cursor.close()
    db.close()

    flash("Family member added successfully!", "success")
    return redirect(url_for("family_mode"))

@app.route("/switch_member/<int:member_id>")
def switch_member(member_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM family_members WHERE id = %s AND user_id = %s", (member_id, session["user_id"]))
    member = cursor.fetchone()
    cursor.close()
    db.close()

    if not member:
        flash("Member not found or unauthorized.", "error")
        return redirect(url_for("family_mode"))

    session["active_member_id"] = member_id
    flash(f"Switched to {member[2]} ({member[3]})", "success")  # name and relation in columns 2 and 3

    return redirect(url_for("dashboard"))

# Test route for manually triggering reminders
@app.route("/test-reminders")
def test_reminders():
    if "user_id" not in session:
        flash("You need to be logged in to test reminders", "error")
        return redirect(url_for("login"))

    check_and_send_reminders()
    flash("Reminder check completed. Check console for results.", "success")
    return redirect(url_for("upload"))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True) 