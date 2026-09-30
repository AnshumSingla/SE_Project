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
        
        # Track processed email IDs to prevent duplicates
        self.processed_email_ids = set()
        
        self.deadline_patterns = [
            # Date patterns with context
            r'(?:deadline|due|expires|closing date|last date|submit by|by)\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})',
            r'(?:deadline|due|expires|closing date|last date|submit by|by)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:deadline|due|expires|closing date|last date|submit by|by)\s*:?\s*(\d{4}-\d{1,2}-\d{1,2})',
            
            # Standalone date patterns (include abbreviated months)
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            # Full month names
            r'((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4})',
            # Abbreviated month names
            r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{4})',
            
            # Time patterns
            r'at\s+(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))',
            r'(\d{1,2}:\d{2})\s*(?:est|pst|cst|mst|utc|gmt)',
            r'by\s+(\d{1,2}:\d{2})'
        ]

    def _parse_date_safely(self, date_string: str, from_subject: bool = False) -> Optional[datetime]:
        """
        Parse date string and handle year inference intelligently
        
        Args:
            date_string: The date string to parse
            from_subject: If True, apply stricter validation (subject dates often describe positions, not deadlines)
        """
        now = datetime.now()
        
        try:
            # Try to parse the date
            parsed = dateutil.parser.parse(date_string, fuzzy=True, default=datetime(now.year, 1, 1))
            
            # Check if the original string contains an explicit year
            has_year = bool(re.search(r'\b(19|20)\d{2}\b', date_string))
            
            # If the parsed date doesn't have an explicit year
            if not has_year and parsed.year == now.year:
                # Calculate days difference
                days_diff = (parsed.date() - now.date()).days
                days_past = abs(days_diff) if days_diff < 0 else 0
                
                # Only infer next year if date is within 45 days in the past (about 6 weeks)
                # Beyond that, it's likely describing a past event, not a future deadline
                if days_diff < 0 and days_past <= 45:
                    # Try next year
                    try:
                        parsed = parsed.replace(year=now.year + 1)
                        print(f"  ⏭️  Inferred next year for '{date_string}': {parsed.strftime('%Y-%m-%d')}")
                    except ValueError:
                        pass
                elif days_diff < 0 and days_past > 45:
                    # Too far in the past - likely describing old position/event, skip it
                    print(f"  ⏪ Skipping old past date (>{days_past} days ago) '{date_string}': {parsed.strftime('%Y-%m-%d')}")
                    return None
                elif days_diff < 0 and from_subject:
                    # Date is in the past and from subject line - likely describing position, not a deadline
                    print(f"  ⏪ Skipping past date from subject '{date_string}': {parsed.strftime('%Y-%m-%d')}")
                    return None
                elif days_diff == 0 and parsed.hour == 0 and parsed.minute == 0:
                    # Today with no time specified - ambiguous, skip if from subject
                    if from_subject:
                        print(f"  ⏪ Skipping ambiguous today date from subject: '{date_string}'")
                        return None
            
            # Additional validation for subject dates
            if from_subject:
                days_until = (parsed.date() - now.date()).days
                # If date is too far in the future (>6 months) without explicit year, it's suspicious
                if not has_year and days_until > 180:
                    print(f"  ⚠️  Suspicious far-future date from subject without year: '{date_string}' ({days_until} days)")
                    # Still allow it, but log the warning
            
            # Only return if it's a future date (at least tomorrow or later)
            if parsed.date() > now.date():
                return parsed
            elif parsed.date() == now.date() and parsed.hour > now.hour:
                # Allow today if time is explicitly in the future
                return parsed
            else:
                print(f"  ⏪ Skipping past date '{date_string}': {parsed.strftime('%Y-%m-%d %H:%M')}")
                return None
                
        except Exception as e:
            print(f"  ❌ Failed to parse date '{date_string}': {e}")
            return None

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
        Extract deadlines using a rule-based approach with improved date parsing
        Prioritizes dates from body over subject line and filters misleading subject dates
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        all_text = f"{subject} {body}".lower()
        
        print(f"  🔍 Searching for deadlines in: {subject[:50]}...")
        
        # Detect forwarded emails
        is_forwarded = 'fwd:' in subject.lower() or 'fw:' in subject.lower() or 're:' in subject.lower()
        if is_forwarded:
            print(f"  📧 Detected forwarded/replied email - skipping subject dates")
        
        # Separate searches for body and subject to prioritize body
        body_dates = []
        subject_dates = []
        deadline_texts = []
        
        # Search body first (more reliable)
        for pattern in self.deadline_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            for match in matches:
                if not match or len(match.strip()) < 3:
                    continue
                
                print(f"  📅 Found date in BODY: '{match}'")
                parsed_date = self._parse_date_safely(match, from_subject=False)
                
                if parsed_date:
                    body_dates.append({
                        'text': match,
                        'parsed': parsed_date,
                        'date_str': parsed_date.strftime('%Y-%m-%d'),
                        'time_str': parsed_date.strftime('%H:%M') if parsed_date.hour or parsed_date.minute else None,
                        'source': 'body'
                    })
                    deadline_texts.append(match)
                    print(f"  ✅ Parsed as: {parsed_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Check if we have actual date info in body (not just time)
        has_body_date = any(d for d in body_dates if d['parsed'].date() != datetime.now().date())
        
        # Then search subject (less reliable - often describes the position itself)
        # Skip subject dates if email is forwarded OR if meaningful body dates found
        if not has_body_date and not is_forwarded:
            for pattern in self.deadline_patterns:
                matches = re.findall(pattern, subject, re.IGNORECASE)
                for match in matches:
                    if not match or len(match.strip()) < 3:
                        continue
                    
                    print(f"  📅 Found date in SUBJECT: '{match}'")
                    parsed_date = self._parse_date_safely(match, from_subject=True)
                    
                    if parsed_date:
                        subject_dates.append({
                            'text': match,
                            'parsed': parsed_date,
                            'date_str': parsed_date.strftime('%Y-%m-%d'),
                            'time_str': parsed_date.strftime('%H:%M') if parsed_date.hour or parsed_date.minute else None,
                            'source': 'subject'
                        })
                        if match not in deadline_texts:
                            deadline_texts.append(match)
                        print(f"  ✅ Parsed as: {parsed_date.strftime('%Y-%m-%d %H:%M')}")
        elif has_body_date:
            print(f"  ⏭️  Skipping subject line dates (found meaningful date(s) in body)")
        elif is_forwarded:
            print(f"  ⏭️  Skipping subject line dates (forwarded email)")
        
        # Combine, prioritizing body dates
        found_dates = body_dates + subject_dates
        
        # Find the earliest upcoming deadline
        best_deadline = None
        if found_dates:
            # Sort by date
            found_dates.sort(key=lambda x: x['parsed'])
            
            # Prefer dates from body over subject
            body_deadline = next((d for d in found_dates if d['source'] == 'body'), None)
            
            if body_deadline:
                best_deadline = body_deadline
                print(f"  🎯 Selected deadline from BODY: {best_deadline['date_str']}")
            elif found_dates:
                best_deadline = found_dates[0]  # Earliest date from subject
                print(f"  🎯 Selected deadline from SUBJECT: {best_deadline['date_str']}")
        
        # Determine deadline type (only if we have a valid future deadline)
        deadline_type = "other"
        if best_deadline:
            lower_text = all_text.lower()
            if any(word in lower_text for word in ['application', 'apply']):
                deadline_type = "application"
            elif any(word in lower_text for word in ['interview', 'meeting']):
                deadline_type = "interview"
            elif any(word in lower_text for word in ['assessment', 'test', 'challenge']):
                deadline_type = "assessment"
            elif any(word in lower_text for word in ['response', 'reply', 'confirm']):
                deadline_type = "response"
            elif any(word in lower_text for word in ['event', 'conference', 'fair']):
                deadline_type = "event"
        
        return {
            "has_deadline": bool(best_deadline),
            "deadline_date": best_deadline['date_str'] if best_deadline else None,
            "deadline_time": best_deadline['time_str'] if best_deadline else None,
            "timezone": None,
            "deadline_text": best_deadline['text'] if best_deadline else (deadline_texts[0] if deadline_texts else None),
            "deadline_type": deadline_type,
            "description": f"Deadline for {deadline_type}" if best_deadline else None,
            "all_found_dates": found_dates,
            "all_deadline_texts": deadline_texts
        }

    def check_event_exists(self, calendar_service, email_data: Dict, deadline_date: str) -> bool:
        """
        Check if an event for this email/deadline already exists in the calendar
        Also checks if this email ID has been processed before
        """
        try:
            # Check if email ID was already processed (works without calendar service)
            email_id = email_data.get('id')
            if email_id and email_id in self.processed_email_ids:
                print(f"  🔄 Duplicate: Email ID {email_id[:20]}... already processed")
                return True
            
            # Validate deadline is in the future
            deadline_dt = datetime.fromisoformat(deadline_date)
            if deadline_dt.date() <= datetime.now().date():
                print(f"  ⏪ Deadline {deadline_date} is not in the future, skipping duplicate check")
                return True  # Return True to prevent creating events for past dates
            
            # If no calendar service, can only check email ID
            if not calendar_service:
                return False
            
            # Search for events on the deadline date with similar subject
            time_min = f"{deadline_date}T00:00:00Z"
            time_max = f"{deadline_date}T23:59:59Z"
            
            subject = email_data.get('subject', '')
            
            events_result = calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                q=subject[:50],  # Search by first 50 chars of subject
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Check if any event matches our criteria
            for event in events:
                event_summary = event.get('summary', '')
                event_desc = event.get('description', '')
                extended_props = event.get('extendedProperties', {}).get('private', {})
                
                # Match by email ID (most reliable) or subject
                if extended_props.get('email_id') == email_id:
                    print(f"  🔄 Duplicate: Event exists with matching email ID {email_id[:20]}...")
                    return True
                elif subject[:30] in event_summary or subject[:30] in event_desc:
                    print(f"  🔄 Duplicate: Event exists for '{subject[:50]}' on {deadline_date}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"  ⚠️  Could not check for duplicates: {e}")
            # If we can't check, assume it doesn't exist (fail-safe)
            return False
    
    def create_calendar_event(self, email_data: Dict, deadline_info: Dict, calendar_service=None) -> Optional[Dict]:
        """
        Create a structured Google Calendar event for the actual deadline date
        Only creates if the event doesn't already exist and is in the future
        """
        if not deadline_info.get('has_deadline'):
            return None
        
        event_date = deadline_info.get('deadline_date')
        if not event_date:
            return None

        # STRICT validation: deadline MUST be in the future (at least tomorrow)
        try:
            deadline_dt = datetime.fromisoformat(event_date)
            now = datetime.now()
            
            # Reject if deadline is today or in the past
            if deadline_dt.date() <= now.date():
                print(f"  ❌ REJECTED: Deadline {event_date} is not in the future (today is {now.date()})")
                return {
                    'status': 'rejected',
                    'reason': 'past_deadline',
                    'message': f'Deadline {event_date} has passed or is today'
                }
        except Exception as e:
            print(f"  ❌ Invalid date format: {event_date} - {e}")
            return None
        
        # Check for duplicates (works with or without calendar service)
        if self.check_event_exists(calendar_service, email_data, event_date):
            print(f"  ⏭️  Skipping duplicate event")
            return {
                'status': 'duplicate',
                'message': 'Event already exists or email already processed'
            }
        
        # Mark this email as processed
        email_id = email_data.get('id')
        if email_id:
            self.processed_email_ids.add(email_id)
        
        subject = email_data.get('subject', 'Job Deadline Reminder')
        deadline_type = deadline_info.get('deadline_type', 'deadline')

        # Calendar event title
        event_title = f"{deadline_type.upper()} DEADLINE: {subject}" if deadline_type != 'other' else f"DEADLINE: {subject}"

        # Detailed description
        description = f"""
Job Deadline Reminder

Subject: {email_data.get('subject', '')}
From: {email_data.get('sender', '')}
Deadline Type: {deadline_type}
Deadline Date: {event_date}

Details: {deadline_info.get('deadline_text', 'See original email for details')}
Action Required: {deadline_info.get('description', 'Review and respond as needed')}

Received: {email_data.get('date', '')}
""".strip()

        # Default time if missing (end of day)
        event_time = deadline_info.get('deadline_time') or '23:59'
        deadline_str = f"{event_date}T{event_time}:00"

        print(f"  📆 Creating calendar event for: {deadline_str}")

        # Reminder schedule (relative to the deadline date, not today)
        reminders = [
            {'method': 'email', 'minutes': 1440},  # 1 day before
            {'method': 'popup', 'minutes': 60},    # 1 hour before
        ]
        if deadline_type in ['application', 'assessment']:
            reminders.append({'method': 'email', 'minutes': 10080})  # 1 week before

        return {
            'summary': event_title,
            'description': description,
            'start': {
                'dateTime': deadline_str,
                'timeZone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata')
            },
            'end': {
                'dateTime': deadline_str,
                'timeZone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata')
            },
            'reminders': {
                'useDefault': False,
                'overrides': reminders
            },
            'colorId': '11',  # Red color for urgency
            'source': {
                'title': 'Email Reminder System',
                'url': f"mailto:{email_data.get('sender', '')}"
            },
            # Add email metadata as extended properties for duplicate detection
            'extendedProperties': {
                'private': {
                    'email_id': email_data.get('id', ''),
                    'deadline_type': deadline_type,
                    'created_by': 'email_reminder_system',
                    'original_sender': email_data.get('sender', ''),
                    'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        }

    def analyze_email(self, email_data: Dict, calendar_service=None) -> Dict:
        """
        Analyze a single email through the rule-based pipeline
        Pass calendar_service to enable duplicate detection
        """
        print(f"\n🔍 Analyzing email: {email_data.get('subject', 'No Subject')}")
        
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
            print("  📅 Extracting deadlines...")
            deadline_info = self.extract_deadlines_rule_based(email_data)
            result["deadline_info"] = deadline_info
            
            # Step 3: Create calendar event if deadline found
            if deadline_info.get("has_deadline", False):
                print("  📝 Creating calendar event...")
                calendar_event = self.create_calendar_event(email_data, deadline_info, calendar_service)
                result["calendar_event"] = calendar_event
                
                if calendar_event and calendar_event.get('status') != 'duplicate':
                    print(f"  ✅ Event scheduled for: {deadline_info['deadline_date']}")
                elif calendar_event and calendar_event.get('status') == 'duplicate':
                    print(f"  ⏭️  Duplicate event skipped")
        
        return result

def main():
    """Test the system with sample data"""
    system = EmailReminderSystem()
    
    # Test email with various date formats
    test_email = {
        'subject': 'Software Engineer Position - Application Deadline December 15, 2024',
        'body': 'We are excited to invite you to apply. The deadline is December 15, 2024 at 11:59 PM.',
        'sender': 'careers@techcorp.com',
        'date': datetime.now().isoformat()
    }
    
    result = system.analyze_email(test_email)
    print(f"\n📊 Result: {json.dumps(result, indent=2, default=str)}")

if __name__ == "__main__":
    main()