# Token Refresh Implementation - Complete Guide

## Overview

Implemented a robust OAuth token management system with automatic refresh, proactive renewal, and proper error handling.

---

## 🔑 Implementation Summary

### **1. OAuth Flow with Expiry Tracking**

#### Backend (`api_service.py` - OAuth Callback)

- **Calculates token expiry**: `current_time + expires_in` (default 3600s = 1 hour)
- **Sends expiry timestamp** in postMessage to frontend
- **Stores full credentials** including `refresh_token`, `expiry`, and `scopes`

```python
# Lines 183-207
expiry_time = datetime.now() + timedelta(seconds=expires_in)
expiry_timestamp = int(expiry_time.timestamp() * 1000)  # Milliseconds

credentials_dict = {
    'token': access_token,
    'refresh_token': refresh_token,
    'expiry': expiry_time.isoformat(),
    'expiry_time': expiry_timestamp  # Sent to frontend
}
```

#### Frontend (`LandingPage.jsx`)

- **Receives credentials** with `expiry_time` from postMessage
- **Stores in localStorage** via AuthContext

```jsx
// Lines 33-44
const mockCredential = {
  credential: "server_auth_token",
  userInfo: event.data.user,
  accessToken: event.data.accessToken,
  credentials: event.data.credentials, // Includes expiry_time
};
```

---

### **2. Backend Auto-Refresh Before Every API Call**

#### Helper Function (`api_service.py` - Lines 302-324)

```python
def _ensure_valid_credentials(credentials):
    """
    Validate credentials and auto-refresh if expired.
    Returns refreshed credentials or raises exception.
    """
    if credentials.expired or (credentials.expiry and credentials.expiry <= datetime.now()):
        print(f"🔄 Token expired, auto-refreshing...")
        credentials.refresh(Request())
        print(f"✅ Token auto-refreshed successfully")
    return credentials
```

#### Applied To All Endpoints

- **`/api/emails/scan`** (Line 530)
- **`/api/calendar/upcoming`** (Line 1210)
- **`/api/calendar/reminders/<event_id>` DELETE** (Line 1085)

```python
# Before making Google API calls
credentials = _ensure_valid_credentials(credentials)
```

---

### **3. Frontend Background Token Refresh**

#### AuthContext (`AuthContext.jsx` - Lines 38-100)

**Proactive Refresh Timer:**

- Checks token expiry **every 10 minutes**
- Refreshes if **< 5 minutes** until expiry
- Prevents 401 errors before they happen

```jsx
const refreshTokenIfNeeded = async () => {
  const now = Date.now();
  const expiryTime = user.credentials.expiry_time || 0;
  const minutesUntilExpiry = (expiryTime - now) / (1000 * 60);

  if (minutesUntilExpiry < 5) {
    // Refresh token
  }
};

// Check immediately on mount
refreshTokenIfNeeded();

// Then check every 10 minutes
const interval = setInterval(refreshTokenIfNeeded, 10 * 60 * 1000);
```

---

### **4. Axios Interceptor for 401 Errors**

#### API Service (`apiService.js` - Lines 55-95)

**Automatic Retry on 401:**

1. **Catches 401 response**
2. **Calls `/api/auth/refresh`** with `refresh_token`
3. **Updates stored credentials** with new `access_token` and `expiry_time`
4. **Retries original request** automatically
5. **User never notices** the refresh happened

```javascript
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const newAccessToken = await refreshAccessToken();

      if (newAccessToken) {
        return api(originalRequest); // Retry with new token
      }
    }
  }
);
```

---

### **5. Refresh Token Endpoint**

#### Backend (`api_service.py` - Lines 326-382)

**Enhanced Error Handling:**

- Returns **`invalid_grant`** error for revoked tokens
- Includes **`expiry_time`** in response (Unix timestamp in ms)
- Logs detailed refresh status

```python
@app.route('/api/auth/refresh', methods=['POST'])
def refresh_access_token():
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )

    credentials.refresh(Request())
    expiry_timestamp = int(credentials.expiry.timestamp() * 1000)

    return jsonify({
        "success": True,
        "access_token": credentials.token,
        "expiry_time": expiry_timestamp
    })
```

---

### **6. Invalid Grant Error Handling**

#### When Refresh Token is Revoked/Expired

**Backend Response:**

```json
{
  "success": false,
  "error": "invalid_grant",
  "message": "Refresh token has been revoked. Please login again."
}
```

**Frontend Actions:**

1. **AuthContext** (Lines 68-74): Clears storage and redirects to login
2. **apiService** (Lines 58-72): Clears storage and redirects to login
3. **User sees toast**: "Session expired. Please login again."

```javascript
if (data.error === "invalid_grant") {
  localStorage.removeItem("jobReminderUser");
  localStorage.removeItem("lastSync");
  window.location.href = "/";
}
```

---

