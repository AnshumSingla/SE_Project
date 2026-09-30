"""
Requirements Verification Script
Tests that all required packages are installed and importable
"""

import sys

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    display_name = package_name or module_name
    try:
        __import__(module_name)
        print(f"✅ {display_name}")
        return True
    except ImportError as e:
        print(f"❌ {display_name} - {e}")
        return False

def main():
    print("\n" + "="*60)
    print("REQUIREMENTS VERIFICATION")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Core packages
    print("🌐 Web API Service:")
    all_passed &= test_import("flask", "Flask")
    all_passed &= test_import("flask_cors", "Flask-CORS")
    
    print("\n🔗 Google APIs:")
    all_passed &= test_import("googleapiclient.discovery", "google-api-python-client")
    all_passed &= test_import("google.auth", "google-auth")
    all_passed &= test_import("google_auth_oauthlib", "google-auth-oauthlib")
    all_passed &= test_import("google.auth.transport.requests", "google-auth-httplib2")
    
    print("\n🔐 Security & Configuration:")
    all_passed &= test_import("dotenv", "python-dotenv")
    all_passed &= test_import("cryptography")
    
    print("\n🌍 HTTP & Networking:")
    all_passed &= test_import("requests")
    all_passed &= test_import("oauthlib")
    
    print("\n📅 Date/Time & Data:")
    all_passed &= test_import("dateutil", "python-dateutil")
    all_passed &= test_import("pytz")
    
    print("\n🔧 Core Supporting:")
    all_passed &= test_import("pydantic")
    all_passed &= test_import("cachetools")
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL REQUIREMENTS SATISFIED")
        print("="*60 + "\n")
        return 0
    else:
        print("❌ SOME REQUIREMENTS MISSING")
        print("="*60 + "\n")
        print("Run: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
