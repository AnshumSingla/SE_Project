"""
Google Calendar Integration Module for Email Reminder System

This module handles creating calendar events and reminders.
Requires Google Calendar API credentials setup.
"""

import os
import pickle
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_LIBRARIES_AVAILABLE = True
except ImportError:
    GOOGLE_LIBRARIES_AVAILABLE = False

class CalendarIntegrator:
    """Handles Google Calendar API integration for the email reminder system"""
    
    # Calendar API scopes - read/write access to Calendar
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, credentials_file='calendar_credentials.json', token_file='calendar_token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        
        if not GOOGLE_LIBRARIES_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. Run: "
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
    
    def authenticate(self):
        """Authenticate with Google Calendar API using OAuth2"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Calendar credentials file '{self.credentials_file}' not found. "
                        "Download from Google Cloud Console (same project as Gmail)."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build Calendar service
        self.service = build('calendar', 'v3', credentials=creds)
        return self.service
    
    def create_deadline_reminder(self, email_data: Dict, deadline_info: Dict) -> Optional[Dict]:
        """
        Create a calendar event for a job deadline
        
        Args:
            email_data: Email information dictionary
            deadline_info: Deadline extraction results
            
        Returns:
            Created event dictionary or None if failed
        """
        if not self.service:
            self.authenticate()
        
        if not deadline_info.get('has_deadline'):
            print("   ⚠️ No deadline found, skipping calendar event creation")
            return None
        
        try:
            # Prepare event data
            event_data = self._prepare_event_data(email_data, deadline_info)
            
            # Create the event
            event = self.service.events().insert(
                calendarId='primary',
                body=event_data
            ).execute()
            
            print(f"   ✅ Calendar event created: {event.get('htmlLink', 'No link')}")
            return event
            
        except HttpError as e:
            print(f"   ❌ Error creating calendar event: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Unexpected error creating calendar event: {e}")
            return None
    
    def _prepare_event_data(self, email_data: Dict, deadline_info: Dict) -> Dict:
        """Prepare event data for Google Calendar API"""
        
        # Extract basic info
        subject = email_data.get('subject', 'Job Deadline')
        sender = email_data.get('sender', 'Unknown sender')
        deadline_type = deadline_info.get('deadline_type', 'deadline')
        deadline_date = deadline_info.get('deadline_date')
        deadline_time = deadline_info.get('deadline_time', '09:00')
        
        # Create event title
        title_prefix = {
            'application': '📝 APPLICATION DEADLINE',
            'interview': '🎯 INTERVIEW DEADLINE', 
            'assessment': '💻 ASSESSMENT DEADLINE',
            'response': '✉️ RESPONSE DEADLINE',
            'event': '📅 EVENT DEADLINE'
        }.get(deadline_type, '⏰ DEADLINE')
        
        event_title = f"{title_prefix}: {subject}"
        
        # Create detailed description
        description = self._create_event_description(email_data, deadline_info)
        
        # Handle date/time
        if deadline_date:
            # Parse the deadline date
            try:
                if 'T' in deadline_date:  # ISO format
                    deadline_datetime = datetime.fromisoformat(deadline_date.replace('Z', '+00:00'))
                else:
                    # Parse date and add time
                    date_parts = deadline_date.split('-')
                    if len(date_parts) == 3:
                        year, month, day = map(int, date_parts)
                        
                        # Parse time
                        if deadline_time and ':' in deadline_time:
                            time_parts = deadline_time.split(':')
                            hour = int(time_parts[0])
                            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                            
                            # Handle AM/PM
                            if 'pm' in deadline_time.lower() and hour != 12:
                                hour += 12
                            elif 'am' in deadline_time.lower() and hour == 12:
                                hour = 0
                        else:
                            hour, minute = 9, 0  # Default to 9 AM
                        
                        deadline_datetime = datetime(year, month, day, hour, minute)
                    else:
                        # Fallback to tomorrow 9 AM
                        deadline_datetime = datetime.now() + timedelta(days=1)
                        deadline_datetime = deadline_datetime.replace(hour=9, minute=0, second=0, microsecond=0)
                        
            except Exception as e:
                print(f"   ⚠️ Error parsing deadline date: {e}")
                # Fallback to tomorrow
                deadline_datetime = datetime.now() + timedelta(days=1)
                deadline_datetime = deadline_datetime.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            # No specific date provided, default to tomorrow
            deadline_datetime = datetime.now() + timedelta(days=1)
            deadline_datetime = deadline_datetime.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Format for Google Calendar API
        start_time = deadline_datetime.isoformat() + 'Z'
        end_time = (deadline_datetime + timedelta(hours=1)).isoformat() + 'Z'  # 1-hour event
        
        # Set up reminders based on deadline type
        reminders = self._create_reminders(deadline_type)
        
        # Choose event color (red for urgent deadlines)
        color_id = '11'  # Red for deadlines
        if deadline_type in ['interview', 'assessment']:
            color_id = '11'  # Red for urgent
        elif deadline_type == 'application':
            color_id = '6'   # Orange for applications
        
        # Build event object
        event = {
            'summary': event_title,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/New_York',  # Default timezone
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': reminders,
            },
            'colorId': color_id,
            'source': {
                'title': 'Email Reminder System',
                'url': f"mailto:{sender}"
            },
            # Add email metadata as extended properties
            'extendedProperties': {
                'private': {
                    'email_id': email_data.get('id', ''),
                    'deadline_type': deadline_type,
                    'created_by': 'email_reminder_system',
                    'original_sender': sender
                }
            }
        }
        
        return event
    
    def _create_event_description(self, email_data: Dict, deadline_info: Dict) -> str:
        """Create detailed event description"""
        
        subject = email_data.get('subject', 'No subject')
        sender = email_data.get('sender', 'Unknown sender')
        email_date = email_data.get('date', 'Unknown date')
        deadline_text = deadline_info.get('deadline_text', 'Check email for details')
        deadline_type = deadline_info.get('deadline_type', 'deadline')
        
        description = f"""🤖 Automated Deadline Reminder

