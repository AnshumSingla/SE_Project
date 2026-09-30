"""
Email Reminder API Service

Flask-based API service that provides endpoints for the web/mobile app
to interact with the AutoGen-based email processing system.
"""

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import urllib.parse
import secrets
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import traceback

# Load environment variables
load_dotenv()

# Import email processing system
from complete_system import IntegratedEmailReminderSystem

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# Session config
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set True in production

# Enable CORS with credentials
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

# Google OAuth Config
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
    """Initialize email reminder system"""
    global email_system
    try:
        email_system = IntegratedEmailReminderSystem(use_llm=True)
        return True
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return False


# ---------------------- AUTH ----------------------

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth flow"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    params = {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent'
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        if request.args.get('state') != session.get('oauth_state'):
            raise Exception("Invalid OAuth state")

        code = request.args.get('code')
        if not code:
            raise Exception("No authorization code provided")

        token_data = {
            'code': code,
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        token_response.raise_for_status()
        token = token_response.json()

        access_token = token['access_token']
        refresh_token = token.get('refresh_token')

        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo = requests.get(GOOGLE_USERINFO_URL, headers=headers).json()

        session['user'] = userinfo
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            scopes=SCOPES
        )

        with open('gmail_token.json', 'w') as f:
            f.write(credentials.to_json())
        with open('calendar_token.json', 'w') as f:
            f.write(credentials.to_json())

        user_info_json = json.dumps(userinfo)
        return f"""
        <script>
            if (window.opener) {{
                window.opener.postMessage({{
                    success: true,
                    user: {user_info_json},
                    accessToken: "{access_token}"
                }}, 'http://localhost:3000');
                setTimeout(() => window.close(), 1000);
            }}
        </script>
        """

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------- API ENDPOINTS ----------------------

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_ready": email_system is not None
    })


