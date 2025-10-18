import mysql.connector
from werkzeug.security import generate_password_hash

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="DocuMate@2025!",
    database="documate"
)
cursor = db.cursor()
cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", ("testuser", "test@example.com", generate_password_hash("password")))
db.commit()
cursor.close()
db.close()
print("Test user inserted")