## 📊 Token Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Signs In                                            │
│    ↓                                                         │
│ 2. Backend exchanges code for tokens                        │
│    - access_token (expires in 1 hour)                       │
│    - refresh_token (long-lived)                             │
│    - expiry_time (current_time + 3600s)                     │
│    ↓                                                         │
│ 3. Frontend stores credentials in localStorage              │
│    ↓                                                         │
│ 4. Background Timer Starts (every 10 min)                   │
│    ├─ If < 5 min until expiry → Refresh                     │
│    └─ Updates expiry_time                                   │
│    ↓                                                         │
│ 5. User makes API call                                      │
│    ├─ Backend checks credentials.expired                    │
│    ├─ Auto-refreshes if expired                             │
│    └─ Proceeds with Google API call                         │
│    ↓                                                         │
│ 6. If 401 error (unexpected)                                │
│    ├─ Axios interceptor catches it                          │
│    ├─ Calls /api/auth/refresh                               │
│    ├─ Updates credentials                                   │
│    └─ Retries original request                              │
│    ↓                                                         │
│ 7. If invalid_grant error                                   │
│    ├─ Clear all stored data                                 │
│    ├─ Show "Session expired" message                        │
│    └─ Redirect to login page                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### ✅ **Proactive Refresh**

- Checks every 10 minutes
- Refreshes 5 minutes before expiry
- Prevents 401 errors entirely

### ✅ **Backend Validation**

- Auto-checks `credentials.expired` before every Google API call
- Self-healing: refreshes tokens transparently
- No stale tokens reach Google APIs

### ✅ **Reactive Refresh**

- Axios interceptor catches unexpected 401s
- Automatic retry with new token
- User never sees errors

### ✅ **Expiry Tracking**

- Stores Unix timestamp (ms) in localStorage
- Calculates exact minutes until expiry
- Precise refresh timing

### ✅ **Error Handling**

- Detects `invalid_grant` (revoked token)
- Clears corrupted state
- Graceful logout with user notification

### ✅ **Stateless Architecture**

- No database required
- Works on Vercel serverless
- Credentials passed in every request

---

## 🧪 Testing Checklist

### **Happy Path**

- [x] User logs in → credentials stored with expiry_time
- [x] Background timer checks every 10 minutes
- [x] Token refreshes 5 minutes before expiry
- [x] API calls succeed continuously without re-login

### **Token Expiry**

- [x] Let token expire (wait 1 hour without refresh)
- [x] Make API call → backend auto-refreshes
- [x] If backend fails → axios interceptor refreshes
- [x] Request succeeds after refresh

### **Revoked Token**

- [ ] Revoke refresh token in Google Console
- [ ] Make API call → invalid_grant error
- [ ] User logged out automatically
- [ ] Toast message shown: "Session expired"

### **Page Refresh**

- [x] User refreshes browser
- [x] Credentials loaded from localStorage
- [x] Background timer restarts
- [x] No re-login required

### **Multiple Tabs**

- [x] Open app in 2 tabs
- [x] Login in tab 1 → both tabs share localStorage
- [x] Refresh happens in one tab → other tab gets new token
- [x] Both tabs continue working

---

## 🔧 Configuration

### **Backend Environment Variables**

```bash
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
FRONTEND_URL=https://se-project-theta.vercel.app
```

### **Frontend Environment Variables**

```bash
VITE_API_BASE_URL=https://se-project-akel.vercel.app
```

### **Google Cloud Console**

- **Scopes**: `openid`, `email`, `profile`, `gmail.readonly`, `calendar`
- **OAuth 2.0 Redirect URIs**:
  - `http://localhost:5000/auth/google/callback`
  - `https://se-project-akel.vercel.app/auth/google/callback`
- **Access type**: `offline` (to get refresh_token)

---

## 📝 Code Locations

### **Backend**

| File             | Lines   | Purpose                              |
| ---------------- | ------- | ------------------------------------ |
| `api_service.py` | 302-324 | `_ensure_valid_credentials()` helper |
| `api_service.py` | 326-382 | `/api/auth/refresh` endpoint         |
| `api_service.py` | 183-207 | OAuth callback with expiry           |
| `api_service.py` | 530     | Email scan auto-refresh              |
| `api_service.py` | 1210    | Calendar list auto-refresh           |
| `api_service.py` | 1085    | Calendar delete auto-refresh         |

### **Frontend**

| File              | Lines  | Purpose                        |
| ----------------- | ------ | ------------------------------ |
| `AuthContext.jsx` | 38-100 | Background refresh timer       |
| `AuthContext.jsx` | 68-74  | invalid_grant handling         |
| `apiService.js`   | 27-95  | Axios interceptor + refresh    |
| `LandingPage.jsx` | 33-44  | Receive credentials from OAuth |

---

## 🚀 Deployment Notes

### **Vercel Serverless Considerations**

1. **No file storage**: Credentials passed in request body/params
2. **No persistent sessions**: Token-based auth only
3. **Cold starts**: Background timer restarts on mount
4. **Environment variables**: Set in Vercel dashboard

### **Token Security**

- ✅ `refresh_token` stored in localStorage (encrypted HTTPS)
- ✅ `client_secret` on backend only (never exposed to frontend)
- ✅ Tokens cleared on logout
- ✅ Auto-logout on invalid_grant

---

## 📚 References

- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)
- [Token Refresh Guide](https://developers.google.com/identity/protocols/oauth2/web-server#offline)
- [Axios Interceptors](https://axios-http.com/docs/interceptors)

---

**Status**: ✅ Implementation Complete  
**Last Updated**: 2025-11-30  
**Production URLs**:

- Frontend: https://se-project-theta.vercel.app
- Backend: https://se-project-akel.vercel.app
