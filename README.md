# 📅 Job Deadline Tracker

> Never miss a job application deadline again. Automatically scan your Gmail, extract deadlines, and sync with Google Calendar.

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://se-project-theta.vercel.app)
[![Backend](https://img.shields.io/badge/backend-vercel-black)](https://se-project-akel.vercel.app)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ Features

- 📧 **Smart Email Scanning** - AI-powered analysis of Gmail for job opportunities
- 📅 **Auto Calendar Sync** - Seamless Google Calendar integration
- 🔔 **Smart Reminders** - 1 week, 1 day, and 1 hour before deadlines
- 🔄 **Auto Token Refresh** - Stay logged in without re-authentication
- ⚡ **Real-time Updates** - Instant dashboard refresh after scanning
- 🎯 **Duplicate Detection** - Prevents creating duplicate calendar events
- 🌐 **Serverless Architecture** - Deployed on Vercel with zero database

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   React     │ ───▶ │   Flask     │ ───▶ │   Google     │
│   Frontend  │      │   Backend   │      │     APIs     │
│  (Vercel)   │ ◀─── │  (Vercel)   │ ◀─── │ (Gmail/Cal)  │
└─────────────┘      └─────────────┘      └──────────────┘
```

### Tech Stack

**Frontend:**
- React + Vite
- Tailwind CSS + Framer Motion
- React Router + Context API
- Axios for API calls

**Backend:**
- Flask (Python)
- Google OAuth 2.0
- Gmail API + Calendar API
- Serverless on Vercel

**Storage:**
- Client-side: localStorage
- Deadlines: Google Calendar
- No database required

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- Google Cloud account
- Vercel account (for deployment)

### 1. Clone Repository

```bash
git clone https://github.com/AnshumSingla/SE_Project.git
cd SE_Project
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create .env file
cp .env.template .env

# Configure Google OAuth in .env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
BACKEND_URL=http://localhost:5000
FRONTEND_URL=http://localhost:3000
```

### 3. Frontend Setup

```bash
cd frontend
npm install

# Create .env file
echo "VITE_API_BASE_URL=http://localhost:5000" > .env
```

### 4. Google Cloud Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Gmail API** and **Google Calendar API**
4. Create **OAuth 2.0 Client ID** (Web application)
5. Add authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback`
   - `https://your-backend.vercel.app/auth/google/callback`
6. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - `https://your-frontend.vercel.app`

### 5. Run Locally

```bash
# Terminal 1 - Backend
python api_service.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit `http://localhost:3000` 🚀

## 📱 Usage

1. **Sign in with Google** - OAuth authentication
2. **Auto-sync on load** - Dashboard automatically loads calendar events
3. **Scan emails** - Click "Scan Recent Emails" to find new deadlines
4. **View deadlines** - See all upcoming deadlines in the dashboard
5. **Delete events** - Remove deadlines directly from the UI

### Smart Features

- **24-hour scan cooldown** - Prevents excessive API calls
- **Manual scan override** - Force scan anytime with the scan button
- **Automatic token refresh** - Stays logged in indefinitely
- **Duplicate prevention** - Won't create duplicate calendar events

## 🎯 AI-Powered Detection

The system identifies:

- 📝 Job application deadlines
- 🎯 Interview invitations
- 💻 Coding assessments
- ✉️ Response requirements
- 📅 Career events
- 🎓 Academic deadlines

### Date Recognition

- Absolute dates: "December 15, 2025"
- Relative dates: "in 2 weeks", "next Monday"
- Implicit deadlines: "apply before Friday"
- Forwarded email handling

## 🚀 Deployment

### Deploy to Vercel

**Backend:**
```bash
vercel --prod
```

Environment variables needed:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `BACKEND_URL` (your Vercel backend URL)
- `FRONTEND_URL` (your Vercel frontend URL)

**Frontend:**
```bash
cd frontend
vercel --prod
```

Environment variables needed:
- `VITE_API_BASE_URL` (your Vercel backend URL)

## 🛠️ Troubleshooting

### OAuth Issues
- Check authorized redirect URIs in Google Cloud Console
- Verify client ID and secret in environment variables
- Clear browser localStorage and try again

### No Events Showing
- Log out and log back in to refresh credentials
- Check browser console for API errors
- Verify Google Calendar API is enabled

### Duplicate Events
- Fixed automatically - backend checks for duplicates before creating

## 🔒 Security

- ✅ OAuth 2.0 authentication
- ✅ Automatic token refresh
- ✅ No passwords stored
- ✅ Client-side credential storage
- ✅ CORS configured properly
- ✅ Environment variables for secrets

## 📄 License

MIT License - feel free to use for personal or commercial projects

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📧 Contact

For questions or support, open an issue on GitHub

---

**Built with ❤️ for job seekers everywhere**
