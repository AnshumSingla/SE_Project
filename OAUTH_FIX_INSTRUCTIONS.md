# Fix OAuth Redirect URI Mismatch Error

## Quick Fix Instructions

### Step 1: Open Google Cloud Console

1. Go to: https://console.cloud.google.com/
2. Select project: **email-reminder-system-479300**
3. Go to: **APIs & Services** → **Credentials**

### Step 2: Edit OAuth Client ID

1. Find your OAuth 2.0 Client ID: `851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com`
2. Click on it to edit

### Step 3: Add Authorized JavaScript Origins

Add these EXACT URLs:

```
http://localhost:3000
http://127.0.0.1:3000
```

### Step 4: Add Authorized Redirect URIs

Add these EXACT URLs (FIXED - No more random ports!):

```
http://localhost:5000/auth/google/callback
```

**This is the ONLY redirect URI you need!** The server-side OAuth flow uses this fixed URL instead of random ports.

### Step 5: Save Changes

1. Click **SAVE** at the bottom
2. Wait 5-10 minutes for changes to propagate

### Alternative: Use Demo Mode

While waiting for OAuth to be fixed, click **"Try Demo Mode"** on the landing page to test the system with sample data.

## Current System URLs

- Frontend: http://localhost:3000 (currently running)
- Backend: http://localhost:5000 (currently running)
- Your Google Client ID: 851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com

Once you complete these steps, the Google Sign-In will work properly!
