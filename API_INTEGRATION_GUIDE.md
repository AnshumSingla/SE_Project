# 🚀 API Integration Guide

## **Updated System Architecture**

Your system now works as a **backend API service** that your web/mobile app can integrate with. Here's how the components work together:

### **🏗️ System Components:**

```
Your Web/Mobile App
        ↓ (HTTP API calls)
Flask API Service (api_service.py)
        ↓
User Management (OAuth + Database)
        ↓
AutoGen Multi-Agent System
        ↓
Gmail + Calendar APIs (user-specific)
        ↓
Notifications Back to Your App
```

## **📡 API Endpoints**

### **1. Authentication & Setup**

```http
POST /api/auth/setup
```

**Purpose**: Setup user credentials after OAuth  
**Payload**:

```json
{
  "user_id": "unique_user_id",
  "gmail_credentials": "encrypted_oauth_data",
  "calendar_credentials": "encrypted_oauth_data"
}
```

### **2. Email Scanning**

```http
POST /api/emails/scan
```

**Purpose**: Scan user's Gmail for job opportunities  
**Payload**:

```json
{
  "user_id": "user123",
  "max_emails": 50,
  "days_back": 7,
  "search_query": "from:careers"
}
```

**Response**:

```json
{
  "success": true,
  "summary": {
    "total_emails": 25,
    "job_related_emails": 8,
    "emails_with_deadlines": 5
  },
  "emails": [
    {
      "email_id": "msg_123",
      "subject": "Software Engineering Internship",
      "sender": "careers@company.com",
      "classification": {
        "is_job_related": true,
        "category": "application",
        "urgency": "medium",
        "confidence": 0.95
      },
      "deadline": {
        "has_deadline": true,
        "date": "2025-12-15",
        "time": "23:59",
        "type": "application",
        "urgency_days": 20
      }
    }
  ]
}
```

### **3. Calendar Reminders**

```http
POST /api/calendar/reminders
```

**Purpose**: Create Google Calendar reminders  
**Payload**:

```json
{
  "user_id": "user123",
  "email_ids": ["msg_123", "msg_456"],
  "reminder_preferences": {
    "default_reminders": [1440, 60],
    "urgent_reminders": [10080, 1440, 60]
  }
}
```

### **4. Upcoming Deadlines**

```http
GET /api/calendar/upcoming?user_id=user123&days_ahead=30
```

**Purpose**: Get upcoming job deadlines  
**Response**:

```json
{
  "success": true,
  "upcoming_events": [
    {
      "event_id": "cal_event_1",
      "title": "APPLICATION DEADLINE: Software Engineering Internship",
      "start_time": "2025-12-15T23:59:00Z",
      "deadline_type": "application",
      "urgency": "medium",
      "days_until": 20,
      "calendar_link": "https://calendar.google.com/..."
    }
  ]
}
```

### **5. Notifications**

```http
POST /api/notifications/send
```

**Purpose**: Send notifications to user  
**Payload**:

```json
{
  "user_id": "user123",
  "notification_type": "deadline_reminder",
  "message": "Application deadline in 24 hours!",
  "channels": ["push", "email"]
}
```

### **6. Analytics Dashboard**

```http
GET /api/analytics/dashboard?user_id=user123&period=month
```

**Purpose**: Get analytics for user dashboard  
**Response**:

```json
{
  "analytics": {
    "job_application_stats": {
      "total_opportunities_found": 15,
      "applications_submitted": 8,
      "interviews_scheduled": 3,
      "response_rate": 53.3
    },
    "deadline_management": {
      "upcoming_deadlines": 6,
      "overdue_deadlines": 1,
      "completed_deadlines": 12
    }
  }
}
```

## **🔄 Integration Flow for Your App**

### **Step 1: User Authentication**

```javascript
// In your web/mobile app
const authUrl = `https://accounts.google.com/o/oauth2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&scope=gmail.readonly%20calendar&response_type=code`;

// User clicks "Connect Gmail" → redirected to Google OAuth
// After approval, Google redirects back with authorization code
```

### **Step 2: Setup User Credentials**

```javascript
// After receiving OAuth code, exchange for tokens
const tokens = await exchangeCodeForTokens(authorizationCode);

// Setup user in your system
const setupResult = await fetch("/api/auth/setup", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: userId,
    gmail_credentials: tokens.gmail,
    calendar_credentials: tokens.calendar,
  }),
});
```

### **Step 3: Scan Emails**

```javascript
// Scan user's emails
const scanResult = await fetch("/api/emails/scan", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: userId,
    max_emails: 50,
    days_back: 7,
  }),
});

const data = await scanResult.json();
// Display job opportunities in your app UI
```

### **Step 4: Create Reminders**

```javascript
// User selects emails to create reminders for
const reminderResult = await fetch("/api/calendar/reminders", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: userId,
    email_ids: selectedEmailIds,
  }),
});
```

### **Step 5: Send Notifications**

```javascript
// Your app can trigger notifications
const notificationResult = await fetch("/api/notifications/send", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: userId,
    notification_type: "deadline_reminder",
    message: "You have a deadline approaching!",
    channels: ["push", "email"],
  }),
});
```

## **🚀 Getting Started**

### **1. Start the API Service**

```bash
cd SE_Project
python api_service.py
```

The service runs on `http://localhost:5000`

### **2. Test with Demo Client**

```bash
python api_client_demo.py
```

### **3. Integrate with Your App**

Use the provided `EmailReminderAPIClient` class as a reference for your frontend integration.

## **🔒 Security Features**

- **OAuth 2.0**: Secure Google account authentication
- **Encrypted Storage**: User credentials encrypted with Fernet
- **Session Management**: Secure user sessions with expiration
- **User Isolation**: Each user's data is completely isolated

## **📱 Notification Integration**

Your app needs to implement notification handlers:

```javascript
// Push notifications
const sendPushNotification = (userId, message) => {
  // Your push notification service (FCM, APNs, etc.)
};

// Email notifications
const sendEmailNotification = (userId, message) => {
  // Your email service (SendGrid, AWS SES, etc.)
};

// In-app notifications
const showInAppNotification = (message) => {
  // Your app's notification UI
};
```

## **📊 Dashboard Integration**

Use the analytics endpoint to power your dashboard:

```javascript
// Fetch analytics data
const analytics = await fetch(
  `/api/analytics/dashboard?user_id=${userId}&period=month`
);
const data = await analytics.json();

// Display in your dashboard
displayJobStats(data.analytics.job_application_stats);
displayDeadlineStats(data.analytics.deadline_management);
displayCategoryBreakdown(data.analytics.category_breakdown);
```

## **🎯 Key Benefits**

✅ **API-First Design**: Easy integration with any frontend  
✅ **User-Specific**: Multi-tenant with secure data isolation  
✅ **OAuth Integration**: Seamless Google account connection  
✅ **Real-time Processing**: Immediate email analysis and reminder creation  
✅ **Comprehensive Analytics**: Track job application performance  
✅ **Flexible Notifications**: Multiple notification channels  
✅ **Scalable Architecture**: Ready for production deployment

Your web/mobile app now has a complete backend service for automated job deadline management! 🎉