@app.route('/api/emails/scan', methods=['POST'])
def scan_emails():
    """Scan user's Gmail for job-related emails"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        max_emails = data.get('max_emails', 50)
        days_back = data.get('days_back', 7)
        search_query = data.get('search_query', '')

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        if not email_system:
            return jsonify({"success": False, "error": "System not initialized"}), 500

        results = email_system.process_user_emails(
            user_id=user_id,
            max_emails=max_emails,
            days_back=days_back,
            search_query=search_query
        )

        formatted_results = []
        for result in results:
            email_data = result.get('email_data', {})
            classification = result.get('classification', {})
            deadline_info = result.get('deadline_info', {})

            entry = {
                "email_id": email_data.get('id'),
                "subject": email_data.get('subject'),
                "sender": email_data.get('sender'),
                "date": email_data.get('date'),
                "snippet": email_data.get('snippet', '')[:200],
                "classification": {
                    "is_job_related": classification.get('is_job_related', False),
                    "category": classification.get('category', ''),
                    "urgency": classification.get('urgency', 'low'),
                    "confidence": classification.get('confidence', 0.8),
                    "reasoning": classification.get('reason', '')
                },
                "deadline": {"has_deadline": False}
            }

            if deadline_info and deadline_info.get('has_deadline'):
                entry["deadline"] = {
                    "has_deadline": True,
                    "date": deadline_info.get('deadline_date'),
                    "time": deadline_info.get('deadline_time'),
                    "type": deadline_info.get('deadline_type'),
                    "description": deadline_info.get('description'),
                    "text": deadline_info.get('deadline_text'),
                    "urgency_days": _calculate_urgency_days(deadline_info.get('deadline_date'))
                }
            
            formatted_results.append(entry)

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
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/calendar/reminders', methods=['POST'])
def create_calendar_reminders():
    """Create reminders in Google Calendar"""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        data = request.get_json()
        user_id = data.get('user_id')
        emails = data.get('emails', [])
        reminder_prefs = data.get('reminder_preferences', {})

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        with open('calendar_token.json', 'r') as f:
            creds_data = json.load(f)
        credentials = Credentials.from_authorized_user_info(creds_data)

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        calendar_service = build('calendar', 'v3', credentials=credentials)
        user_timezone = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Kolkata')

        created_events = []
        failed_events = []
        
        for email in emails:
            try:
                if not email.get('deadline', {}).get('has_deadline'):
                    continue

                subject = email.get('subject', 'Job Deadline')
                deadline = email['deadline']
                deadline_date = deadline['date']
                deadline_time = deadline.get('time')
                
                # Handle None or missing time
                if not deadline_time or deadline_time == 'None':
                    deadline_time = '23:59:00'
                
                deadline_str = f"{deadline_date}T{deadline_time}"
                deadline_dt = datetime.fromisoformat(deadline_str.replace('Z', ''))

                event_body = {
                    'summary': f'📧 Job Deadline: {subject[:100]}',
                    'description': f'{deadline.get("description", "")}\n\nEmail: {email.get("snippet", "")}',
                    'start': {'dateTime': deadline_dt.isoformat(), 'timeZone': user_timezone},
                    'end': {'dateTime': deadline_dt.isoformat(), 'timeZone': user_timezone},
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'popup', 'minutes': m}
                            for m in reminder_prefs.get('default_reminders', [1440, 60])
                        ]
                    },
                    'colorId': '11'
                }

                event = calendar_service.events().insert(
                    calendarId='primary',
                    body=event_body
                ).execute()

                created_events.append({
                    "event_id": event['id'],
                    "email_id": email.get('email_id'),
                    "title": subject,
                    "start_time": deadline_dt.isoformat(),
                    "calendar_link": event.get('htmlLink'),
                    "status": "synced_to_google_calendar"
                })
                
                print(f"✅ Created Google Calendar event: {subject}")
                
            except Exception as e:
                print(f"❌ Failed to create event for {email.get('subject')}: {e}")
                failed_events.append(email.get('email_id'))

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
        return jsonify({
            "success": False,
            "error": "Calendar credentials not found. Please authenticate with Google."
        }), 401
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/calendar/upcoming', methods=['GET'])
def get_upcoming_reminders():
    """Get upcoming Google Calendar job reminders"""
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        user_id = request.args.get('user_id')
        days_ahead = int(request.args.get('days_ahead', 30))

        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400

        with open('calendar_token.json', 'r') as f:
            creds_data = json.load(f)
        credentials = Credentials.from_authorized_user_info(creds_data)

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        service = build('calendar', 'v3', credentials=credentials)
        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime',
            q='Job Deadline'
        ).execute()

        events = events_result.get('items', [])
        
        upcoming_events = []
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date'))
            
            # Calculate days until deadline
            try:
                event_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                days_until = (event_date - datetime.now()).days
            except:
                days_until = 0
            
            # Determine urgency
            if days_until <= 3:
                urgency = "high"
            elif days_until <= 7:
                urgency = "medium"
            else:
                urgency = "low"
            
            # Parse deadline type from title
            title_lower = e.get('summary', '').lower()
            if 'interview' in title_lower:
                deadline_type = 'interview'
            elif 'assessment' in title_lower or 'coding' in title_lower:
                deadline_type = 'assessment'
            elif 'application' in title_lower:
                deadline_type = 'application'
            else:
                deadline_type = 'other'
            
            upcoming_events.append({
                "event_id": e['id'],
                "title": e.get('summary', ''),
                "start_time": start,
                "deadline_type": deadline_type,
                "urgency": urgency,
                "days_until": days_until,
                "calendar_link": e.get('htmlLink', ''),
                "description": e.get('description', '')
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
                "high_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'high'),
                "medium_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'medium'),
                "low_urgency": sum(1 for e in upcoming_events if e['urgency'] == 'low')
            }
        })

    except FileNotFoundError:
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
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------- UTIL ----------------------

def _calculate_urgency_days(deadline_date):
    """Days until deadline"""
    if not deadline_date:
        return None
    try:
        deadline = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
        return max(0, (deadline - datetime.now()).days)
    except:
        return None


# ---------------------- RUN ----------------------

if __name__ == '__main__':
    if init_system():
        print("🚀 Email Reminder API Service Starting...")
        print("📧 Gmail + Google Calendar Integration Ready")
        print("🔗 API Endpoints Available:")
        print("   • POST /api/emails/scan - Scan and process emails")
        print("   • POST /api/calendar/reminders - Create calendar reminders")
        print("   • GET  /api/calendar/upcoming - Get upcoming deadlines")
        print("=" * 50)
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
    else:
        print("❌ Failed to initialize system")
        exit(1)
