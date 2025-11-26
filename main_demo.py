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

def main():
    """Main function - Use complete_system.py instead for production"""
    print("🤖 Email Reminder System - Rule-Based Module")
    print("📝 Note: This is a utility module for the rule-based email analyzer.")
    print("=" * 60)
    print("\n⚠️  For full system functionality, please use complete_system.py")
    print("    which integrates with Gmail and Google Calendar APIs.\n")
    print("✨ Features available in complete_system.py:")
    print("   1. Real Gmail integration for email scanning")
    print("   2. Google Calendar API for automatic reminder creation")
    print("   3. Rule-based email classification and deadline extraction")
    print("   4. Cross-device synchronization via Google Calendar")

if __name__ == "__main__":
    main()