"""
Complete Email Reminder System with Gmail and Google Calendar Integration

This is the main integrated system that combines:
1. Gmail email fetching 
2. AutoGen multi-agent analysis
3. Google Calendar reminder creation
4. Rule-based fallback when LLM is not available
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Import our custom modules
try:
    from gmail_integration import GmailIntegrator
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("⚠️ Gmail integration not available")

try:
    from calendar_integration import CalendarIntegrator
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    print("⚠️ Calendar integration not available")

# Import the rule-based system from our demo
from main_demo import EmailReminderSystem as RuleBasedSystem

# AutoGen imports
try:
    import autogen
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False

# Load environment variables
load_dotenv()

class UserSpecificGmailIntegrator:
    """Wrapper for Gmail service with user-specific credentials"""
    
    def __init__(self, gmail_service):
        self.service = gmail_service
    
    def get_recent_emails(self, max_results=50, days_back=7, query=""):
        """Fetch recent emails using authenticated service"""
        from datetime import datetime, timedelta
        import base64
        
        # Build query for recent emails
        date_filter = datetime.now() - timedelta(days=days_back)
        date_str = date_filter.strftime('%Y/%m/%d')
        
        search_query = f"after:{date_str}"
        if query:
            search_query += f" {query}"
        
        try:
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me', 
                q=search_query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    # Get full message details
                    msg = self.service.users().messages().get(
                        userId='me', 
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_email_message(msg)
                    if email_data:
                        emails.append(email_data)
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing email: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []
    
    def _parse_email_message(self, message):
        """Parse Gmail API message into structured dictionary"""
        # Reuse the parsing logic from GmailIntegrator
        from gmail_integration import GmailIntegrator
        integrator = GmailIntegrator()
        return integrator._parse_email_message(message)

class UserSpecificCalendarIntegrator:
    """Wrapper for Calendar service with user-specific credentials"""
    
    def __init__(self, calendar_service):
        self.service = calendar_service
    
    def create_deadline_reminder(self, email_data: Dict, deadline_info: Dict):
        """Create calendar event using authenticated service"""
        from calendar_integration import CalendarIntegrator
        
        # Create a temporary integrator to use the existing logic
        temp_integrator = CalendarIntegrator()
        temp_integrator.service = self.service
        
        return temp_integrator.create_deadline_reminder(email_data, deadline_info)
    
    def get_upcoming_reminders(self, days_ahead=30):
        """Get upcoming reminders using authenticated service"""
        from calendar_integration import CalendarIntegrator
        
        # Create a temporary integrator to use the existing logic
        temp_integrator = CalendarIntegrator()
        temp_integrator.service = self.service
        
        return temp_integrator.get_upcoming_reminders(days_ahead)

class IntegratedEmailReminderSystem:
    """
    Complete email reminder system with Gmail and Calendar integration
    Now supports user-specific credential management
    """
    
    def __init__(self, use_llm=True, user_id=None, credential_manager=None):
        self.use_llm = use_llm and AUTOGEN_AVAILABLE and os.getenv("OPENAI_API_KEY")
        self.user_id = user_id
        self.credential_manager = credential_manager
        
        # Initialize components
        self.rule_based_system = RuleBasedSystem()
        
        # Gmail integration - user-specific
        self.gmail_service = None
        if GMAIL_AVAILABLE and self.credential_manager and self.user_id:
            try:
                self.gmail_service = self.credential_manager.get_gmail_service(self.user_id)
                if self.gmail_service:
                    # Create a wrapper for the new API-compatible interface
                    self.gmail = UserSpecificGmailIntegrator(self.gmail_service)
            except Exception as e:
                print(f"⚠️ Gmail setup failed: {e}")
        else:
            # Fallback to file-based credentials for demo
            self.gmail = None
            if GMAIL_AVAILABLE:
                credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
                token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
                try:
                    self.gmail = GmailIntegrator(credentials_file, token_file)
                except Exception as e:
                    print(f"⚠️ Gmail setup failed: {e}")
        
        # Calendar integration - user-specific
        self.calendar_service = None
        if CALENDAR_AVAILABLE and self.credential_manager and self.user_id:
            try:
                self.calendar_service = self.credential_manager.get_calendar_service(self.user_id)
                if self.calendar_service:
                    # Create a wrapper for the new API-compatible interface
                    self.calendar = UserSpecificCalendarIntegrator(self.calendar_service)
            except Exception as e:
                print(f"⚠️ Calendar setup failed: {e}")
        else:
            # Fallback to file-based credentials for demo
            self.calendar = None
            if CALENDAR_AVAILABLE:
                cal_credentials = os.getenv('CALENDAR_CREDENTIALS_FILE', 'calendar_credentials.json')
                cal_token = os.getenv('CALENDAR_TOKEN_FILE', 'calendar_token.json')
                try:
                    self.calendar = CalendarIntegrator(cal_credentials, cal_token)
                except Exception as e:
                    print(f"⚠️ Calendar setup failed: {e}")
        
        # LLM-based agents (if available)
        if self.use_llm:
            self.setup_llm_agents()
    
    def setup_llm_agents(self):
        """Setup AutoGen LLM agents for enhanced analysis"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            llm_config = {
                "config_list": [
                    {
                        "model": "gpt-4o-mini",
                        "api_key": api_key,
                    }
                ],
                "temperature": 0.0,
            }
            
            self.user_proxy = autogen.UserProxyAgent(
                name="UserProxy",
                human_input_mode="NEVER",
                code_execution_config=False,
                max_consecutive_auto_reply=0
            )
            
            self.enhanced_classifier = autogen.AssistantAgent(
                name="EnhancedClassifier",
                llm_config=llm_config,
                system_message=(
                    "You are an expert email classifier for job opportunities. "
                    "Analyze emails with high accuracy to identify job-related content, "
                    "career opportunities, application deadlines, interviews, assessments, "
                    "and academic opportunities. Respond ONLY in JSON format with: "
                    '{"is_job_related": true/false, "confidence": 0.0-1.0, '
                    '"category": "job_posting|interview|assessment|deadline|application|academic|networking|other", '
                    '"urgency": "high|medium|low", "reasoning": "detailed explanation"}'
                )
            )
            
            print("✅ LLM agents initialized")
            
        except Exception as e:
            print(f"⚠️ LLM agent setup failed: {e}")
            self.use_llm = False
    
    def analyze_email_enhanced(self, email_data: Dict) -> Dict:
        """Enhanced email analysis using LLM + rule-based fallback"""
        
        if self.use_llm:
            try:
                # Try LLM analysis first
                return self._analyze_with_llm(email_data)
            except Exception as e:
                print(f"   ⚠️ LLM analysis failed: {e}, falling back to rule-based")
        
        # Fallback to rule-based analysis
        return self.rule_based_system.analyze_email(email_data)
    
    def _analyze_with_llm(self, email_data: Dict) -> Dict:
        """Analyze email using AutoGen LLM agents"""
        email_text = f"""
        Subject: {email_data.get('subject', '')}
        From: {email_data.get('sender', '')}
        Date: {email_data.get('date', '')}
        
        Body:
        {email_data.get('body', '')}
        """
        
        # Enhanced classification
        response = self.user_proxy.initiate_chat(
            self.enhanced_classifier,
            message=f"Analyze this email for job relevance:\n\n{email_text}",
            silent=True
        )
        
        # Parse LLM response
        try:
            response_text = response.chat_history[-1]['content']
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                llm_classification = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in LLM response")
        except:
            # Fallback to rule-based if LLM parsing fails
            return self.rule_based_system.analyze_email(email_data)
        
        # If job-related, extract deadlines using rule-based system (more reliable)
        result = {
            "email_data": email_data,
            "classification": llm_classification,
            "deadline_info": None,
            "calendar_event": None,
            "analysis_method": "llm_enhanced"
        }
        
        if llm_classification.get("is_job_related", False):
            # Use rule-based deadline extraction (more reliable than LLM for dates)
            deadline_info = self.rule_based_system.extract_deadlines_rule_based(email_data)
            result["deadline_info"] = deadline_info
            
            # Create calendar event if deadline found
            if deadline_info.get("has_deadline", False) and self.calendar:
                try:
                    calendar_event = self.calendar.create_deadline_reminder(email_data, deadline_info)
                    result["calendar_event"] = calendar_event
                except Exception as e:
                    print(f"   ⚠️ Calendar event creation failed: {e}")
        
        return result
    
    def scan_gmail_and_process(self, max_emails=50, days_back=7, query="") -> List[Dict]:
        """
        Main workflow: Scan Gmail and process all emails
        
        Args:
            max_emails: Maximum emails to process
            days_back: Days to look back
            query: Optional Gmail search query
        
        Returns:
            List of analysis results
        """
        print("🚀 Starting Complete Email Reminder System...")
        print("=" * 60)
        
        # Check system capabilities
        print("🔍 System Status:")
        print(f"   📧 Gmail Integration: {'✅' if self.gmail else '❌'}")
        print(f"   📅 Calendar Integration: {'✅' if self.calendar else '❌'}")
        print(f"   🤖 LLM Analysis: {'✅' if self.use_llm else '❌'}")
        print()
        
        if not self.gmail:
            print("⚠️ Gmail not available, using sample emails...")
            return self._process_sample_emails()
        
        # Fetch emails from Gmail
        print(f"📧 Fetching emails from Gmail (last {days_back} days)...")
        try:
            emails = self.gmail.get_recent_emails(
                max_results=max_emails,
                days_back=days_back,
                query=query
            )
            
            if not emails:
                print("📭 No emails found")
                return []
                
        except Exception as e:
            print(f"❌ Gmail fetch failed: {e}")
            print("⚠️ Falling back to sample emails...")
            return self._process_sample_emails()
        
        # Process each email
        print(f"\n🔍 Analyzing {len(emails)} emails...")
        results = []
        
        job_related_count = 0
        deadlines_found = 0
        calendar_events_created = 0
        
        for i, email in enumerate(emails):
            print(f"\n📧 [{i+1}/{len(emails)}] {email.get('subject', 'No Subject')[:50]}...")
            
            try:
                # Analyze email
                result = self.analyze_email_enhanced(email)
                results.append(result)
                
                # Update counters
                if result['classification'].get('is_job_related', False):
                    job_related_count += 1
                    print(f"   🎯 Job-related: {result['classification'].get('category', 'unknown')}")
                    
                    if result.get('deadline_info', {}).get('has_deadline', False):
                        deadlines_found += 1
                        deadline_date = result['deadline_info'].get('deadline_date', 'unknown')
                        print(f"   ⏰ Deadline: {deadline_date}")
                        
                        if result.get('calendar_event'):
                            calendar_events_created += 1
                            print(f"   📅 Calendar reminder created")
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
                continue
        
        # Final summary
        print(f"\n🎉 Email Processing Complete!")
        print(f"📊 Results Summary:")
        print(f"   📧 Total emails: {len(emails)}")
        print(f"   💼 Job-related: {job_related_count}")
        print(f"   ⏰ Deadlines found: {deadlines_found}")
        print(f"   📅 Calendar events: {calendar_events_created}")
        
        return results
    
    def _process_sample_emails(self) -> List[Dict]:
        """Process sample emails when Gmail is not available"""
        print("📝 Processing sample emails...")
        return self.rule_based_system.process_sample_emails()
    
    def get_upcoming_deadlines(self, days_ahead=30) -> List[Dict]:
        """Get upcoming deadlines from calendar"""
        if not self.calendar:
            print("❌ Calendar integration not available")
            return []
        
        try:
            return self.calendar.get_upcoming_reminders(days_ahead)
        except Exception as e:
            print(f"❌ Error fetching upcoming deadlines: {e}")
            return []
    
    def search_job_emails(self, query="") -> List[Dict]:
        """Search for specific job-related emails"""
        if not self.gmail:
            print("❌ Gmail integration not available")
            return []
        
        # Build job-focused search query
        job_query = "from:careers OR from:hr OR from:recruitment OR subject:interview OR subject:application"
        if query:
            job_query += f" {query}"
        
        try:
            emails = self.gmail.search_emails(job_query, max_results=20)
            results = []
            
            for email in emails:
                result = self.analyze_email_enhanced(email)
                if result['classification'].get('is_job_related', False):
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Job email search failed: {e}")
            return []

