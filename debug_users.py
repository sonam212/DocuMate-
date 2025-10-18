import mysql.connector

db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='DocuMate@2025!',
    database='documate'
)
cursor = db.cursor()
cursor.execute('SELECT id, username, email, password_hash FROM users')
users = cursor.fetchall()
print('Users:')
for user in users:
    print(user)
cursor.close()
db.close()
