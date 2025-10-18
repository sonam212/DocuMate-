from werkzeug.security import generate_password_hash
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="DocuMate@2025!",
        database="documate",
    )

# Generate hash for 'password'
hashed = generate_password_hash('password')

db = get_db_connection()
cursor = db.cursor()
cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed, 'demo@email.com'))
db.commit()
cursor.close()
db.close()

print(f"Password reset for demo@email.com to 'password' (hashed: {hashed})")