📧 ORIGINAL EMAIL:
   Subject: {subject}
   From: {sender}
   Date: {email_date}

⏰ DEADLINE DETAILS:
   Type: {deadline_type.title()}
   Extracted Text: "{deadline_text}"
   
📋 ACTION REQUIRED:
   {self._get_action_text(deadline_type)}

💡 TIPS:
   • Set up your materials in advance
   • Double-check all requirements
   • Submit early to avoid technical issues
   
🔗 QUICK ACTIONS:
   • Reply to original email: mailto:{sender}
   • Mark as completed when done
   
---
Generated by Email Reminder System on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return description
    
    def _get_action_text(self, deadline_type: str) -> str:
        """Get action text based on deadline type"""
        actions = {
            'application': 'Submit your complete application with all required documents',
            'interview': 'Confirm your interview attendance and prepare thoroughly',
            'assessment': 'Complete the coding challenge or assessment test',
            'response': 'Send your response or confirmation as requested',
            'event': 'Register or attend the scheduled event',
            'other': 'Take the required action as specified in the email'
        }
        return actions.get(deadline_type, actions['other'])
    
    def _create_reminders(self, deadline_type: str) -> List[Dict]:
        """Create appropriate reminders based on deadline type"""
        
        # Base reminders for all deadlines
        reminders = [
            {'method': 'popup', 'minutes': 60},    # 1 hour before
            {'method': 'email', 'minutes': 1440},  # 1 day before
        ]
        
        # Additional reminders for important deadline types
        if deadline_type in ['application', 'assessment']:
            reminders.extend([
                {'method': 'email', 'minutes': 10080},  # 1 week before
                {'method': 'popup', 'minutes': 4320},   # 3 days before
            ])
        elif deadline_type == 'interview':
            reminders.extend([
                {'method': 'email', 'minutes': 2880},   # 2 days before
                {'method': 'popup', 'minutes': 180},    # 3 hours before
            ])
        
        return reminders
    
    def get_upcoming_reminders(self, days_ahead=30) -> List[Dict]:
        """Get upcoming job deadline events from calendar"""
        if not self.service:
            self.authenticate()
        
        try:
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Search for events created by this system
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter for reminder system events
            reminder_events = []
            for event in events:
                # Check if created by our system
                extended_props = event.get('extendedProperties', {}).get('private', {})
                if extended_props.get('created_by') == 'email_reminder_system':
                    reminder_events.append({
                        'id': event.get('id'),
                        'title': event.get('summary'),
                        'start_time': event.get('start', {}).get('dateTime'),
                        'deadline_type': extended_props.get('deadline_type'),
                        'original_sender': extended_props.get('original_sender'),
                        'link': event.get('htmlLink')
                    })
            
            return reminder_events
            
        except Exception as e:
            print(f"❌ Error fetching calendar events: {e}")
            return []
    
    def delete_reminder(self, event_id: str) -> bool:
        """Delete a reminder event"""
        if not self.service:
            self.authenticate()
        
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            print(f"✅ Deleted reminder event: {event_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting reminder: {e}")
            return False

# Demo function for testing Calendar integration  
def test_calendar_integration():
    """Test function to verify Calendar API setup"""
    print("🧪 Testing Google Calendar Integration...")
    
    if not GOOGLE_LIBRARIES_AVAILABLE:
        print("❌ Google API libraries not installed")
        print("   Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return
    
    try:
        calendar = CalendarIntegrator()
        
        # Test authentication
        print("🔑 Authenticating with Google Calendar...")
        calendar.authenticate()
        print("✅ Authentication successful")
        
        # Test creating a sample reminder
        print("📅 Creating test reminder...")
        
        sample_email = {
            'subject': 'Test Job Application Deadline',
            'sender': 'test@example.com',
            'date': '2025-11-25',
            'id': 'test123'
        }
        
        sample_deadline = {
            'has_deadline': True,
            'deadline_date': '2025-12-01',
            'deadline_time': '23:59',
            'deadline_type': 'application',
            'deadline_text': 'Application due December 1, 2025'
        }
        
        event = calendar.create_deadline_reminder(sample_email, sample_deadline)
        
        if event:
            print("✅ Test reminder created successfully")
            
            # Test fetching upcoming reminders
            print("📋 Fetching upcoming reminders...")
            upcoming = calendar.get_upcoming_reminders(days_ahead=7)
            print(f"✅ Found {len(upcoming)} upcoming reminders")
            
            # Clean up test event
            if event.get('id'):
                calendar.delete_reminder(event['id'])
                print("🧹 Test event cleaned up")
        
    except Exception as e:
        print(f"❌ Calendar integration test failed: {e}")
        print("   Make sure you have:")
        print("   1. Downloaded credentials.json from Google Cloud Console")
        print("   2. Enabled Google Calendar API for your project")
        print("   3. Configured OAuth consent screen")

if __name__ == "__main__":
    test_calendar_integration()