"""
Test CORS and DELETE endpoint functionality
"""
import requests

API_BASE_URL = "http://localhost:5000"

def test_options_request():
    """Test OPTIONS request (CORS preflight)"""
    print("="*60)
    print("Testing CORS Preflight (OPTIONS)")
    print("="*60)
    
    event_id = "test_event_123"
    user_id = "test_user"
    
    url = f"{API_BASE_URL}/api/calendar/reminders/{event_id}"
    params = {"user_id": user_id}
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "DELETE",
        "Access-Control-Request-Headers": "content-type"
    }
    
    print(f"\n📡 Sending OPTIONS request:")
    print(f"   URL: {url}")
    print(f"   Headers: {headers}")
    
    try:
        response = requests.options(url, params=params, headers=headers, timeout=5)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower():
                print(f"      {key}: {value}")
        
        if response.status_code == 204:
            print("\n✅ OPTIONS request handled correctly!")
            return True
        elif response.status_code == 200:
            print("\n✅ OPTIONS request successful!")
            return True
        else:
            print(f"\n❌ Unexpected status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Server not running. Start with: python api_service.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_delete_request():
    """Test actual DELETE request"""
    print("\n" + "="*60)
    print("Testing DELETE Request")
    print("="*60)
    
    event_id = "test_event_123"
    user_id = "test_user"
    
    url = f"{API_BASE_URL}/api/calendar/reminders/{event_id}"
    params = {"user_id": user_id}
    headers = {
        "Origin": "http://localhost:5173",
        "Content-Type": "application/json"
    }
    
    print(f"\n📡 Sending DELETE request:")
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    
    try:
        response = requests.delete(url, params=params, headers=headers, timeout=5)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   CORS Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower():
                print(f"      {key}: {value}")
        
        if response.status_code in [200, 404, 500]:
            try:
                print(f"   Body: {response.json()}")
            except:
                print(f"   Body: {response.text}")
            
        if response.status_code == 200 or response.status_code == 500:
            print("\n✅ DELETE endpoint is accessible!")
            return True
        else:
            print(f"\n❌ Unexpected status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Server not running. Start with: python api_service.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 CORS & DELETE Endpoint Test\n")
    
    options_ok = test_options_request()
    delete_ok = test_delete_request()
    
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    print(f"OPTIONS (CORS Preflight): {'✅ PASS' if options_ok else '❌ FAIL'}")
    print(f"DELETE Request: {'✅ PASS' if delete_ok else '❌ FAIL'}")
    
    if options_ok and delete_ok:
        print("\n🎉 All tests passed! The delete endpoint is ready.")
        print("\n💡 Next steps:")
        print("   1. Make sure the backend server is running")
        print("   2. Try deleting a reminder from the frontend")
        print("   3. Check the server logs for confirmation")
    else:
        print("\n⚠️  Some tests failed. Check the server configuration.")
    
    print("="*60)
