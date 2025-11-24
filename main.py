import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
import autogen
from email import message_from_string
import base64

# Load environment variables
load_dotenv()

class EmailReminderSystem:
    def __init__(self):
        self.setup_llm_config()
        self.setup_agents()
        
    def setup_llm_config(self):
        """Configure LLM for AutoGen agents"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set. Put it in a .env file or env var.")
        
        self.llm_config = {
            "config_list": [
                {
                    "model": "gpt-4o-mini",  # Using a reliable model
                    "api_key": api_key,
                }
            ],
            "temperature": 0.0,
        }

    def setup_agents(self):
        """Initialize all AutoGen agents for the pipeline"""
        
        # User Proxy Agent - coordinates the workflow
        self.user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            max_consecutive_auto_reply=0
        )

        # Gmail Scanner Agent - handles email retrieval
        self.gmail_agent = autogen.AssistantAgent(
            name="GmailAgent",
            llm_config=self.llm_config,
            system_message=(
                "You are a Gmail integration specialist. Your role is to help retrieve and process Gmail messages. "
                "You understand Gmail API responses and can extract relevant email data including sender, subject, "
                "body content, and timestamps. You work with email data in JSON format."
            ),
        )

        # Email Classifier Agent - determines if emails are job-related
        self.classifier_agent = autogen.AssistantAgent(
            name="EmailClassifier",
            llm_config=self.llm_config,
            system_message=(
                "You are an expert email classifier specializing in job and career opportunities. "
                "Analyze emails and determine if they are job/career related. Look for:"
                "- Job postings, internship opportunities, application deadlines"
                "- Interview invitations, assessment deadlines"
                "- Career fair announcements, networking events"
                "- Scholarship or fellowship applications"
                "- Conference submission deadlines related to career development"
                "- University program applications"
                "\n"
                "You MUST respond ONLY in JSON format:"
                "{\n"
                '  "is_job_related": true/false,\n'
                '  "reason": "brief explanation",\n'
                '  "category": "job_posting|interview|assessment|deadline|application|event|other",\n'
                '  "urgency": "high|medium|low"\n'
                "}"
            ),
        )

        # Deadline Extractor Agent - finds specific dates and deadlines
        self.deadline_agent = autogen.AssistantAgent(
            name="DeadlineExtractor",
            llm_config=self.llm_config,
            system_message=(
                "You are a deadline extraction specialist. Your job is to find specific dates, "
                "deadlines, and time-sensitive information from emails. Look for:"
                "- Application deadlines (exact dates and times)"
                "- Interview schedules"
                "- Assessment submission dates"
                "- Event dates and registration deadlines"
                "- Follow-up dates and response requirements"
                "\n"
                "You MUST respond ONLY in JSON format:"
                "{\n"
                '  "has_deadline": true/false,\n'
                '  "deadline_date": "YYYY-MM-DD" or null,\n'
                '  "deadline_time": "HH:MM" or null,\n'
                '  "timezone": "timezone if specified" or null,\n'
                '  "deadline_text": "exact text from email containing the deadline",\n'
                '  "deadline_type": "application|interview|assessment|response|event|other",\n'
                '  "description": "brief description of what the deadline is for"\n'
                "}"
            ),
        )

        # Calendar Agent - handles Google Calendar integration
        self.calendar_agent = autogen.AssistantAgent(
            name="CalendarAgent",
            llm_config=self.llm_config,
            system_message=(
                "You are a Google Calendar integration specialist. You help create calendar events "
                "and reminders based on email deadlines and job opportunities. You understand:"
                "- How to structure calendar event data"
                "- Setting appropriate reminder times for different types of deadlines"
                "- Creating clear, actionable event titles and descriptions"
                "- Handling timezone conversions when needed"
                "\n"
                "You format calendar events as JSON with proper Google Calendar API structure."
            ),
        )

    def analyze_email(self, email_data: Dict) -> Dict:
        """
        Analyze a single email through the agent pipeline
        
        Args:
            email_data: Dictionary with email information (subject, body, sender, date)
            
        Returns:
            Dictionary with analysis results and calendar event data
        """
        
        # Step 1: Classify if email is job-related
        email_text = f"""
        Subject: {email_data.get('subject', '')}
        From: {email_data.get('sender', '')}
        Date: {email_data.get('date', '')}
        
        Body:
        {email_data.get('body', '')}
        """
        
        print(f"🔍 Analyzing email: {email_data.get('subject', 'No Subject')}")
        
        # Classification
        classification_response = self.user_proxy.initiate_chat(
            self.classifier_agent,
            message=f"Classify this email for job relevance:\n\n{email_text}",
            silent=True
        )
        
        try:
            # Extract JSON from the response
            classification_text = classification_response.chat_history[-1]['content']
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', classification_text, re.DOTALL)
            if json_match:
                classification = json.loads(json_match.group())
            else:
                classification = {"is_job_related": False, "reason": "Could not parse classification"}
        except (json.JSONDecodeError, KeyError, IndexError):
            classification = {"is_job_related": False, "reason": "Classification failed"}
        
        result = {
            "email_data": email_data,
            "classification": classification,
            "deadline_info": None,
            "calendar_event": None
        }
        
        # Step 2: Extract deadlines if job-related
        if classification.get("is_job_related", False):
            print("📅 Extracting deadlines...")
            
            deadline_response = self.user_proxy.initiate_chat(
                self.deadline_agent,
                message=f"Extract deadlines from this job-related email:\n\n{email_text}",
                silent=True
            )
            
            try:
                deadline_text = deadline_response.chat_history[-1]['content']
                json_match = re.search(r'\{.*\}', deadline_text, re.DOTALL)
                if json_match:
                    deadline_info = json.loads(json_match.group())
                    result["deadline_info"] = deadline_info
                    
                    # Step 3: Create calendar event if deadline found
                    if deadline_info.get("has_deadline", False):
                        print("📝 Creating calendar event...")
                        
                        calendar_response = self.user_proxy.initiate_chat(
                            self.calendar_agent,
                            message=f"""Create a Google Calendar reminder for this deadline:
                            
