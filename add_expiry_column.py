import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="DocuMate@2025!",
    database="documate"
)

cursor = db.cursor()

try:
    # Check if 'expiry_date' column exists
    cursor.execute("""
        SHOW COLUMNS FROM documents LIKE 'expiry_date';
    """)
    result = cursor.fetchone()

    if result:
        print("ℹ Column 'expiry_date' already exists. No changes made.")
    else:
        cursor.execute("ALTER TABLE documents ADD expiry_date DATE;")
        print("✅ Column 'expiry_date' added successfully.")

except mysql.connector.Error as err:
    print(f"⚠ Error: {err}")

cursor.close()
db.close()