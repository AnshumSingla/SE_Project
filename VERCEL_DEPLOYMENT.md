# Vercel Deployment Guide

## 🚀 Your Setup

**Backend:** `https://se-project-akel.vercel.app/`  
**Frontend:** (Update in `.env` after deployment)

---

## ✅ What's Been Updated

### 1. **Backend Configuration** (`api_service.py`)

✅ **Dynamic CORS Origins** - Supports both local and Vercel URLs:

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    os.environ.get('FRONTEND_URL', '').rstrip('/'),
]
```

✅ **Dynamic OAuth Redirect URI** - Uses environment variable:

```python
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:5000')
REDIRECT_URI = f"{BACKEND_URL.rstrip('/')}/auth/google/callback"
```

✅ **Secure Cookies for Production**:

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
```

### 2. **Environment Variables** (`.env`)

Added deployment URLs:

```env
BACKEND_URL=https://se-project-akel.vercel.app
FRONTEND_URL=https://your-frontend-url.vercel.app
```

### 3. **Vercel Configuration** (`vercel.json`)

Created backend deployment config for Python/Flask.

---

## 📋 Steps to Complete Deployment

### Step 1: Update Google Cloud Console

**Important:** Add your Vercel URLs to Google OAuth allowed URIs:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: `email-reminder-system-479300`
3. Navigate to: **APIs & Services** → **Credentials**
4. Click your OAuth 2.0 Client ID
5. Add to **Authorized redirect URIs**:
   ```
   https://se-project-akel.vercel.app/auth/google/callback
   ```
6. Add to **Authorized JavaScript origins**:
   ```
   https://se-project-akel.vercel.app
   https://your-frontend-url.vercel.app
   ```
7. Click **Save**

### Step 2: Set Vercel Environment Variables (Backend)

In your Vercel backend project settings, add these environment variables:

```env
GOOGLE_CLIENT_ID=851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_PROJECT_ID=email-reminder-system-479300
SECRET_KEY=smart-job-reminder-secret-key-2025-secure-oauth-sessions
BACKEND_URL=https://se-project-akel.vercel.app
FRONTEND_URL=https://your-frontend-url.vercel.app
GEMINI_API_KEY=AIzaSyD4IOjEEM07dAwXSVFxlvRumWxotqbZMQs
LLM_PROVIDER=gemini
DEFAULT_TIMEZONE=Asia/Kolkata
FLASK_DEBUG=false
MAX_EMAILS_TO_PROCESS=50
DAYS_BACK_TO_SCAN=7
```

### Step 3: Update Frontend .env

Update `frontend/.env` with your actual frontend URL after deployment:

```env
VITE_GOOGLE_CLIENT_ID=851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com
VITE_API_BASE_URL=https://se-project-akel.vercel.app/
VITE_FRONTEND_URL=https://your-frontend-url.vercel.app
```

### Step 4: Redeploy Both Projects

1. **Backend:** Push changes to trigger Vercel rebuild
2. **Frontend:** Push changes to trigger Vercel rebuild

---

## 🔍 Testing the Deployment

### Test OAuth Flow:

1. Visit your frontend URL
2. Click "Sign in with Google"
3. You should be redirected to Google OAuth
4. After authentication, redirected back to your app

### Debug OAuth Issues:

If OAuth fails, check:

- ✅ Google Cloud Console has correct redirect URIs
- ✅ Vercel environment variables are set correctly
- ✅ Both frontend and backend URLs are correct in `.env`
- ✅ CORS origins include your frontend URL

### Check Backend Logs:

In Vercel dashboard:

1. Go to your backend project
2. Click **Deployments**
3. Click latest deployment
4. Click **View Function Logs**

Look for CORS and OAuth debug messages.

---

## 🐛 Common Issues & Fixes

### Issue 1: CORS Errors

**Error:** `Access to fetch has been blocked by CORS policy`

**Fix:**

1. Verify `FRONTEND_URL` is set in backend Vercel environment variables
2. Redeploy backend after setting environment variables
3. Check browser console for exact origin being blocked

### Issue 2: OAuth Redirect Mismatch

**Error:** `redirect_uri_mismatch`

**Fix:**

1. Ensure redirect URI in Google Console exactly matches:
   ```
   https://se-project-akel.vercel.app/auth/google/callback
   ```
2. No trailing slash
3. Must be HTTPS in production

### Issue 3: Session Cookie Issues

**Error:** Cookies not being set/read

**Fix:**

- Verify `SESSION_COOKIE_SAMESITE = 'None'` and `SESSION_COOKIE_SECURE = True`
- Both are required for cross-origin cookies
- Browser must support third-party cookies

### Issue 4: Environment Variables Not Loading

**Error:** Using default localhost URLs in production

**Fix:**

1. Set environment variables in Vercel project settings (not in `.env` file)
2. Redeploy after adding variables
3. Check logs to verify variables are loaded

---

## 📝 Local Development vs Production

### Local Development:

```env
BACKEND_URL=http://localhost:5000
FRONTEND_URL=http://localhost:3000
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_SAMESITE=Lax
```

### Production (Vercel):

```env
BACKEND_URL=https://se-project-akel.vercel.app
FRONTEND_URL=https://your-frontend-url.vercel.app
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=None
```

---

## ✅ Deployment Checklist

- [ ] Update Google Cloud Console with Vercel redirect URIs
- [ ] Set all environment variables in Vercel backend
- [ ] Update `FRONTEND_URL` in backend `.env` (Vercel settings)
- [ ] Update `VITE_API_BASE_URL` in frontend `.env`
- [ ] Update `VITE_FRONTEND_URL` in frontend `.env`
- [ ] Push changes to trigger Vercel rebuilds
- [ ] Test OAuth login flow
- [ ] Test email scanning
- [ ] Test calendar integration
- [ ] Verify CORS is working

---

## 🎯 Next Steps

1. **Get your frontend Vercel URL** after deployment
2. **Update the FRONTEND_URL** in:
   - Backend `.env` file (Vercel environment variables)
   - Frontend `.env` file (replace `your-frontend-url.vercel.app`)
3. **Add URLs to Google Console** (Step 1 above)
4. **Redeploy both projects**
5. **Test the OAuth flow**

---

## 📞 Support

If you encounter issues:

1. Check Vercel function logs
2. Check browser console for errors
3. Verify all environment variables are set correctly
4. Ensure Google Console has correct URIs