def create_system_for_user(user_id: str, credential_manager, use_llm=True):
    """
    Factory function to create email reminder system for specific user
    
    Args:
        user_id: Unique user identifier
        credential_manager: CredentialManager instance
        use_llm: Whether to use LLM analysis
        
    Returns:
        IntegratedEmailReminderSystem instance
    """
    return IntegratedEmailReminderSystem(
        use_llm=use_llm,
        user_id=user_id,
        credential_manager=credential_manager
    )

def main():
    """Main function with menu-driven interface"""
    
    print("🤖 Automated Email Reminder System")
    print("📧 Gmail + 🤖 AutoGen + 📅 Google Calendar")
    print("=" * 50)
    
    # Initialize system
    try:
        system = IntegratedEmailReminderSystem(use_llm=True)
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return
    
    while True:
        print("\n📋 Choose an option:")
        print("1. 🔍 Scan recent emails and create reminders")
        print("2. 🎯 Search for job-related emails")
        print("3. 📅 View upcoming deadlines")
        print("4. 📝 Process sample emails (demo)")
        print("5. ❌ Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            days_back = int(input("How many days back to scan? (default 7): ") or "7")
            max_emails = int(input("Max emails to process? (default 50): ") or "50")
            
            results = system.scan_gmail_and_process(
                max_emails=max_emails,
                days_back=days_back
            )
            
        elif choice == "2":
            search_query = input("Enter search terms (optional): ").strip()
            results = system.search_job_emails(search_query)
            
            if results:
                print(f"\n✅ Found {len(results)} job-related emails:")
                for r in results:
                    email = r['email_data']
                    classification = r['classification']
                    print(f"   • {email.get('subject', 'No Subject')[:60]}")
                    print(f"     From: {email.get('sender', 'Unknown')}")
                    print(f"     Category: {classification.get('category', 'Unknown')}")
            else:
                print("📭 No job-related emails found")
                
        elif choice == "3":
            upcoming = system.get_upcoming_deadlines()
            
            if upcoming:
                print(f"\n📅 Upcoming deadlines ({len(upcoming)} found):")
                for event in upcoming:
                    print(f"   • {event.get('title', 'No Title')}")
                    print(f"     Date: {event.get('start_time', 'Unknown')}")
                    print(f"     Type: {event.get('deadline_type', 'Unknown')}")
            else:
                print("📅 No upcoming deadlines found")
                
        elif choice == "4":
            system._process_sample_emails()
            
        elif choice == "5":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice, please try again")

if __name__ == "__main__":
    main()