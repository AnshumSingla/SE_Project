import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import dateutil.parser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailReminderSystem:
    def __init__(self):
        self.job_keywords = [
            # Job/Career keywords
            'job', 'career', 'position', 'role', 'internship', 'fellowship',
            'application', 'apply', 'hiring', 'recruitment', 'interview',
            'assessment', 'coding challenge', 'technical interview',
            'opportunity', 'opening', 'vacancy', 'employment',
            
            # Deadline keywords  
            'deadline', 'due', 'expires', 'closing date', 'last date',
            'application due', 'submit by', 'deadline:', 'due date',
            
            # Company/Organization indicators
            'hr@', 'careers@', 'recruitment@', 'jobs@', 'hiring@',
            'noreply@company', '.edu', 'university', 'college'
        ]
        
        self.deadline_patterns = [
            # Date patterns
            r'(?:deadline|due|expires|closing date|last date|submit by|by)\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
            
            # Time patterns
            r'at\s+(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))',
            r'(\d{1,2}:\d{2})\s*(?:est|pst|cst|mst|utc|gmt)',
            r'by\s+(\d{1,2}:\d{2})'
        ]

    def classify_email_rule_based(self, email_data: Dict) -> Dict:
        """
        Classify email using rule-based approach (no LLM needed)
        """
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('sender', '').lower()
        
        # Combine all text for analysis
        all_text = f"{subject} {body} {sender}"
        
        # Check for job-related keywords
        job_score = 0
        matched_keywords = []
        
        for keyword in self.job_keywords:
            if keyword.lower() in all_text:
                job_score += 1
                matched_keywords.append(keyword)
        
        # Determine if job-related based on score and context
        is_job_related = False
        category = "other"
        urgency = "low"
        
        if job_score >= 2:  # At least 2 keywords match
            is_job_related = True
            
            # Determine category
            if any(word in all_text for word in ['interview', 'interview invitation']):
                category = "interview"
                urgency = "high"
            elif any(word in all_text for word in ['deadline', 'due', 'application']):
                category = "application"
                urgency = "medium"
            elif any(word in all_text for word in ['assessment', 'coding challenge', 'test']):
                category = "assessment"
                urgency = "high"
            else:
                category = "job_posting"
                urgency = "medium"
        
        # Check sender domain for additional signals
        if any(domain in sender for domain in ['careers@', 'hr@', 'recruitment@', 'jobs@']):
            is_job_related = True
            if urgency == "low":
                urgency = "medium"
        
        return {
            "is_job_related": is_job_related,
            "reason": f"Matched keywords: {', '.join(matched_keywords[:3])}" if matched_keywords else "No job keywords found",
            "category": category,
            "urgency": urgency,
            "matched_keywords": matched_keywords
        }

    def extract_deadlines_rule_based(self, email_data: Dict) -> Dict:
        """
        Extract deadlines using rule-based approach (no LLM needed)
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        all_text = f"{subject} {body}"
        
        found_dates = []
        found_times = []
        deadline_texts = []
        
        # Search for deadline patterns
        for pattern in self.deadline_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if match:
                    try:
                        # Try to parse the date
                        parsed_date = dateutil.parser.parse(match, fuzzy=True)
                        found_dates.append({
                            'text': match,
                            'parsed': parsed_date,
                            'date_str': parsed_date.strftime('%Y-%m-%d'),
                            'time_str': parsed_date.strftime('%H:%M') if parsed_date.hour != 0 or parsed_date.minute != 0 else None
                        })
                        deadline_texts.append(match)
                    except:
                        # If parsing fails, still capture the text
                        deadline_texts.append(match)
        
        # Additional search for common deadline phrases
        deadline_phrases = [
            r'deadline\s*:?\s*([^.!?\n]+)',
            r'due\s*:?\s*([^.!?\n]+)',
            r'submit\s+by\s*:?\s*([^.!?\n]+)',
            r'application\s+closes?\s*:?\s*([^.!?\n]+)'
        ]
        
        for phrase_pattern in deadline_phrases:
            matches = re.findall(phrase_pattern, all_text, re.IGNORECASE)
            for match in matches:
                deadline_texts.append(match.strip())
        
        # Determine the most likely deadline
        best_deadline = None
        if found_dates:
            # Sort by date and take the earliest future date
            future_dates = [d for d in found_dates if d['parsed'] > datetime.now()]
            if future_dates:
                best_deadline = min(future_dates, key=lambda x: x['parsed'])
            else:
                # If no future dates, take the most recent past date (might be this year)
                best_deadline = max(found_dates, key=lambda x: x['parsed'])
        
        # Determine deadline type
        deadline_type = "other"
        if any(word in all_text.lower() for word in ['application', 'apply']):
            deadline_type = "application"
        elif any(word in all_text.lower() for word in ['interview', 'meeting']):
            deadline_type = "interview"
        elif any(word in all_text.lower() for word in ['assessment', 'test', 'challenge']):
            deadline_type = "assessment"
        elif any(word in all_text.lower() for word in ['response', 'reply', 'confirm']):
            deadline_type = "response"
        elif any(word in all_text.lower() for word in ['event', 'conference', 'fair']):
            deadline_type = "event"
        
        return {
            "has_deadline": bool(best_deadline or deadline_texts),
            "deadline_date": best_deadline['date_str'] if best_deadline else None,
            "deadline_time": best_deadline['time_str'] if best_deadline else None,
            "timezone": None,  # Would need more sophisticated parsing
            "deadline_text": deadline_texts[0] if deadline_texts else None,
            "deadline_type": deadline_type,
            "description": f"Deadline for {deadline_type}" if best_deadline or deadline_texts else None,
            "all_found_dates": found_dates,
            "all_deadline_texts": deadline_texts
        }

    def create_calendar_event(self, email_data: Dict, deadline_info: Dict) -> Dict:
        """
        Create a structured calendar event
        """
        if not deadline_info.get('has_deadline'):
            return None
            
        # Create event title
        subject = email_data.get('subject', 'Job Deadline Reminder')
        deadline_type = deadline_info.get('deadline_type', 'deadline')
        
        event_title = f"DEADLINE: {subject}"
        if deadline_type != 'other':
            event_title = f"{deadline_type.upper()} DEADLINE: {subject}"
        
        # Create description
        description = f"""
