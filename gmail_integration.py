"""
Gmail Integration Module for Email Reminder System

This module handles connecting to Gmail API and fetching emails.
Requires Gmail API credentials setup.
"""

import os
import json
import base64
from email.mime.text import MIMEText
from typing import Dict, List, Optional
from datetime import datetime, timedelta

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    GOOGLE_LIBRARIES_AVAILABLE = True
except ImportError:
    GOOGLE_LIBRARIES_AVAILABLE = False

class GmailIntegrator:
    """Handles Gmail API integration for the email reminder system"""
    
    # Gmail API scope - read-only access to Gmail
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_file=None, token_file='token.json', credentials=None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.credentials = credentials  # Accept direct credentials object
        
        if not GOOGLE_LIBRARIES_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. Run: "
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
    
    def authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        
        # Use provided credentials if available (for Vercel/serverless)
        if self.credentials:
            print("✅ Using provided credentials object")
            creds = self.credentials
        # Load existing token (JSON format from OAuth callback)
        elif os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as token:
                    creds_data = json.load(token)
                creds = Credentials.from_authorized_user_info(creds_data)
            except Exception as e:
                print(f"⚠️ Error loading token: {e}")
                creds = None
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed credentials only if using file-based auth
                if not self.credentials and self.token_file:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
            else:
                if not self.credentials_file or not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Gmail credentials not available. "
                        "Please authenticate via /auth/google endpoint."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                
                # Save credentials as JSON
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
        
        # Build Gmail service
        self.service = build('gmail', 'v1', credentials=creds)
        return self.service
    
    def get_recent_emails(self, max_results=50, days_back=7, query="") -> List[Dict]:
        """
        Fetch recent emails from Gmail
        
        Args:
            max_results: Maximum number of emails to fetch
            days_back: Number of days to look back
            query: Gmail search query (optional)
            
        Returns:
            List of email dictionaries with parsed content
        """
        if not self.service:
            self.authenticate()
        
        # Build query for recent emails
        date_filter = datetime.now() - timedelta(days=days_back)
        date_str = date_filter.strftime('%Y/%m/%d')
        
        search_query = f"after:{date_str}"
        if query:
            search_query += f" {query}"
        
        try:
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me', 
                q=search_query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            emails = []
            print(f"📧 Found {len(messages)} emails to process...")
            
            for i, message in enumerate(messages):
                try:
                    # Get full message details
                    msg = self.service.users().messages().get(
                        userId='me', 
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_email_message(msg)
                    if email_data:
                        emails.append(email_data)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"   Processed {i + 1}/{len(messages)} emails...")
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing email {message.get('id', 'unknown')}: {e}")
                    continue
            
            print(f"✅ Successfully processed {len(emails)} emails")
            return emails
            
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []
    
    def _parse_email_message(self, message) -> Optional[Dict]:
        """Parse a Gmail API message into a structured dictionary"""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract header information
            email_data = {
                'id': message['id'],
                'thread_id': message['threadId'],
                'subject': '',
                'sender': '',
                'recipient': '',
                'date': '',
                'body': '',
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', [])
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'subject':
                    email_data['subject'] = value
                elif name == 'from':
                    email_data['sender'] = value
                elif name == 'to':
                    email_data['recipient'] = value
                elif name == 'date':
                    email_data['date'] = value
            
            # Extract email body
            email_data['body'] = self._extract_body(message['payload'])
            
            # Convert date to standard format
            if email_data['date']:
                try:
                    from email.utils import parsedate_to_datetime
                    parsed_date = parsedate_to_datetime(email_data['date'])
                    email_data['date'] = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass  # Keep original date format if parsing fails
            
            return email_data
            
        except Exception as e:
            print(f"   ⚠️ Error parsing email: {e}")
            return None
    
    def _extract_body(self, payload) -> str:
        """Extract text body from email payload"""
        body = ""
        
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    body += self._extract_body(part)
            else:
                # Single part message
                if payload.get('mimeType') == 'text/plain':
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                elif payload.get('mimeType') == 'text/html':
                    # For HTML, we might want to strip tags (simplified approach)
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        # Simple HTML tag removal (for basic cases)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
        
        except Exception as e:
            print(f"   ⚠️ Error extracting body: {e}")
        
        return body.strip()
    
    def search_emails(self, query: str, max_results=10) -> List[Dict]:
        """
        Search emails using Gmail query syntax
        
        Args:
            query: Gmail search query (e.g., "from:careers@company.com", "subject:interview")
            max_results: Maximum number of results
            
        Returns:
            List of matching email dictionaries
        """
        if not self.service:
            self.authenticate()
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_email_message(msg)
                    if email_data:
                        emails.append(email_data)
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing search result: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            print(f"❌ Error searching emails: {e}")
            return []

# Demo function for testing Gmail integration
def test_gmail_integration():
    """Test function to verify Gmail API setup"""
    print("🧪 Testing Gmail Integration...")
    
    if not GOOGLE_LIBRARIES_AVAILABLE:
        print("❌ Google API libraries not installed")
        print("   Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return
    
    try:
        gmail = GmailIntegrator()
        
        # Test authentication
        print("🔑 Authenticating with Gmail...")
        gmail.authenticate()
        print("✅ Authentication successful")
        
        # Test fetching recent emails (just a few for testing)
        print("📧 Fetching recent emails...")
        emails = gmail.get_recent_emails(max_results=5, days_back=1)
        
        print(f"✅ Retrieved {len(emails)} emails")
        
        # Show sample email data (without sensitive content)
        if emails:
            sample = emails[0]
            print(f"\n📋 Sample email structure:")
            print(f"   Subject: {sample.get('subject', 'N/A')[:50]}...")
            print(f"   From: {sample.get('sender', 'N/A')[:30]}...")
            print(f"   Date: {sample.get('date', 'N/A')}")
            print(f"   Body length: {len(sample.get('body', ''))} characters")
        
    except Exception as e:
        print(f"❌ Gmail integration test failed: {e}")
        print("   Make sure you have:")
        print("   1. Downloaded credentials.json from Google Cloud Console")
        print("   2. Enabled Gmail API for your project")
        print("   3. Configured OAuth consent screen")

if __name__ == "__main__":
    test_gmail_integration()