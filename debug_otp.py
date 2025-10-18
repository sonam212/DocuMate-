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
cursor.execute('SELECT * FROM otp_verifications WHERE email = %s', ('unique@example.com',))
result = cursor.fetchone()
cursor.close()
db.close()
if result:
    print(f'OTP Record: {result}')
else:
    print('No OTP record found')