Job Deadline Reminder

Original Email Subject: {email_data.get('subject', '')}
From: {email_data.get('sender', '')}
Deadline Type: {deadline_type}

Deadline Details: {deadline_info.get('deadline_text', 'See original email')}

Action Required: {deadline_info.get('description', 'Check original email for details')}

Original Email Date: {email_data.get('date', '')}
""".strip()

        # Set event date/time
        event_date = deadline_info.get('deadline_date')
        event_time = deadline_info.get('deadline_time', '09:00')  # Default to 9 AM if no time
        
        # Calculate reminder times
        reminders = [
            {'method': 'email', 'minutes': 1440},  # 1 day before
            {'method': 'popup', 'minutes': 60},    # 1 hour before
        ]
        
        # Add extra early reminder for important deadlines
        if deadline_info.get('deadline_type') in ['application', 'assessment']:
            reminders.append({'method': 'email', 'minutes': 10080})  # 1 week before
        
        return {
            'summary': event_title,
            'description': description,
            'start': {
                'date': event_date,
                'timeZone': 'America/New_York'  # Default timezone
            },
            'end': {
                'date': event_date, 
                'timeZone': 'America/New_York'
            },
            'reminders': {
                'useDefault': False,
                'overrides': reminders
            },
            'colorId': '11',  # Red color for deadlines
            'source': {
                'title': 'Email Reminder System',
                'url': f"mailto:{email_data.get('sender', '')}"
            }
        }

    def analyze_email(self, email_data: Dict) -> Dict:
        """
        Analyze a single email through the rule-based pipeline
        """
        print(f"🔍 Analyzing email: {email_data.get('subject', 'No Subject')}")
        
        # Step 1: Classify if email is job-related
        classification = self.classify_email_rule_based(email_data)
        
        result = {
            "email_data": email_data,
            "classification": classification,
            "deadline_info": None,
            "calendar_event": None
        }
        
        # Step 2: Extract deadlines if job-related
        if classification.get("is_job_related", False):
            print("📅 Extracting deadlines...")
            deadline_info = self.extract_deadlines_rule_based(email_data)
            result["deadline_info"] = deadline_info
            
            # Step 3: Create calendar event if deadline found
            if deadline_info.get("has_deadline", False):
                print("📝 Creating calendar event...")
                calendar_event = self.create_calendar_event(email_data, deadline_info)
                result["calendar_event"] = calendar_event
        
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

Requirements:
- Current student in Computer Science or related field
- GPA of 3.0 or higher
- Programming experience in Python, Java, or C++

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

Interview Details:
- Duration: 60 minutes
- Format: Technical interview + behavioral questions
- Platform: Zoom (link will be sent separately)

Please respond by November 30, 2025 to confirm your attendance.

Looking forward to hearing from you!

Best,
HR Team - DataCompany Inc.
"""
            },
            {
                "subject": "Coding Challenge - Software Developer Position",
                "sender": "tech-hiring@startup.io",
                "date": "2025-11-25",
                "body": """
Hello,

Thank you for your interest in the Software Developer position at StartupIO.

Next step: Please complete our coding challenge by December 1, 2025 at 11:59 PM UTC.

Challenge Details:
- Time limit: 3 hours
- Languages: Python, JavaScript, or Java
- Topics: Algorithms, data structures, system design

Access the challenge here: [link]

If you have any questions, please don't hesitate to reach out.

Best of luck!
Tech Team
"""
            },
            {
                "subject": "Pizza Party This Weekend!",
                "sender": "friend@email.com",
                "date": "2025-11-25", 
                "body": """
Hey! Want to join us for pizza this Saturday? Let me know!

We're meeting at Tony's Pizza at 7 PM. Should be fun!
"""
            },
            {
                "subject": "University Graduate Program Application - Final Reminder",
                "sender": "admissions@university.edu",
                "date": "2025-11-25",
                "body": """
Dear Applicant,

This is a final reminder that applications for the Master's in Computer Science program close on December 10, 2025.

Required documents:
- Completed application form
- Official transcripts
- Three letters of recommendation  
- Statement of purpose
- GRE scores (optional for 2025 admissions)

All materials must be submitted through our online portal by 11:59 PM EST on the deadline date.

For questions, contact our admissions office.

Good luck with your application!

Admissions Committee
"""
            }
        ]
        
        print("🚀 Starting Email Reminder System Analysis (Rule-Based Mode)...\n")
        
        results = []
        for email in sample_emails:
            result = self.analyze_email(email)
            results.append(result)
            
            # Print detailed summary
            print(f"\n📧 Email: {email['subject']}")
            print(f"📤 From: {email['sender']}")
            
            classification = result['classification']
            print(f"🎯 Job Related: {classification.get('is_job_related', False)}")
            
            if classification.get('is_job_related'):
                print(f"🏷️  Category: {classification.get('category', 'Unknown')}")
                print(f"⚡ Urgency: {classification.get('urgency', 'Unknown')}")
                print(f"🔍 Keywords: {', '.join(classification.get('matched_keywords', [])[:5])}")
            
            deadline_info = result.get('deadline_info')
            if deadline_info and deadline_info.get('has_deadline'):
                print(f"⏰ Deadline Found: YES")
                print(f"📅 Date: {deadline_info.get('deadline_date', 'Unknown')}")
                if deadline_info.get('deadline_time'):
                    print(f"🕐 Time: {deadline_info.get('deadline_time')}")
                print(f"📝 Type: {deadline_info.get('deadline_type', 'Unknown')}")
                print(f"📋 Text: {deadline_info.get('deadline_text', 'N/A')}")
                
                if result.get('calendar_event'):
                    calendar_event = result['calendar_event']
                    print(f"✅ Calendar Event: '{calendar_event.get('summary', 'Unknown')}'")
                    print(f"🔔 Reminders: {len(calendar_event.get('reminders', {}).get('overrides', []))} alerts set")
            else:
                print(f"⏰ Deadline Found: NO")
            
            print("-" * 70)
            
        return results