Email Subject: {email_data.get('subject', '')}
Deadline Info: {json.dumps(deadline_info, indent=2)}

Create a calendar event JSON with:
- Appropriate title
- Description with email context
- Reminder settings (suggest 1 day and 1 hour before)
- Event time set for the deadline
""",
                            silent=True
                        )
                        
                        try:
                            calendar_text = calendar_response.chat_history[-1]['content']
                            # This would contain the calendar event structure
                            result["calendar_event"] = calendar_text
                        except (KeyError, IndexError):
                            result["calendar_event"] = "Failed to create calendar event"
            except (json.JSONDecodeError, KeyError, IndexError):
                result["deadline_info"] = {"has_deadline": False, "error": "Deadline extraction failed"}
        
        return result

    def process_sample_emails(self):
        """Process sample emails to test the system"""
        sample_emails = [
            {
                "subject": "Software Engineering Internship - Application Deadline Reminder",
                "sender": "careers@techcorp.com",
                "date": "2025-11-25",
                "body": """
Dear Student,

This is a reminder that the application deadline for our Summer 2025 Software Engineering Internship program is approaching.

Application Deadline: December 15, 2025 at 11:59 PM PST

Please submit your application, including resume, cover letter, and transcript through our careers portal.

Best regards,
TechCorp Recruitment Team
"""
            },
            {
                "subject": "Interview Invitation - Data Science Role",
                "sender": "hr@datacompany.com", 
                "date": "2025-11-25",
                "body": """
Hi there,

We were impressed with your application for the Data Science position. We would like to invite you for an interview.

Please confirm your availability for December 3, 2025 at 2:00 PM EST for a virtual interview.

Please respond by November 30, 2025.

Looking forward to hearing from you!

Best,
HR Team
"""
            },
            {
                "subject": "Pizza Party This Weekend!",
                "sender": "friend@email.com",
                "date": "2025-11-25", 
                "body": """
Hey! Want to join us for pizza this Saturday? Let me know!
"""
            }
        ]
        
        print("🚀 Starting Email Reminder System Analysis...\n")
        
        results = []
        for email in sample_emails:
            result = self.analyze_email(email)
            results.append(result)
            
            # Print summary
            print(f"\n📧 Email: {email['subject']}")
            print(f"🎯 Job Related: {result['classification'].get('is_job_related', False)}")
            
            if result['deadline_info'] and result['deadline_info'].get('has_deadline'):
                deadline = result['deadline_info']
                print(f"⏰ Deadline: {deadline.get('deadline_date')} {deadline.get('deadline_time', '')}")
                print(f"📝 Type: {deadline.get('deadline_type', 'Unknown')}")
                
                if result['calendar_event']:
                    print("✅ Calendar event created")
            
            print("-" * 50)
            
        return results

def main():
    """Main function to run the email reminder system"""
    try:
        # Initialize the system
        system = EmailReminderSystem()
        
        # Process sample emails
        results = system.process_sample_emails()
        
        print(f"\n🎉 Analysis Complete! Processed {len(results)} emails.")
        
        # Count job-related emails
        job_related_count = sum(1 for r in results if r['classification'].get('is_job_related', False))
        deadline_count = sum(1 for r in results if r.get('deadline_info', {}).get('has_deadline', False))
        
        print(f"📊 Summary:")
        print(f"   - Job-related emails: {job_related_count}")
        print(f"   - Emails with deadlines: {deadline_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
