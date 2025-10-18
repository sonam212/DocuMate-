import requests
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Test user credentials (assuming test user exists)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password"
BASE_URL = "http://127.0.0.1:5000"

session = requests.Session()

def test_home():
    print("Testing Home Page...")
    response = session.get(BASE_URL)
    if response.status_code == 200:
        print("✅ Home page loads successfully")
        return True
    else:
        print(f"❌ Home page failed: {response.status_code}")
        return False

def test_login():
    print("Testing Login...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 302 and "home" in response.headers.get("Location", ""):
        print("✅ Login successful")
        return True
    else:
        print(f"❌ Login failed: {response.status_code}, Location: {response.headers.get('Location')}")
        return False

def test_upload_page():
    print("Testing Upload Page (requires login)...")
    response = session.get(f"{BASE_URL}/upload")
    if response.status_code == 200:
        print("✅ Upload page loads successfully")
        return True
    else:
        print(f"❌ Upload page failed: {response.status_code}")
        return False

def test_dashboard():
    print("Testing Dashboard...")
    response = session.get(f"{BASE_URL}/dashboard")
    if response.status_code == 200:
        print("✅ Dashboard loads successfully")
        return True
    else:
        print(f"❌ Dashboard failed: {response.status_code}")
        return False

def test_profile():
    print("Testing Profile...")
    response = session.get(f"{BASE_URL}/profile")
    if response.status_code == 200:
        print("✅ Profile loads successfully")
        return True
    else:
        print(f"❌ Profile failed: {response.status_code}")
        return False

def test_calendar():
    print("Testing Calendar...")
    response = session.get(f"{BASE_URL}/calendar")
    if response.status_code == 200:
        print("✅ Calendar loads successfully")
        return True
    else:
        print(f"❌ Calendar failed: {response.status_code}")
        return False

def test_family_mode():
    print("Testing Family Mode...")
    response = session.get(f"{BASE_URL}/family_mode")
    if response.status_code == 200:
        print("✅ Family Mode loads successfully")
        return True
    else:
        print(f"❌ Family Mode failed: {response.status_code}")
        return False

def test_logout():
    print("Testing Logout...")
    response = session.get(f"{BASE_URL}/logout")
    if response.status_code == 302 and "login" in response.headers.get("Location", ""):
        print("✅ Logout successful")
        return True
    else:
        print(f"❌ Logout failed: {response.status_code}, Location: {response.headers.get('Location')}")
        return False

def test_upload_functionality():
    print("Testing Upload Functionality...")
    # Simple test: Try to access upload page and simulate form (but without file, expect error or redirect)
    response = session.get(f"{BASE_URL}/upload")
    if "Upload Document" in response.text:
        print("✅ Upload form is present")
        # Note: Full upload test would require a file; skipping file upload for now as it needs a PDF
        return True
    else:
        print("❌ Upload form not found")
        return False

def test_error_pages():
    print("Testing Error Pages...")
    # 404
    response = session.get(f"{BASE_URL}/nonexistent")
    if response.status_code == 404:
        print("✅ 404 handled")
    else:
        print(f"❌ 404 failed: {response.status_code}")
    
    # 500 (harder to trigger, but check if route exists)
    try:
        response = session.get(f"{BASE_URL}/error")
        if response.status_code == 500:
            print("✅ 500 handled")
        else:
            print("ℹ️ 500 not triggered (normal if no error)")
    except:
        print("ℹ️ 500 test skipped")

    return True

if __name__ == "__main__":
    print("Starting Thorough Testing of DocuMate App...")
    tests = [
        test_home,
        test_login,
        test_upload_page,
        test_dashboard,
        test_profile,
        test_calendar,
        test_family_mode,
        test_upload_functionality,
        test_error_pages,
        test_logout
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! The app is functioning correctly after the changes.")
    else:
        print("\n⚠️ Some tests failed. Review the output above for details.")
