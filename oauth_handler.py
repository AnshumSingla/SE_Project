#!/usr/bin/env python3
"""
Direct OAuth Handler - Bypasses frontend redirect URI issues
This creates the Gmail/Calendar tokens directly without frontend OAuth
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail and Calendar scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

def create_tokens():
    """
    Create Gmail and Calendar tokens directly
    This bypasses the frontend OAuth redirect URI issues
    """
    print("🔐 Starting Direct OAuth Authentication...")
    print("This will open a browser window for you to authenticate with Google")
    
    # Check if credentials file exists
    credentials_file = 'frontend/client_secret_851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com.json'
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        return False
    
    creds = None
    token_file = 'gmail_token.json'
    
    # Check if token already exists
    if os.path.exists(token_file):
        print("📱 Loading existing tokens...")
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired tokens...")
            creds.refresh(Request())
        else:
            print("🌐 Opening browser for authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        # Save the credentials for the next run
        print("💾 Saving tokens...")
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        # Also create calendar token (same credentials)
        with open('calendar_token.json', 'w') as cal_token:
            cal_token.write(creds.to_json())
    
    print("✅ Authentication successful!")
    print(f"📧 Gmail token saved: {token_file}")
    print(f"📅 Calendar token saved: calendar_token.json")
    
    # Test the tokens
    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"📧 Gmail connected: {profile.get('emailAddress')}")
        
        calendar_service = build('calendar', 'v3', credentials=creds)
        calendar_list = calendar_service.calendarList().list().execute()
        print(f"📅 Calendar connected: {len(calendar_list.get('items', []))} calendars found")
        
        return True
    except Exception as e:
        print(f"❌ Error testing tokens: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Smart Job Reminder - Direct OAuth Setup")
    print("=" * 50)
    print()
    print("This will:")
    print("1. Open a browser window for Google authentication")
    print("2. Create gmail_token.json and calendar_token.json files")
    print("3. Bypass the frontend OAuth redirect issues")
    print()
    input("Press Enter to continue...")
    
    if create_tokens():
        print()
        print("🎉 SUCCESS! Your tokens are ready.")
        print("Now you can use the full system with real Gmail integration!")
        print()
        print("Next steps:")
        print("1. Restart your Flask backend")
        print("2. Use the frontend normally - it will use real Gmail data")
    else:
        print()
        print("❌ Authentication failed. Please check your credentials file.")