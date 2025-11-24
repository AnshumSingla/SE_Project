"""
Client Example - How your web/mobile app would interact with the API service

This demonstrates the proper integration flow for your application.
"""

import requests
import json
from datetime import datetime

class EmailReminderAPIClient:
    """Client class for interacting with the Email Reminder API"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        """Check if the API service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def setup_user_oauth(self, user_id: str, oauth_data: dict):
        """Setup user credentials after OAuth flow"""
        payload = {
            "user_id": user_id,
            "gmail_credentials": oauth_data.get("gmail_credentials"),
            "calendar_credentials": oauth_data.get("calendar_credentials")
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/setup",
                json=payload
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def scan_user_emails(self, user_id: str, max_emails=50, days_back=7, search_query=""):
        """Scan user's emails for job opportunities"""
        payload = {
            "user_id": user_id,
            "max_emails": max_emails,
            "days_back": days_back,
            "search_query": search_query
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/emails/scan",
                json=payload
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_calendar_reminders(self, user_id: str, email_ids: list, reminder_preferences=None):
        """Create calendar reminders for selected emails"""
        payload = {
            "user_id": user_id,
            "email_ids": email_ids,
            "reminder_preferences": reminder_preferences or {
                "default_reminders": [1440, 60],  # 1 day, 1 hour
                "urgent_reminders": [10080, 1440, 60]  # 1 week, 1 day, 1 hour
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/calendar/reminders",
                json=payload
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_upcoming_deadlines(self, user_id: str, days_ahead=30):
        """Get upcoming deadlines for user"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/calendar/upcoming",
                params={"user_id": user_id, "days_ahead": days_ahead}
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_notification(self, user_id: str, notification_type: str, message: str, channels=None):
        """Send notification to user"""
        payload = {
            "user_id": user_id,
            "notification_type": notification_type,
            "message": message,
            "channels": channels or ["push"]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/notifications/send",
                json=payload
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_dashboard_analytics(self, user_id: str, period="month"):
        """Get analytics for user dashboard"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/analytics/dashboard",
                params={"user_id": user_id, "period": period}
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

def demo_integration_flow():
    """Demonstrate the complete integration flow"""
    print("🔗 Email Reminder API Client Demo")
    print("=" * 50)
    
    # Initialize client
    client = EmailReminderAPIClient()
    
    # Test API health
    print("🏥 Checking API health...")
    health = client.health_check()
    print(f"   Status: {health}")
    
    # Simulate user OAuth setup
    user_id = "demo_user_12345"
    print(f"\n👤 Setting up user: {user_id}")
    
    oauth_result = client.setup_user_oauth(user_id, {
        "gmail_credentials": "base64_encoded_gmail_creds",
        "calendar_credentials": "base64_encoded_calendar_creds"
    })
    print(f"   Setup result: {oauth_result.get('success', False)}")
    
    # Scan emails
    print(f"\n📧 Scanning emails for user...")
    scan_result = client.scan_user_emails(
        user_id=user_id,
        max_emails=20,
        days_back=7
    )
    
    if scan_result.get("success"):
        summary = scan_result.get("summary", {})
        emails = scan_result.get("emails", [])
        
        print(f"   ✅ Scan completed:")
        print(f"      • Total emails: {summary.get('total_emails', 0)}")
        print(f"      • Job-related: {summary.get('job_related_emails', 0)}")
        print(f"      • With deadlines: {summary.get('emails_with_deadlines', 0)}")
        
        # Show sample results
        job_emails = [e for e in emails if e['classification']['is_job_related']]
        if job_emails:
            print(f"\n📋 Sample job-related emails:")
            for i, email in enumerate(job_emails[:3], 1):
                print(f"      {i}. {email['subject'][:50]}...")
                print(f"         Category: {email['classification']['category']}")
                print(f"         Urgency: {email['classification']['urgency']}")
                if email['deadline']['has_deadline']:
                    print(f"         Deadline: {email['deadline']['date']} {email['deadline']['time'] or ''}")
        
        # Create calendar reminders for emails with deadlines
        deadline_emails = [e['email_id'] for e in emails if e['deadline']['has_deadline']]
        if deadline_emails:
            print(f"\n📅 Creating calendar reminders...")
            calendar_result = client.create_calendar_reminders(
                user_id=user_id,
                email_ids=deadline_emails[:3]  # Create for first 3
            )
            
            if calendar_result.get("success"):
                created_count = calendar_result.get("summary", {}).get("total_events_created", 0)
                print(f"   ✅ Created {created_count} calendar events")
    
    # Get upcoming deadlines
    print(f"\n⏰ Getting upcoming deadlines...")
    upcoming_result = client.get_upcoming_deadlines(user_id, days_ahead=30)
    
    if upcoming_result.get("success"):
        events = upcoming_result.get("upcoming_events", [])
        print(f"   ✅ Found {len(events)} upcoming deadlines:")
        
        for event in events[:3]:  # Show first 3
            print(f"      • {event['title'][:60]}...")
            print(f"        Date: {event['start_time']}")
            print(f"        Days until: {event['days_until']}")
    
    # Send sample notification
    print(f"\n🔔 Sending notification...")
    notification_result = client.send_notification(
        user_id=user_id,
        notification_type="deadline_reminder",
        message="You have a job application deadline in 24 hours!",
        channels=["push", "email"]
    )
    
    if notification_result.get("success"):
        sent_count = notification_result.get("summary", {}).get("total_sent", 0)
        print(f"   ✅ Sent {sent_count} notifications")
    
    # Get dashboard analytics
    print(f"\n📊 Getting dashboard analytics...")
    analytics_result = client.get_dashboard_analytics(user_id, period="month")
    
    if analytics_result.get("success"):
        analytics = analytics_result.get("analytics", {})
        job_stats = analytics.get("job_application_stats", {})
        
        print(f"   ✅ Analytics summary:")
        print(f"      • Opportunities found: {job_stats.get('total_opportunities_found', 0)}")
        print(f"      • Applications submitted: {job_stats.get('applications_submitted', 0)}")
        print(f"      • Interviews scheduled: {job_stats.get('interviews_scheduled', 0)}")
        print(f"      • Response rate: {job_stats.get('response_rate', 0):.1f}%")
    
    print(f"\n🎉 Integration demo completed!")

if __name__ == "__main__":
    demo_integration_flow()