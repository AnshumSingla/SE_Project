"""
API-Only Email Classification Demo

This demonstrates using ONLY the API-based AutoGen LLM approach
for email classification and deadline extraction.
"""

import requests
import json
from datetime import datetime

class APIOnlyEmailProcessor:
    """Client that uses only the API endpoints for processing"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.user_id = "demo_user_api_only"
    
    def health_check(self):
        """Check if API service is running"""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def scan_emails_api_only(self):
        """Scan emails using ONLY the API/LLM method"""
        print("🤖 Using API-Only Method (AutoGen LLM Agents)")
        print("=" * 50)
        
        payload = {
            "user_id": self.user_id,
            "max_emails": 20,
            "days_back": 7,
            "search_query": ""
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/emails/scan",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._display_api_results(data)
            else:
                print(f"❌ API Error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def _display_api_results(self, data):
        """Display results from API processing"""
        if not data.get("success"):
            print(f"❌ Processing failed: {data.get('error')}")
            return
        
        summary = data.get("summary", {})
        emails = data.get("emails", [])
        
        print(f"📊 API Processing Summary:")
        print(f"   • Total emails processed: {summary.get('total_emails', 0)}")
        print(f"   • Job-related emails found: {summary.get('job_related_emails', 0)}")
        print(f"   • Emails with deadlines: {summary.get('emails_with_deadlines', 0)}")
        print(f"   • Scan timestamp: {data.get('scan_timestamp', 'N/A')}")
        print()
        
        job_related_emails = [e for e in emails if e['classification']['is_job_related']]
        
        if job_related_emails:
            print("🎯 JOB-RELATED EMAILS (via API/LLM Classification):")
            print("=" * 60)
            
            for i, email in enumerate(job_related_emails, 1):
                self._display_email_analysis(i, email)
        else:
            print("No job-related emails found in this batch.")
        
        return job_related_emails
    
    def _display_email_analysis(self, index, email):
        """Display detailed API analysis for an email"""
        classification = email.get('classification', {})
        deadline = email.get('deadline', {})
        
        print(f"\n📧 Email {index}:")
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   From: {email.get('sender', 'N/A')}")
        print(f"   Date: {email.get('date', 'N/A')}")
        
        print(f"\n🤖 API/LLM Classification:")
        print(f"   • Job Related: {classification.get('is_job_related', False)}")
        print(f"   • Category: {classification.get('category', 'N/A')}")
        print(f"   • Urgency: {classification.get('urgency', 'N/A')}")
        print(f"   • Confidence: {classification.get('confidence', 0):.1%}")
        print(f"   • AI Reasoning: {classification.get('reasoning', 'N/A')}")
        
        if deadline.get('has_deadline'):
            print(f"\n📅 Deadline Information:")
            print(f"   • Date: {deadline.get('date', 'N/A')}")
            print(f"   • Time: {deadline.get('time', 'N/A')}")
            print(f"   • Type: {deadline.get('type', 'N/A')}")
            print(f"   • Description: {deadline.get('description', 'N/A')}")
            print(f"   • Urgency: {deadline.get('urgency_days', 'N/A')} days remaining")
        else:
            print(f"\n📅 No deadline detected")
        
        print("-" * 60)
    
    def create_calendar_reminders(self, email_ids):
        """Create calendar reminders via API"""
        print(f"\n📅 Creating Calendar Reminders via API...")
        
        payload = {
            "user_id": self.user_id,
            "email_ids": email_ids,
            "reminder_preferences": {
                "default_reminders": [1440, 60],  # 1 day and 1 hour before
                "urgent_reminders": [10080, 1440, 60]  # 1 week, 1 day, 1 hour
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/calendar/reminders",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Created {len(data.get('created_events', []))} calendar events")
                for event in data.get('created_events', []):
                    print(f"   • Event: {event.get('title', 'N/A')}")
                    print(f"     Calendar Link: {event.get('calendar_link', 'N/A')}")
                return data
            else:
                print(f"❌ Failed to create reminders: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_upcoming_deadlines(self):
        """Get upcoming deadlines via API"""
        print(f"\n📋 Getting Upcoming Deadlines via API...")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/calendar/upcoming",
                params={"user_id": self.user_id, "days_ahead": 30}
            )
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('upcoming_events', [])
                
                if events:
                    print(f"📅 Found {len(events)} upcoming deadlines:")
                    for event in events:
                        urgency = event.get('urgency', 'unknown')
                        days_until = event.get('days_until', 'N/A')
                        print(f"   • {event.get('title', 'N/A')}")
                        print(f"     Urgency: {urgency} | Days until: {days_until}")
                        print(f"     From: {event.get('original_email', {}).get('sender', 'N/A')}")
                else:
                    print("No upcoming deadlines found.")
                
                return data
            else:
                print(f"❌ Failed to get upcoming deadlines: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

def main():
    """Run the API-only demo"""
    print("🚀 API-ONLY EMAIL PROCESSING DEMO")
    print("Using AutoGen LLM Agents via REST API")
    print("=" * 50)
    
    processor = APIOnlyEmailProcessor()
    
    # Check API health
    health = processor.health_check()
    print(f"🏥 API Health: {health}")
    
    if health.get("system_ready"):
        print("✅ API service is ready and initialized\n")
        
        # Process emails using API only
        job_emails = processor.scan_emails_api_only()
        
        if job_emails:
            # Create calendar reminders for emails with deadlines
            deadline_emails = [
                email['email_id'] for email in job_emails 
                if email['deadline']['has_deadline']
            ]
            
            if deadline_emails:
                processor.create_calendar_reminders(deadline_emails)
            
            # Get upcoming deadlines
            processor.get_upcoming_deadlines()
        
    else:
        print("❌ API service is not ready. Please start the API service first.")
        print("Run: python api_service.py")

if __name__ == "__main__":
    main()