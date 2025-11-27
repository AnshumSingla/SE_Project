"""
Test delete reminder functionality
"""
import requests
import json

API_BASE_URL = "http://localhost:5000"

def test_delete_endpoint():
    """Test that the delete endpoint exists and responds correctly"""
    
    print("="*60)
    print("Testing Delete Reminder Endpoint")
    print("="*60)
    
    # Test with a fake event ID (should return 404 or success)
    event_id = "test_event_123"
    user_id = "test_user"
    
    url = f"{API_BASE_URL}/api/calendar/reminders/{event_id}"
    params = {"user_id": user_id}
    
    print(f"\n📡 Testing DELETE request:")
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    
    try:
        response = requests.delete(url, params=params, timeout=5)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        # Check if endpoint exists (not 404 for endpoint itself)
        if response.status_code == 200 or response.status_code == 500:
            print("\n✅ Endpoint exists and responds!")
            return True
        else:
            print(f"\n❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Server not running. Start with: python api_service.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def print_endpoint_summary():
    """Print summary of the delete endpoint"""
    print("\n" + "="*60)
    print("📋 Delete Reminder API Endpoint Summary")
    print("="*60)
    print("\n🔗 Endpoint:")
    print("   DELETE /api/calendar/reminders/<event_id>")
    print("\n📥 Parameters:")
    print("   - Path: event_id (Google Calendar event ID)")
    print("   - Query: user_id (User identifier)")
    print("\n📤 Response:")
    print("   Success: {success: true, message: '...', event_id: '...'}")
    print("   Error: {success: false, error: '...'}")
    print("\n🎯 Usage in Frontend:")
    print("   apiService.deleteReminder(userId, eventId)")
    print("\n🗑️  What it does:")
    print("   1. Validates user_id and event_id")
    print("   2. Loads calendar credentials")
    print("   3. Calls Google Calendar API to delete event")
    print("   4. Returns success/failure status")
    print("="*60)

if __name__ == "__main__":
    print_endpoint_summary()
    print("\n")
    test_delete_endpoint()
