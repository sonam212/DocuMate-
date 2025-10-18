import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # MySQL Workbench login
        password="DocuMate@2025!",  # MySQL root password
        database="documate"  # database name
    )

try:
    connection = get_db_connection()
    if connection.is_connected():
        print("✅ Connected to MySQL database:", connection.database)

except mysql.connector.Error as err:
    print("❌ Error:", err)

finally:
    if 'connection' in locals() and connection.is_connected():
        connection.close()