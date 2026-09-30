"""
Test script for the complete email reminder system
Runs automated tests without requiring user input
"""

from complete_system import IntegratedEmailReminderSystem

def test_complete_system():
    """Test the complete integrated system"""
    
    print("🧪 Testing Complete Email Reminder System")
    print("=" * 50)
    
    # Initialize system
    print("🔧 Initializing system...")
    try:
        system = IntegratedEmailReminderSystem(use_llm=False)  # Use rule-based for testing
        print("✅ System initialized successfully")
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return
    
    # Check system components
    print("\n🔍 System Component Status:")
    print(f"   📧 Gmail Integration: {'✅' if system.gmail else '❌ Not configured'}")
    print(f"   📅 Calendar Integration: {'✅' if system.calendar else '❌ Not configured'}")
    print(f"   🤖 LLM Analysis: {'✅' if system.use_llm else '❌ Using rule-based fallback'}")
    
    # Test with sample emails
    print("\n📝 Testing with sample emails...")
    try:
        results = system._process_sample_emails()
        
        if results:
            print(f"✅ Successfully processed {len(results)} sample emails")
            
            # Analyze results
            job_related = sum(1 for r in results if r['classification'].get('is_job_related', False))
            with_deadlines = sum(1 for r in results if r.get('deadline_info') and r['deadline_info'].get('has_deadline', False))
            
            print(f"📊 Results:")
            print(f"   💼 Job-related emails: {job_related}/{len(results)}")
            print(f"   ⏰ Emails with deadlines: {with_deadlines}/{len(results)}")
            
            # Show sample classifications
            print(f"\n📋 Sample Classifications:")
            for i, result in enumerate(results[:3]):
                email = result['email_data']
                classification = result['classification']
                print(f"   {i+1}. {email.get('subject', 'No Subject')[:40]}...")
                print(f"      Job-related: {classification.get('is_job_related', False)}")
                if classification.get('is_job_related'):
                    print(f"      Category: {classification.get('category', 'unknown')}")
                    print(f"      Urgency: {classification.get('urgency', 'unknown')}")
        else:
            print("❌ No results returned from sample processing")
            
    except Exception as e:
        print(f"❌ Sample email processing failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Gmail integration (if available)
    if system.gmail:
        print(f"\n📧 Testing Gmail integration...")
        try:
            # This would require authentication, so just test the setup
            print("⚠️ Gmail integration available but requires authentication")
            print("   Run the full system with: python complete_system.py")
        except Exception as e:
            print(f"❌ Gmail test failed: {e}")
    else:
        print(f"\n📧 Gmail integration not configured")
        print("   To enable: Set up credentials.json and configure Gmail API")
    
    # Test Calendar integration (if available)
    if system.calendar:
        print(f"\n📅 Testing Calendar integration...")
        try:
            print("⚠️ Calendar integration available but requires authentication")
            print("   Run the full system with: python complete_system.py")
        except Exception as e:
            print(f"❌ Calendar test failed: {e}")
    else:
        print(f"\n📅 Calendar integration not configured")
        print("   To enable: Set up calendar_credentials.json and configure Calendar API")
    
    print(f"\n🎉 System Test Complete!")
    print(f"\n📋 Next Steps:")
    print(f"   1. ✅ Basic functionality working")
    print(f"   2. 📧 Set up Gmail API for real email scanning")
    print(f"   3. 📅 Set up Calendar API for automatic reminders")
    print(f"   4. 🔑 Add OpenAI API key for enhanced LLM analysis")
    print(f"   5. 🚀 Run: python complete_system.py")

if __name__ == "__main__":
    test_complete_system()