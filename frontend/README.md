# Smart Job Reminder Frontend

A modern, dark-themed React web application for intelligent job deadline tracking and management.

## Features

✨ **Smart Email Scanning** - AI-powered analysis to detect job opportunities and deadlines  
🗓️ **Calendar Integration** - Visual timeline of all your job deadlines  
🔔 **Intelligent Reminders** - Customizable notification frequency  
🔐 **Google OAuth** - Secure authentication and calendar access  
🌙 **Dark Theme** - Beautiful futuristic UI with neon accents  
📱 **Responsive Design** - Works perfectly on desktop and mobile

## Tech Stack

- **React 18** + **Vite** for fast development
- **Tailwind CSS** for styling with custom dark theme
- **Framer Motion** for smooth animations
- **React Big Calendar** for calendar visualization
- **Google OAuth 2.0** for authentication
- **Axios** for API communication

## Quick Start

### Prerequisites

- Node.js 16+ installed
- Your backend API service running on `http://localhost:5000`

### Installation

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Google OAuth Client ID:

   ```
   VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id_here
   ```

3. **Start development server:**

   ```bash
   npm run dev
   ```

4. **Open in browser:**
   Visit `http://localhost:3000`

## Environment Variables

| Variable                | Description                | Required                                 |
| ----------------------- | -------------------------- | ---------------------------------------- |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth 2.0 Client ID | ✅ Yes                                   |
| `VITE_API_BASE_URL`     | Backend API URL            | No (defaults to `http://localhost:5000`) |

## API Integration

The frontend communicates with your Flask API backend through these endpoints:

- `POST /api/emails/scan` - Scan emails for job opportunities
- `GET /api/calendar/upcoming` - Get upcoming deadlines
- `POST /api/calendar/reminders` - Create calendar reminders
- `POST /api/notifications/send` - Send notifications

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Calendar API
4. Create OAuth 2.0 credentials
5. Add authorized JavaScript origins:
   - `http://localhost:3000` (development)
   - Your production domain

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Navbar.jsx      # Top navigation bar
│   ├── EmailScanner.jsx # Email scanning interface
│   ├── CustomReminderModal.jsx # Add custom reminders
│   ├── ReminderSettings.jsx # Frequency settings
│   ├── StatsCards.jsx  # Dashboard statistics
│   └── UpcomingDeadlines.jsx # Deadline list
├── context/            # React context providers
│   └── AuthContext.jsx # Authentication state
├── pages/              # Main application pages
│   ├── LandingPage.jsx # Welcome/login page
│   └── HomePage.jsx    # Main dashboard
├── services/           # API communication
│   └── apiService.js   # Backend API client
├── App.jsx            # Main app component
└── main.jsx           # Application entry point
```

## Customization

### Theme Colors

Edit `tailwind.config.js` to customize the color scheme:

```js
colors: {
  primary: {
    500: '#00FFFF', // Main cyan
  },
  accent: {
    500: '#00ADB5', // Main accent
  },
  dark: {
    500: '#0D0D0D', // Background
    400: '#1A1A1A', // Cards
  }
}
```

### API Endpoints

Modify `src/services/apiService.js` to add new API endpoints or change request formats.

## Deployment

### Build for Production

```bash
npm run build
```

### Deploy to Vercel

1. Connect your GitHub repository to Vercel
2. Add environment variables in Vercel dashboard
3. Deploy automatically on push to main branch

### Deploy to Netlify

1. Connect repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variables

## Performance

- **Vite** provides lightning-fast hot reload
- **Code splitting** for optimal bundle sizes
- **Image optimization** with modern formats
- **Lazy loading** for calendar components

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is part of the Smart Job Reminder system. See the main project for licensing information.
