"""
Test script to verify duplicate and wrong deadline fixes
"""

from main_demo import EmailReminderSystem
from datetime import datetime

def test_duplicate_detection():
    """Test that duplicate emails are detected"""
    print("=" * 60)
    print("TEST 1: Duplicate Email Detection")
    print("=" * 60)
    
    system = EmailReminderSystem()
    
    # Test email
    test_email = {
        'id': 'test_email_123',
        'subject': 'Software Engineer Position - Application Deadline Dec 15',
        'body': 'Please submit your application by December 15, 2025 at 11:59 PM.',
        'sender': 'careers@techcorp.com',
        'date': datetime.now().isoformat()
    }
    
    # Process first time
    print("\n1️⃣ Processing email first time:")
    result1 = system.analyze_email(test_email)
    has_deadline_1 = result1.get('deadline_info', {}).get('has_deadline', False)
    event_1 = result1.get('calendar_event')
    
    print(f"   Has deadline: {has_deadline_1}")
    print(f"   Event created: {event_1 is not None and event_1.get('status') != 'duplicate'}")
    
    # Process second time (should detect duplicate by email ID)
    print("\n2️⃣ Processing same email second time:")
    result2 = system.analyze_email(test_email)
    event_2 = result2.get('calendar_event')
    
    print(f"   Event status: {event_2.get('status') if event_2 else 'None'}")
    print(f"   Should be duplicate: {event_2.get('status') == 'duplicate' if event_2 else False}")
    
    # Verify
    if event_2 and event_2.get('status') == 'duplicate':
        print("\n✅ TEST PASSED: Duplicate detection working!")
    else:
        print("\n❌ TEST FAILED: Duplicate not detected!")
    
    return event_2 and event_2.get('status') == 'duplicate'

def test_subject_vs_body_dates():
    """Test that body dates are prioritized over subject dates"""
    print("\n" + "=" * 60)
    print("TEST 2: Subject vs Body Date Priority")
    print("=" * 60)
    
    system = EmailReminderSystem()
    
    # Email with date in subject (describing position) and date in body (actual deadline)
    test_email = {
        'id': 'test_email_456',
        'subject': 'Software Engineer Position - Application Deadline Dec 15',
        'body': 'We are excited about your interest. Please submit your application by January 10, 2026 at 11:59 PM.',
        'sender': 'careers@example.com',
        'date': datetime.now().isoformat()
    }
    
    print("\n📧 Email with:")
    print("   Subject: ...Dec 15")
    print("   Body: ...January 10, 2026")
    
    result = system.analyze_email(test_email)
    deadline_info = result.get('deadline_info', {})
    
    if deadline_info.get('has_deadline'):
        deadline_date = deadline_info.get('deadline_date')
        deadline_source = None
        
        # Check which date was selected
        all_dates = deadline_info.get('all_found_dates', [])
        for date_info in all_dates:
            if date_info['date_str'] == deadline_date:
                deadline_source = date_info['source']
                break
        
        print(f"\n   Selected deadline: {deadline_date}")
        print(f"   Source: {deadline_source}")
        
        # Should be from body (January 10) not subject (Dec 15)
        if deadline_source == 'body' and '2026-01' in deadline_date:
            print("\n✅ TEST PASSED: Body date prioritized correctly!")
            return True
        else:
            print("\n❌ TEST FAILED: Wrong date selected!")
            return False
    else:
        print("\n❌ TEST FAILED: No deadline found!")
        return False

def test_past_date_rejection():
    """Test that past dates are rejected"""
    print("\n" + "=" * 60)
    print("TEST 3: Past Date Rejection")
    print("=" * 60)
    
    system = EmailReminderSystem()
    
    # Email with past date
    test_email = {
        'id': 'test_email_789',
        'subject': 'Software Engineer Position - Application Deadline Nov 20',
        'body': 'Application deadline was November 20, 2025.',
        'sender': 'careers@example.com',
        'date': datetime.now().isoformat()
    }
    
    print("\n📧 Email with past date (Nov 20, 2025):")
    
    result = system.analyze_email(test_email)
    deadline_info = result.get('deadline_info', {})
    event = result.get('calendar_event')
    
    has_deadline = deadline_info.get('has_deadline', False)
    deadline_date = deadline_info.get('deadline_date')
    
    print(f"   Has deadline: {has_deadline}")
    print(f"   Deadline date: {deadline_date}")
    print(f"   Event status: {event.get('status') if event else 'None'}")
    
    # Should not create event for past date
    if not has_deadline or (event and event.get('status') == 'rejected'):
        print("\n✅ TEST PASSED: Past date rejected!")
        return True
    else:
        print("\n❌ TEST FAILED: Past date not rejected!")
        return False

def test_subject_date_with_no_body():
    """Test subject date when no body date exists"""
    print("\n" + "=" * 60)
    print("TEST 4: Subject Date When No Body Date")
    print("=" * 60)
    
    system = EmailReminderSystem()
    
    # Email with only subject date
    test_email = {
        'id': 'test_email_101',
        'subject': 'Interview Invitation - Jan 01, 2026',
        'body': 'We would like to invite you to an interview on the date mentioned in subject.',
        'sender': 'hr@company.com',
        'date': datetime.now().isoformat()
    }
    
    print("\n📧 Email with:")
    print("   Subject: Jan 01, 2026")
    print("   Body: No specific date")
    
    result = system.analyze_email(test_email)
    deadline_info = result.get('deadline_info', {})
    
    print(f"\n   Deadline info: {deadline_info}")
    
    if deadline_info.get('has_deadline'):
        deadline_date = deadline_info.get('deadline_date')
        all_dates = deadline_info.get('all_found_dates', [])
        print(f"\n   Selected deadline: {deadline_date}")
        print(f"   All found dates: {len(all_dates)}")
        for d in all_dates:
            print(f"      - {d['date_str']} (from {d['source']})")
        
        # Should use subject date when no body date
        if '2026-01-01' in deadline_date:
            print("\n✅ TEST PASSED: Subject date used when no body date!")
            return True
        else:
            print("\n❌ TEST FAILED: Wrong date selected!")
            return False
    else:
        all_dates = deadline_info.get('all_found_dates', [])
        print(f"   All found dates: {len(all_dates)}")
        print("\n❌ TEST FAILED: No deadline found!")
        return False

def main():
    """Run all tests"""
    print("\n🧪 Running Duplicate and Wrong Deadline Fix Tests")
    print("=" * 60)
    print(f"Current Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Duplicate Detection", test_duplicate_detection()))
    results.append(("Subject vs Body Priority", test_subject_vs_body_dates()))
    results.append(("Past Date Rejection", test_past_date_rejection()))
    results.append(("Subject Date Fallback", test_subject_date_with_no_body()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed!")

if __name__ == "__main__":
    main()
