import os
import smtplib

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

print("EMAIL_ADDRESS =", EMAIL_ADDRESS)
print("EMAIL_PASSWORD =", EMAIL_PASSWORD)

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    print("✅ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
finally:
    server.quit()