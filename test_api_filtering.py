"""
Test to verify API filtering of duplicates and past deadlines
"""
import sys
sys.path.insert(0, '.')

from main_demo import EmailReminderSystem
from datetime import datetime, timedelta
import json

def test_api_filtering():
    """Simulate the API filtering logic"""
    print("="*60)
    print("Testing API Response Filtering")
    print("="*60)
    
    system = EmailReminderSystem()
    
    # Create test emails
    test_emails = [
        {
            'id': 'email_1',
            'subject': 'Software Engineer Position - Dec 15',
            'body': 'Apply by December 15, 2025',
            'sender': 'careers@company.com',
            'date': datetime.now().isoformat()
        },
        {
            'id': 'email_1',  # Duplicate ID
            'subject': 'Software Engineer Position - Dec 15',
            'body': 'Apply by December 15, 2025',
            'sender': 'careers@company.com',
            'date': datetime.now().isoformat()
        },
        {
            'id': 'email_2',
            'subject': 'Interview on Nov 20',
            'body': 'Interview was on November 20, 2025',  # Past date
            'sender': 'hr@company.com',
            'date': datetime.now().isoformat()
        },
        {
            'id': 'email_3',
            'subject': 'Future Interview',
            'body': 'Interview on December 10, 2025',
            'sender': 'hr@company.com',
            'date': datetime.now().isoformat()
        }
    ]
    
    # Process emails
    results = []
    for email in test_emails:
        result = system.analyze_email(email)
        results.append(result)
    
    print(f"\n📊 Processing Results:")
    print(f"Total emails processed: {len(results)}")
    
    # Simulate API filtering (matches api_service.py logic)
    formatted_results = []
    skipped_count = 0
    
    for result in results:
        email_data = result.get('email_data', {})
        deadline_info = result.get('deadline_info', {})
        calendar_event = result.get('calendar_event')
        
        # Skip emails without deadlines
        if not deadline_info or not deadline_info.get('has_deadline'):
            skipped_count += 1
            print(f"\n❌ FILTERED: {email_data.get('subject', '')[:50]}")
            print(f"   Reason: no_deadline")
            continue
        
        # Skip emails with duplicate or rejected calendar events
        if calendar_event:
            status = calendar_event.get('status')
            if status in ['duplicate', 'rejected']:
                skipped_count += 1
                print(f"\n❌ FILTERED: {email_data.get('subject', '')[:50]}")
                print(f"   Reason: {status}")
                print(f"   Message: {calendar_event.get('message', '')}")
                continue
        
        formatted_results.append({
            'email_id': email_data.get('id'),
            'subject': email_data.get('subject'),
            'deadline': result.get('deadline_info', {})
        })
        print(f"\n✅ INCLUDED: {email_data.get('subject', '')[:50]}")
    
    print(f"\n" + "="*60)
    print(f"📊 API Response Summary:")
    print(f"   Total Processed: {len(results)}")
    print(f"   Filtered Out: {skipped_count}")
    print(f"   Sent to Frontend: {len(formatted_results)}")
    print(f"="*60)
    
    # Verify expectations
    expected_sent = 2  # email_3 (future) and email_1 (first occurrence)
    expected_filtered = 2  # email_1 (duplicate) and email_2 (past)
    
    if len(formatted_results) == expected_sent and skipped_count == expected_filtered:
        print("\n✅ TEST PASSED: Correct filtering!")
        return True
    else:
        print(f"\n❌ TEST FAILED:")
        print(f"   Expected to send: {expected_sent}, Actually sent: {len(formatted_results)}")
        print(f"   Expected to filter: {expected_filtered}, Actually filtered: {skipped_count}")
        return False

if __name__ == "__main__":
    success = test_api_filtering()
    sys.exit(0 if success else 1)