def main():
    """Main function to run the email reminder system"""
    try:
        print("🤖 Email Reminder System - Multi-Agent Pipeline")
        print("📝 Note: Running in rule-based mode (no OpenAI API required)")
        print("=" * 60)
        
        # Initialize the system
        system = EmailReminderSystem()
        
        # Process sample emails
        results = system.process_sample_emails()
        
        # Summary statistics
        total_emails = len(results)
        job_related_count = sum(1 for r in results if r['classification'].get('is_job_related', False))
        deadline_count = sum(1 for r in results if r.get('deadline_info') and r['deadline_info'].get('has_deadline', False))
        calendar_events = sum(1 for r in results if r.get('calendar_event') is not None)
        
        print(f"\n🎉 Analysis Complete!")
        print(f"📊 Summary Statistics:")
        print(f"   📧 Total emails processed: {total_emails}")
        print(f"   💼 Job-related emails: {job_related_count}")
        print(f"   ⏰ Emails with deadlines: {deadline_count}")
        print(f"   📅 Calendar events created: {calendar_events}")
        
        # Show breakdown by category
        categories = {}
        urgency_levels = {}
        
        for result in results:
            if result['classification'].get('is_job_related'):
                category = result['classification'].get('category', 'other')
                urgency = result['classification'].get('urgency', 'low')
                
                categories[category] = categories.get(category, 0) + 1
                urgency_levels[urgency] = urgency_levels.get(urgency, 0) + 1
        
        if categories:
            print(f"\n📋 Job Email Categories:")
            for category, count in categories.items():
                print(f"   • {category.title()}: {count}")
                
        if urgency_levels:
            print(f"\n⚡ Urgency Breakdown:")
            for urgency, count in urgency_levels.items():
                print(f"   • {urgency.title()}: {count}")
        
        print(f"\n✨ Next Steps:")
        print(f"   1. Set up OpenAI API key in .env for LLM-powered analysis")
        print(f"   2. Configure Gmail API for real email scanning")  
        print(f"   3. Set up Google Calendar API for automatic reminder creation")
        print(f"   4. Add scheduling/automation for regular email checking")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()