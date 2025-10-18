import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

db = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'DocuMate@2025!'),
    database=os.getenv('DB_NAME', 'documate')
)
cursor = db.cursor(dictionary=True)
cursor.execute('SELECT email, otp FROM otp_verifications ORDER BY created_at DESC LIMIT 1')
result = cursor.fetchone()
cursor.close()
db.close()
if result:
    print(f'Latest OTP: {result["otp"]} for {result["email"]}')
else:
    print('No OTP found')
