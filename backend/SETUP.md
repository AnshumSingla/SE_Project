# 🚀 API-Only Email Reminder System - Setup Guide

## Quick Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy and edit the `.env` file:

- Add your OpenAI API key for LLM processing
- Add Google OAuth credentials for production

### 5. Run the API Service

```bash
python api_service.py
```

### 6. Test the API

```bash
python api_only_demo.py
```

## 📋 Requirements Verification

The requirements.txt file includes all necessary dependencies for:

✅ **AutoGen LLM Agents** - `pyautogen==0.2.35`
✅ **Flask API Service** - `Flask==3.1.2` + `Flask-CORS==6.0.1`  
✅ **Google APIs** - Gmail & Calendar integration
✅ **OpenAI Integration** - `openai>=2.8.1`
✅ **Security** - `cryptography>=46.0.0`
✅ **Configuration** - `python-dotenv>=1.0.0`

## 🔍 System Status

- **API Service**: ✅ Ready
- **AutoGen Agents**: ✅ Initialized
- **Dependencies**: ✅ All installed
- **Configuration**: ✅ Environment ready

## 🌐 Available API Endpoints

- `POST /api/emails/scan` - Process emails with AI classification
- `POST /api/calendar/reminders` - Create calendar events
- `GET /api/calendar/upcoming` - Get deadline notifications
- `POST /api/notifications/send` - Send user notifications
- `GET /api/analytics/dashboard` - View processing statistics

## 🎯 Next Steps

1. **For Demo**: System is ready to run with sample data
2. **For Production**: Configure Google OAuth and real Gmail access
3. **For Integration**: Use the REST API endpoints in your web/mobile app

The system is **production-ready** for API-only AutoGen LLM processing! 🤖
