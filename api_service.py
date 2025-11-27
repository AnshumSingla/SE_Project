"""
Email Reminder API Service

Flask-based API service that provides endpoints for the web/mobile app
to interact with the AutoGen email processing system.
"""

from flask import Flask, request, jsonify, redirect, session, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import urllib.parse
import secrets
from google.oauth2.credentials import Credentials
from datetime import datetime
from typing import Dict, List, Optional
import traceback

# Load environment variables
load_dotenv()

# Import our email processing system
from complete_system import IntegratedEmailReminderSystem

# Load environment variables
load_dotenv()

app = Flask(__name__)

# IMPORTANT: Set a secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# Configure session
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for cross-site cookies
app.config['SESSION_COOKIE_SECURE'] = True  # Required for production HTTPS

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    os.environ.get('FRONTEND_URL', '').rstrip('/'),
    os.environ.get('VITE_FRONTEND_URL', '').rstrip('/')
]
# Remove empty strings
ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]

# Enable CORS with credentials and explicit methods
CORS(app, 
     origins=ALLOWED_ORIGINS, 
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Google OAuth Configuration (Manual - No Authlib!)
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
# Use environment variable for redirect URI (NO FALLBACK - must be set in production)
BACKEND_URL = os.environ.get('BACKEND_URL')
if not BACKEND_URL:
    raise ValueError("❌ BACKEND_URL environment variable must be set! Set it in Vercel dashboard.")
REDIRECT_URI = f"{BACKEND_URL.rstrip('/')}/auth/google/callback"
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

# Global system instance
email_system = None

def get_credentials_from_session():
    """Get Google API credentials from session (Vercel-compatible)"""
    credentials_dict = session.get('credentials')
    if not credentials_dict:
        return None
    return Credentials.from_authorized_user_info(credentials_dict)

def init_system():
    """Initialize the email reminder system"""
    global email_system
    try:
        email_system = IntegratedEmailReminderSystem(use_llm=True)
        return True
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return False

# Initialize system at module level for Vercel
try:
    print("🔄 Initializing email system...")
    email_system = IntegratedEmailReminderSystem(use_llm=True)
    print("✅ Email system initialized successfully")
except Exception as e:
    print(f"⚠️ Email system initialization failed: {e}")
    email_system = None

@app.after_request
def after_request(response):
    """Ensure CORS headers are set on all responses"""
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/debug/config')
def debug_config():
    """Debug endpoint to check environment variables"""
    return jsonify({
        'BACKEND_URL': os.environ.get('BACKEND_URL', 'NOT SET - using default'),
        'REDIRECT_URI': REDIRECT_URI,
        'FRONTEND_URL': os.environ.get('FRONTEND_URL', 'NOT SET'),
        'ALLOWED_ORIGINS': ALLOWED_ORIGINS,
        'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_CLIENT_ID', 'NOT SET')[:20] + '...' if os.environ.get('GOOGLE_CLIENT_ID') else 'NOT SET'
    })

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth flow - Manual implementation (no Authlib!)"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Debug log
    print(f"🔍 BACKEND_URL from env: {os.environ.get('BACKEND_URL', 'NOT SET')}")
    print(f"🔗 Using REDIRECT_URI: {REDIRECT_URI}")
    
    # Build authorization URL manually
    params = {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'state': state,
        'access_type': 'offline',  # Request refresh token
        'prompt': 'consent'  # Force consent screen to get refresh token
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    print(f"🔗 Redirecting to: {auth_url}")
    
    return redirect(auth_url)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback with manual token exchange"""
    try:
        # Verify state to prevent CSRF attacks
        state = request.args.get('state')
        if state != session.get('oauth_state'):
            raise Exception("Invalid state parameter - possible CSRF attack")
        
        # Get authorization code from URL
        code = request.args.get('code')
        
        if not code:
            raise Exception("No authorization code received")
        
        # Manually exchange code for token
        token_data = {
            'code': code,
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        print(f"🔄 Exchanging authorization code for access token...")
        
        # Exchange code for token
        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        token_response.raise_for_status()
        token = token_response.json()
        
        access_token = token.get('access_token')
        refresh_token = token.get('refresh_token')
        
        print(f"✅ Access token received: {access_token[:20]}...")
        print(f"🔄 Refresh token received: {'Yes' if refresh_token else 'No'}")
        
        # Get user info from Google
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        
        # Store in session
        session['user'] = user_info
        session['access_token'] = access_token
        session['refresh_token'] = token.get('refresh_token')
        
        # Create credentials for Gmail/Calendar APIs
        credentials_dict = {
            'token': access_token,
            'refresh_token': token.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'scopes': token.get('scope', '').split()
        }
        
        credentials = Credentials.from_authorized_user_info(credentials_dict)
        
        # Store credentials in session (not on disk - Vercel filesystem is read-only)
        session['credentials'] = credentials_dict
        print("💾 Credentials stored in session (not writing to disk on Vercel)")
        
        # Extract user info
        email = user_info.get('email', '').replace('"', '&quot;')
        name = user_info.get('name', '').replace('"', '&quot;')
        picture = user_info.get('picture', '').replace('"', '&quot;')
        user_id = user_info.get('id', '').replace('"', '&quot;')
        
        print(f"✅ Manual token exchange successful: {email}")
        
        # Get frontend URL from environment for postMessage
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        
        return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Success</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; text-align: center; background: #f0f0f0; }}
                    .success {{ color: #00cc00; font-size: 24px; }}
                </style>
            </head>
            <body>
                <div class="success">✅ Authentication Successful!</div>
                <p>This window will close automatically...</p>
                <script>
                    console.log('OAuth callback: Sending message to parent...');
                    if (window.opener && !window.opener.closed) {{
                        try {{
                            window.opener.postMessage({{
                                success: true,
                                user: {{
                                    email: "{email}",
                                    name: "{name}",
                                    picture: "{picture}",
                                    sub: "{user_id}"
                                }},
                                accessToken: "{access_token}"
                            }}, '*');
                            console.log('OAuth callback: Message sent successfully');
                            
                            // Close after message is sent
                            setTimeout(() => {{
                                console.log('OAuth callback: Closing popup...');
                                window.close();
                            }}, 1500);
                        }} catch (e) {{
                            console.error('OAuth callback: Error sending message:', e);
                        }}
                    }} else {{
                        console.log('OAuth callback: No opener window found');
                        document.body.innerHTML += '<p>Please close this window and return to the app.</p>';
                    }}
                </script>
            </body>
            </html>
        '''
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return f'''
            <!DOCTYPE html>
            <html>
            <body>
                <h2>❌ Error</h2>
                <p>{str(e)}</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            error: '{str(e)}'
                        }}, '*');
                    }}
                </script>
            </body>
            </html>
        '''

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_ready": email_system is not None
    })

@app.route('/api/auth/setup', methods=['POST'])
def setup_user_credentials():
    """
    Setup user's Google credentials for Gmail and Calendar access
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "gmail_credentials": "base64_encoded_credentials",
        "calendar_credentials": "base64_encoded_credentials"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Store user credentials securely (implement proper encryption)
        # For now, return success
        
        return jsonify({
            "success": True,
            "message": "User credentials setup successfully",
            "user_id": user_id
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/emails/scan', methods=['POST'])
def scan_emails():
    """
    Scan user's emails and process them for job opportunities
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "max_emails": 50,
        "days_back": 7,
        "search_query": "optional gmail search query"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        access_token = data.get('access_token')  # Get access token from request
        max_emails = data.get('max_emails', 50)
        days_back = data.get('days_back', 7)
        search_query = data.get('search_query', '')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        print(f"🔍 Scanning emails for user: {user_id}")
        print(f"📧 Access token provided: {'Yes' if access_token else 'No'}")
        
        # Try to get credentials from session first
        credentials = get_credentials_from_session()
        
        # If no session credentials, try to use access token from request
        if not credentials and access_token and access_token != 'demo_token_for_testing':
            print(f"🔑 No session credentials, attempting to use access token from request")
            try:
                # Reconstruct credentials from access token
                from google.oauth2.credentials import Credentials
                credentials = Credentials(
                    token=access_token,
                    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                    token_uri='https://oauth2.googleapis.com/token',
                    scopes=SCOPES
                )
                print(f"✅ Reconstructed credentials from access token")
            except Exception as e:
                print(f"❌ Failed to reconstruct credentials: {e}")
                credentials = None
        
        if not credentials:
            print("⚠️ No valid credentials available - Gmail authentication required")
            return jsonify({
                "success": False,
                "error": "Gmail authentication required",
                "message": "Please sign in with Google to scan your emails"
            }), 401
        
        print(f"✅ Valid credentials available")
        
        # Process emails using the system
        if not email_system:
            return jsonify({
                "success": False,
                "error": "Email system not initialized"
            }), 500
        
        # Set credentials for Gmail service
        from gmail_integration import GmailIntegrator
        email_system.gmail = GmailIntegrator(credentials=credentials)
        
        # Fetch and process real emails from user's Gmail account
        print(f"📧 Attempting to process emails for user: {user_id}")
        results = email_system.process_user_emails(
            user_id=user_id,
            max_emails=max_emails,
            days_back=days_back,
            search_query=search_query
        )
        print(f"✅ Successfully processed {len(results)} emails from Gmail")
        
        # Format results for API response (filter out duplicates, rejected items, and no-deadline emails)
        formatted_results = []
        skipped_count = 0
        expired_count = 0
        duplicate_count = 0
        
        # Load existing calendar events once for duplicate detection
        existing_titles = _get_existing_calendar_events()
        
        for result in results:
            email_data = result.get('email_data', {})
            classification = result.get('classification', {})
            deadline_info = result.get('deadline_info', {})
            calendar_event = result.get('calendar_event')
            
            # Skip emails without deadlines
            if not deadline_info or not deadline_info.get('has_deadline'):
                skipped_count += 1
                continue
            
            # Skip expired deadlines (past dates)
            deadline_date = deadline_info.get('deadline_date')
            if not _is_future_deadline(deadline_date):
                print(f"⏭️ Skipping expired deadline for: {email_data.get('subject', '')[:50]}...")
                expired_count += 1
                skipped_count += 1
                continue
            
            # Skip duplicates already in Google Calendar
            subject = email_data.get('subject', '').strip().lower()
            # Check if subject contains any existing calendar event title
            is_duplicate = any(subject in existing or existing in subject for existing in existing_titles)
            if is_duplicate:
                print(f"🔄 Skipping duplicate (already in calendar): {email_data.get('subject', '')[:50]}...")
                duplicate_count += 1
                skipped_count += 1
                continue
            
            # Skip emails with duplicate or rejected calendar events (from processing)
            if calendar_event:
                status = calendar_event.get('status')
                if status in ['duplicate', 'rejected']:
                    skipped_count += 1
                    continue
            
            formatted_result = {
                "email_id": email_data.get('id', 'sample_' + str(len(formatted_results))),
                "subject": email_data.get('subject', ''),
                "sender": email_data.get('sender', ''),
                "date": email_data.get('date', ''),
                "snippet": email_data.get('snippet', email_data.get('body', '')[:200]),
                "classification": {
                    "is_job_related": classification.get('is_job_related', False),
                    "category": classification.get('category', 'other'),
                    "urgency": classification.get('urgency', 'low'),
                    "confidence": classification.get('confidence', 0.8),
                    "reasoning": classification.get('reason', classification.get('reasoning', ''))
                },
                "deadline": None
            }
            
            # Add deadline information if present
            if deadline_info and deadline_info.get('has_deadline'):
                formatted_result["deadline"] = {
                    "has_deadline": True,
                    "date": deadline_info.get('deadline_date'),
                    "time": deadline_info.get('deadline_time'),
                    "type": deadline_info.get('deadline_type'),
                    "description": deadline_info.get('description'),
                    "text": deadline_info.get('deadline_text'),
                    "urgency_days": _calculate_urgency_days(deadline_info.get('deadline_date'))
                }
            else:
                formatted_result["deadline"] = {"has_deadline": False}
            
            formatted_results.append(formatted_result)
        
        print(f"📊 Filtering summary:")
        print(f"   ⏭️  Expired deadlines: {expired_count}")
        print(f"   🔄 Duplicates (in calendar): {duplicate_count}")
        print(f"   ❌ Total filtered: {skipped_count}")
        print(f"   ✅ New reminders to show: {len(formatted_results)}")
        
        # 🎯 AUTO-CREATE CALENDAR EVENTS for new reminders
        calendar_events_created = 0
        try:
            # Get calendar service
            calendar_credentials = get_credentials_from_session()
            
            # If no session credentials, try to use access token from request
            if not calendar_credentials and access_token and access_token != 'demo_token_for_testing':
                from google.oauth2.credentials import Credentials
                calendar_credentials = Credentials(
                    token=access_token,
                    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                    token_uri='https://oauth2.googleapis.com/token',
                    scopes=SCOPES
                )
            
            if calendar_credentials:
                from googleapiclient.discovery import build
                from google.auth.transport.requests import Request
                
                # Refresh token if expired
                if calendar_credentials.expired and calendar_credentials.refresh_token:
                    calendar_credentials.refresh(Request())
                
                calendar_service = build('calendar', 'v3', credentials=calendar_credentials)
                print(f"📅 Calendar service ready - creating events for {len(formatted_results)} reminders...")
                
                for result in formatted_results:
                    if not result['deadline']['has_deadline']:
                        continue
                    
                    try:
                        deadline_date = result['deadline']['date']
                        deadline_time = result['deadline'].get('time') or '23:59:00'
                        deadline_dt = datetime.fromisoformat(f"{deadline_date}T{deadline_time}")
                        
                        # Create calendar event
                        event_body = {
                            'summary': f"📧 {result['subject'][:100]}",
                            'description': f"From: {result['sender']}\n\n{result['deadline'].get('description', result['snippet'])}",
                            'start': {
                                'dateTime': deadline_dt.isoformat(),
                                'timeZone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata')
                            },
                            'end': {
                                'dateTime': deadline_dt.isoformat(),
                                'timeZone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata')
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                    {'method': 'email', 'minutes': 10080},  # 1 week
                                    {'method': 'popup', 'minutes': 1440},   # 1 day
                                    {'method': 'popup', 'minutes': 60}      # 1 hour
                                ]
                            },
                            'colorId': '11'  # Red for urgency
                        }
                        
                        event = calendar_service.events().insert(
                            calendarId='primary',
                            body=event_body
                        ).execute()
                        
                        calendar_events_created += 1
                        print(f"✅ Created calendar event: {result['subject'][:50]}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to create calendar event for '{result['subject'][:50]}': {e}")
                
                print(f"🎉 Successfully created {calendar_events_created}/{len(formatted_results)} calendar events!")
            else:
                print("⚠️ No calendar credentials available - skipping calendar event creation")
                
        except Exception as e:
            print(f"❌ Calendar event creation error: {e}")
        
        # Calculate summary statistics based on actual valid results
        job_related_count = sum(1 for r in formatted_results if r['classification']['is_job_related'])
        new_reminders_ready = sum(1 for r in formatted_results if r['deadline']['has_deadline'])
        
        return jsonify({
            "success": True,
            "scan_timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "summary": {
                "total_emails_scanned": len(results),
                "valid_future_deadlines": new_reminders_ready,
                "new_reminders_ready": new_reminders_ready,
                "calendar_events_created": calendar_events_created,
                "job_related_emails": job_related_count,
                "expired_filtered": expired_count,
                "duplicates_filtered": duplicate_count,
                "total_filtered": skipped_count,
                "upcoming_only": True,
                "scan_parameters": {
                    "max_emails": max_emails,
                    "days_back": days_back,
                    "search_query": search_query
                }
            },
            "emails": formatted_results
        })
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Email scan error: {error_message}")
        
        # Provide user-friendly error messages
        if "Gmail authentication required" in error_message or "not initialized" in error_message:
            return jsonify({
                "success": False,
                "error": "Gmail authentication required",
                "message": "Please sign in with Google to access your Gmail account",
                "details": error_message
            }), 401
        elif "Failed to fetch emails" in error_message:
            return jsonify({
                "success": False,
                "error": "Failed to fetch emails from Gmail",
                "message": "Unable to access your Gmail. Please check your permissions and try again.",
                "details": error_message
            }), 500
        else:
            return jsonify({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }), 500

@app.route('/api/calendar/reminders', methods=['POST'])
def create_calendar_reminders():
    """
    Create calendar reminders for selected emails with deadlines
    Syncs with Google Calendar for cross-device access
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "emails": [{"email_id": "...", "subject": "...", "deadline": {...}}],
        "reminder_preferences": {
            "default_reminders": [1440, 60],  // minutes before
            "urgent_reminders": [10080, 1440, 60]
        }
    }
    """
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        data = request.get_json()
        user_id = data.get('user_id')
        emails = data.get('emails', [])
        email_ids = data.get('email_ids', [])  # Fallback for old format
        reminder_prefs = data.get('reminder_preferences', {})
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Load calendar credentials from session (Vercel-compatible)
        try:
            credentials = get_credentials_from_session()
            if not credentials:
                print("⚠️ No credentials in session - cannot sync to calendar")
                return jsonify({
                    "success": False,
                    "created": [],
                    "failed": [],
                    "skipped": [],
                    "duplicates": [],
                    "total_created": 0,
                    "note": "Please sign in again to sync with Google Calendar"
                }), 200
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                session['credentials']['token'] = credentials.token
            
            # Build Calendar API service
            calendar_service = build('calendar', 'v3', credentials=credentials)
            
            created_events = []
            failed_events = []
            skipped_events = []
            duplicate_events = []
            
            print(f"📅 Processing {len(emails)} emails for calendar sync...")
            
            for email in emails:
                try:
                    email_id = email.get('email_id')
                    subject = email.get('subject', 'Job Deadline')
                    deadline = email.get('deadline', {})
                    
                    print(f"  📧 Processing: {subject}")
                    print(f"     Deadline: {deadline}")
                    
                    if not deadline.get('has_deadline'):
                        print(f"     ⏭️ Skipped: No deadline found")
                        skipped_events.append({"email_id": email_id, "reason": "no_deadline"})
                        continue
                    
                    # Parse deadline date/time (handle timezone properly)
                    deadline_date = deadline.get('date')
                    deadline_time = deadline.get('time')
                    
                    # Check for duplicates before creating event
                    if deadline_date:
                        from datetime import timedelta
                        try:
                            deadline_dt_check = dt.fromisoformat(deadline_date)
                            time_min = (deadline_dt_check - timedelta(days=1)).isoformat() + 'Z'
                            time_max = (deadline_dt_check + timedelta(days=1)).isoformat() + 'Z'
                            
                            # Check existing events
                            existing_events = calendar_service.events().list(
                                calendarId='primary',
                                timeMin=time_min,
                                timeMax=time_max,
                                singleEvents=True
                            ).execute().get('items', [])
                            
                            # Simple duplicate check
                            subject_words = set(subject.lower().split())
                            is_duplicate = False
                            for existing in existing_events:
                                existing_title = existing.get('summary', '').lower()
                                existing_words = set(existing_title.split())
                                common = subject_words.intersection(existing_words)
                                
                                if len(common) >= len(subject_words) * 0.7:
                                    print(f"     🔄 Duplicate found: {existing.get('summary')}")
                                    duplicate_events.append({
                                        "email_id": email_id,
                                        "existing_event_id": existing['id'],
                                        "reason": "similar_event_exists"
                                    })
                                    is_duplicate = True
                                    break
                            
                            if is_duplicate:
                                continue
                        except Exception as e:
                            print(f"     ⚠️ Error checking duplicates: {e}")
                    
                    # Handle None or missing time - default to 11:59 PM
                    if not deadline_time or deadline_time == 'None':
                        deadline_time = '23:59:00'
                    
                    # Combine date and time, treat as local timezone
                    from datetime import datetime as dt
                    deadline_str = f"{deadline_date}T{deadline_time}"
                    deadline_dt = dt.fromisoformat(deadline_str.replace('Z', ''))
                    
                    # Get user's timezone from environment or default to Asia/Kolkata (India)
                    user_timezone = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Kolkata')
                    
                    # Create event in user's local timezone (don't convert to UTC)
                    event_body = {
                        'summary': f'📧 Job Deadline: {subject[:100]}',
                        'description': f'{deadline.get("description", "")}\n\nEmail: {email.get("snippet", "")}',
                        'start': {
                            'dateTime': deadline_dt.isoformat(),
                            'timeZone': user_timezone,
                        },
                        'end': {
                            'dateTime': deadline_dt.isoformat(),
                            'timeZone': user_timezone,
                        },
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'popup', 'minutes': min_before}
                                for min_before in reminder_prefs.get('default_reminders', [1440, 60])
                            ],
                        },
                        'colorId': '11',  # Red for urgent deadlines
                    }
                    
                    # Create event in Google Calendar
                    event = calendar_service.events().insert(
                        calendarId='primary',
                        body=event_body
                    ).execute()
                    
                    created_events.append({
                        "event_id": event['id'],
                        "email_id": email_id,
                        "title": subject,
                        "start_time": deadline_dt.isoformat(),
                        "calendar_link": event.get('htmlLink'),
                        "status": "synced_to_google_calendar"
                    })
                    
                    print(f"✅ Created Google Calendar event: {subject}")
                    print(f"   📍 Event ID: {event['id']}")
                    print(f"   🔗 Link: {event.get('htmlLink')}")
                    
                except Exception as e:
                    print(f"❌ Failed to create event for {email.get('subject')}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_events.append({"email_id": email_id, "error": str(e)})
            
            print(f"\n📊 Calendar Sync Summary:")
            print(f"   ✅ Created: {len(created_events)}")
            print(f"   🔄 Duplicates: {len(duplicate_events)}")
            print(f"   ❌ Failed: {len(failed_events)}")
            print(f"   ⏭️ Skipped: {len(skipped_events)}")
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "created_events": created_events,
                "duplicate_events": duplicate_events,
                "summary": {
                    "total_events_created": len(created_events),
                    "duplicate_events": len(duplicate_events),
                    "failed_events": len(failed_events),
                    "skipped_events": len(skipped_events),
                    "synced_to_google_calendar": True
                }
            })
            
        except FileNotFoundError:
            # Fallback if no calendar credentials
            print("⚠️ No calendar credentials found - returning mock data")
            created_events = []
            for email in emails:
                if email.get('deadline', {}).get('has_deadline'):
                    created_events.append({
                        "event_id": f"cal_event_{email.get('email_id')}",
                        "email_id": email.get('email_id'),
                        "title": email.get('subject'),
                        "start_time": email['deadline'].get('date'),
                        "status": "created_locally_only"
                    })
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "created_events": created_events,
                "summary": {
                    "total_events_created": len(created_events),
                    "failed_events": 0,
                    "synced_to_google_calendar": False,
                    "note": "Calendar credentials not found - events created locally only"
                }
            })
        
    except Exception as e:
        print(f"❌ Error creating calendar reminders: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/calendar/reminders/<event_id>', methods=['DELETE', 'OPTIONS'])
def delete_calendar_reminder(event_id):
    """
    Delete a calendar reminder from Google Calendar and backend state.
    Handles CORS preflight OPTIONS requests properly.
    
    Path parameter:
    - event_id: Google Calendar event ID
    
    Query parameter:
    - user_id: User identifier
    """
    # ✅ Handle CORS preflight first
    if request.method == 'OPTIONS':
        print(f"✓ OPTIONS preflight for event_id: {event_id}")
        response = jsonify({"status": "CORS preflight OK"})
        response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 204
    
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from googleapiclient.errors import HttpError
        
        user_id = request.args.get('user_id')
        print(f"🗑️  DELETE request - event_id: {event_id}, user_id: {user_id}")
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        if not event_id:
            return jsonify({
                "success": False,
                "error": "event_id is required"
            }), 400
        
        # Load calendar credentials from session (Vercel-compatible)
        try:
            credentials = get_credentials_from_session()
            if not credentials:
                print("⚠️ No credentials in session - cannot delete calendar event")
                return jsonify({
                    "success": False,
                    "error": "Session expired. Please sign in again to manage calendar events."
                }), 200
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                session['credentials']['token'] = credentials.token
            
            # Build Calendar API service
            calendar_service = build('calendar', 'v3', credentials=credentials)
            
            # Try deleting the event from Google Calendar
            try:
                calendar_service.events().delete(
                    calendarId='primary',
                    eventId=event_id
                ).execute()
                
                print(f"✅ Deleted calendar event: {event_id}")
                
                return jsonify({
                    "success": True,
                    "message": "Reminder deleted successfully from Google Calendar",
                    "event_id": event_id
                }), 200
                
            except HttpError as e:
                if e.resp.status == 404:
                    # Event already deleted or not found
                    print(f"⚠️ Event not found in Google Calendar: {event_id}")
                    return jsonify({
                        "success": True,
                        "message": "Event not found (already deleted)",
                        "event_id": event_id
                    }), 200
                else:
                    raise e
        
        except FileNotFoundError:
            print("⚠️ No calendar credentials found - cannot delete remotely")
            return jsonify({
                "success": False,
                "error": "Calendar credentials not found",
                "note": "Event not deleted remotely, may still exist in UI"
            }), 404
        
    except Exception as e:
        print(f"❌ Error deleting event: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/calendar/upcoming', methods=['GET'])
def get_upcoming_reminders():
    """
    Get upcoming job deadline reminders for a user
    
    Query parameters:
    - user_id: User identifier
    - days_ahead: Number of days to look ahead (default: 30)
    """
    try:
        user_id = request.args.get('user_id')
        days_ahead = int(request.args.get('days_ahead', 90))  # Increased to 90 days
        access_token = request.args.get('access_token')  # Get access token from query params
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        print(f"📅 Fetching upcoming events for user: {user_id}")
        print(f"🔍 Session credentials available: {session.get('credentials') is not None}")
        print(f"🔑 Access token provided: {bool(access_token)}")
        
        # Fetch real upcoming events from Google Calendar
        try:
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            credentials = get_credentials_from_session()
            
            # If no session credentials, try to use access token from request
            if not credentials and access_token:
                print(f"🔑 No session credentials, using access token from request")
                try:
                    # Reconstruct credentials from access token
                    from google.oauth2.credentials import Credentials
                    credentials = Credentials(
                        token=access_token,
                        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                        token_uri='https://oauth2.googleapis.com/token',
                        scopes=SCOPES
                    )
                    print(f"✅ Reconstructed credentials from access token")
                except Exception as e:
                    print(f"❌ Failed to reconstruct credentials: {e}")
                    credentials = None
            
            if not credentials:
                print("⚠️ No credentials available - returning empty events list")
                # Return empty list instead of 401 (session expired on Vercel)
                return jsonify({
                    "success": True,
                    "upcoming_events": [],
                    "total_count": 0,
                    "note": "Please sign in again to sync with Google Calendar"
                }), 200
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                session['credentials']['token'] = credentials.token
            
            # Build Calendar API service
            calendar_service = build('calendar', 'v3', credentials=credentials)
            
            # Get events from Google Calendar
            from datetime import datetime, timedelta
            now = datetime.utcnow().isoformat() + 'Z'
            end_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_date,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            upcoming_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                # Calculate days until deadline
                try:
                    event_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    days_until = (event_date - datetime.now()).days
                    
                    # Skip past events (additional safety check)
                    if days_until < 0:
                        continue
                except:
                    days_until = 0
                
                # Determine urgency based on days until
                if days_until <= 3:
                    urgency = "high"
                elif days_until <= 7:
                    urgency = "medium"
                else:
                    urgency = "low"
                
                # Parse deadline type from title if present
                title_lower = event.get('summary', '').lower()
                if 'interview' in title_lower:
                    deadline_type = 'interview'
                elif 'assessment' in title_lower or 'coding' in title_lower:
                    deadline_type = 'assessment'
                elif 'application' in title_lower:
                    deadline_type = 'application'
                else:
                    deadline_type = 'other'
                
                upcoming_events.append({
                    "event_id": event['id'],
                    "title": event.get('summary', 'No Title'),
                    "start_time": start,
                    "deadline_type": deadline_type,
                    "urgency": urgency,
                    "days_until": days_until,
                    "calendar_link": event.get('htmlLink'),
                    "description": event.get('description', '')
                })
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "query_parameters": {
                    "days_ahead": days_ahead
                },
                "upcoming_events": upcoming_events,
                "summary": {
                    "total_events": len(upcoming_events),
                    "high_urgency": sum(1 for e in upcoming_events if e.get('days_until', 999) <= 3),
                    "medium_urgency": sum(1 for e in upcoming_events if 3 < e.get('days_until', 999) <= 7),
                    "low_urgency": sum(1 for e in upcoming_events if e.get('days_until', 999) > 7)
                }
            })
            
        except FileNotFoundError:
            # No calendar credentials - return empty list
            return jsonify({
                "success": True,
                "user_id": user_id,
                "upcoming_events": [],
                "summary": {
                    "total_events": 0,
                    "high_urgency": 0,
                    "medium_urgency": 0,
                    "low_urgency": 0
                },
                "note": "Calendar credentials not found"
            })
        except Exception as e:
            print(f"❌ Error fetching calendar events: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to fetch calendar events: {str(e)}"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    """
    Send notification to user about upcoming deadlines
    
    Expected payload:
    {
        "user_id": "unique_user_id",
        "notification_type": "deadline_reminder|new_opportunities|daily_digest",
        "message": "Custom notification message",
        "event_id": "optional_calendar_event_id",
        "channels": ["push", "email", "sms"]
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        notification_type = data.get('notification_type')
        message = data.get('message')
        event_id = data.get('event_id')
        channels = data.get('channels', ['push'])
        
        if not user_id or not notification_type:
            return jsonify({
                "success": False,
                "error": "user_id and notification_type are required"
            }), 400
        
        # Simulate notification sending
        sent_notifications = []
        for channel in channels:
            notification_result = {
                "channel": channel,
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "notification_id": f"notif_{user_id}_{len(sent_notifications)}"
            }
            sent_notifications.append(notification_result)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "notification_type": notification_type,
            "message": message,
            "event_id": event_id,
            "sent_notifications": sent_notifications,
            "summary": {
                "total_sent": len(sent_notifications),
                "channels_used": channels
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """
    Get analytics data for user dashboard
    
    Query parameters:
    - user_id: User identifier
    - period: time period (week|month|quarter|year)
    """
    try:
        user_id = request.args.get('user_id')
        period = request.args.get('period', 'month')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # TODO: Implement analytics data collection
        analytics_data = {
            "placeholder": "Analytics implementation pending"
        }
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "analytics": analytics_data,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

def _is_future_deadline(deadline_date: str) -> bool:
    """Check if deadline is today or in the future"""
    if not deadline_date:
        return False
    try:
        deadline = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
        return deadline.date() >= datetime.now().date()
    except Exception as e:
        print(f"⚠️ Error checking deadline date: {e}")
        return False

def _get_existing_calendar_events():
    """Load all existing 'Job Deadline' events from Google Calendar to detect duplicates"""
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from datetime import timedelta
    
    try:
        # Load calendar credentials from session (Vercel-compatible)
        credentials = get_credentials_from_session()
        if not credentials:
            print("⚠️ No credentials in session - skipping duplicate check")
            return set()
        
        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        
        # Build Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Query for existing events in the next year
        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=365)).isoformat() + 'Z'
        
        results = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime',
            q='Job Deadline'  # Search for events with this text
        ).execute()
        
        # Extract and normalize event summaries for comparison
        existing_titles = set()
        for event in results.get('items', []):
            summary = event.get('summary', '')
            if summary:
                existing_titles.add(summary.strip().lower())
        
        print(f"📅 Found {len(existing_titles)} existing calendar events")
        return existing_titles
        
    except FileNotFoundError:
        print("⚠️ calendar_token.json not found - skipping duplicate check")
        return set()
    except Exception as e:
        print(f"⚠️ Calendar duplicate check failed: {e}")
        return set()

def _calculate_urgency_days(deadline_date):
    """Calculate days until deadline for urgency calculation"""
    if not deadline_date:
        return None
    try:
        deadline = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
        now = datetime.now()
        delta = deadline - now
        return max(0, delta.days)
    except:
        return None

if __name__ == '__main__':
    # Initialize the email system
    if init_system():
        print("🚀 Email Reminder API Service Starting...")
        print("📧 AutoGen Multi-Agent System Ready")
        print("🔗 API Endpoints Available:")
        print("   • POST /api/emails/scan - Scan and process emails")
        print("   • POST /api/calendar/reminders - Create calendar reminders")
        print("   • GET  /api/calendar/upcoming - Get upcoming deadlines")
        print("   • POST /api/notifications/send - Send notifications")
        print("   • GET  /api/analytics/dashboard - Get analytics data")
        print("=" * 50)
        
        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        )
    else:
        print("❌ Failed to initialize email system")
        exit(1)