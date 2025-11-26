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
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

# Enable CORS with credentials
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

# Google OAuth Configuration (Manual - No Authlib!)
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
REDIRECT_URI = 'http://localhost:5000/auth/google/callback'
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

# Global system instance
email_system = None

def init_system():
    """Initialize the email reminder system"""
    global email_system
    try:
        email_system = IntegratedEmailReminderSystem(use_llm=True)
        return True
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return False

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth flow - Manual implementation (no Authlib!)"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
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
        
        # Save credentials to token files
        with open('gmail_token.json', 'w') as f:
            f.write(credentials.to_json())
        with open('calendar_token.json', 'w') as f:
            f.write(credentials.to_json())
        
        # Extract user info
        email = user_info.get('email', '').replace('"', '&quot;')
        name = user_info.get('name', '').replace('"', '&quot;')
        picture = user_info.get('picture', '').replace('"', '&quot;')
        user_id = user_info.get('id', '').replace('"', '&quot;')
        
        print(f"✅ Manual token exchange successful: {email}")
        
        return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Success</title>
            </head>
            <body>
                <h2>✅ Authentication Successful!</h2>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: true,
                            user: {{
                                email: "{email}",
                                name: "{name}",
                                picture: "{picture}",
                                sub: "{user_id}"
                            }},
                            accessToken: "{access_token}"
                        }}, 'http://localhost:3000');
                        setTimeout(() => window.close(), 1000);
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
                        }}, 'http://localhost:3000');
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
        if access_token and access_token != 'demo_token_for_testing':
            print(f"🔑 Real Gmail access token detected (length: {len(access_token)})")
        else:
            print(f"🎭 Using demo/fallback mode")
        
        # Process emails using the system
        if not email_system:
            return jsonify({
                "success": False,
                "error": "Email system not initialized"
            }), 500
        
        # Fetch and process real emails from user's Gmail account
        print(f"📧 Attempting to process emails for user: {user_id}")
        results = email_system.process_user_emails(
            user_id=user_id,
            max_emails=max_emails,
            days_back=days_back,
            search_query=search_query
        )
        print(f"✅ Successfully processed {len(results)} emails from Gmail")
        
        # Format results for API response
        formatted_results = []
        for result in results:
            email_data = result.get('email_data', {})
            classification = result.get('classification', {})
            deadline_info = result.get('deadline_info', {})
            
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
        
        # Calculate summary statistics
        total_emails = len(formatted_results)
        job_related_count = sum(1 for r in formatted_results if r['classification']['is_job_related'])
        deadline_count = sum(1 for r in formatted_results if r['deadline']['has_deadline'])
        
        return jsonify({
            "success": True,
            "scan_timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "summary": {
                "total_emails": total_emails,
                "job_related_emails": job_related_count,
                "emails_with_deadlines": deadline_count,
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
        
        # Load calendar credentials
        try:
            with open('calendar_token.json', 'r') as f:
                creds_data = json.load(f)
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            # Build Calendar API service
            calendar_service = build('calendar', 'v3', credentials=credentials)
            
            created_events = []
            failed_events = []
            
            for email in emails:
                try:
                    email_id = email.get('email_id')
                    subject = email.get('subject', 'Job Deadline')
                    deadline = email.get('deadline', {})
                    
                    if not deadline.get('has_deadline'):
                        continue
                    
                    # Parse deadline date/time (handle timezone properly)
                    deadline_date = deadline.get('date')
                    deadline_time = deadline.get('time', '23:59:00')
                    
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
                    
                except Exception as e:
                    print(f"❌ Failed to create event for {email.get('subject')}: {e}")
                    failed_events.append(email_id)
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "created_events": created_events,
                "summary": {
                    "total_events_created": len(created_events),
                    "failed_events": len(failed_events),
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
        days_ahead = int(request.args.get('days_ahead', 30))
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id is required"
            }), 400
        
        # Fetch real upcoming events from Google Calendar
        try:
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            with open('calendar_token.json', 'r') as f:
                creds_data = json.load(f)
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
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
                orderBy='startTime',
                q='Job Deadline'  # Filter for job deadline events
            ).execute()
            
            events = events_result.get('items', [])
            
            upcoming_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                upcoming_events.append({
                    "event_id": event['id'],
                    "title": event.get('summary', 'No Title'),
                    "start_time": start,
                    "deadline_type": "application",  # Parse from title if needed
                    "urgency": "medium",  # Calculate based on days until
                    "days_until": (datetime.fromisoformat(start.replace('Z', '+00:00')) - datetime.now()).days,
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
        
        # Sample analytics data
        analytics_data = {
            "period": period,
            "job_application_stats": {
                "total_opportunities_found": 15,
                "applications_submitted": 8,
                "interviews_scheduled": 3,
                "assessments_completed": 5,
                "deadlines_missed": 1,
                "response_rate": 53.3
            },
            "email_processing_stats": {
                "total_emails_processed": 240,
                "job_related_emails": 35,
                "job_related_percentage": 14.6,
                "deadlines_extracted": 22,
                "calendar_events_created": 18
            },
            "deadline_management": {
                "upcoming_deadlines": 6,
                "overdue_deadlines": 1,
                "completed_deadlines": 12,
                "average_notice_days": 8.5
            },
            "category_breakdown": {
                "applications": 45,
                "interviews": 20,
                "assessments": 25,
                "networking": 10
            }
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

def _calculate_urgency_days(deadline_date):
    """Calculate days until deadline for urgency calculation"""
    if not deadline_date:
        return None
    try:
        from datetime import datetime
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