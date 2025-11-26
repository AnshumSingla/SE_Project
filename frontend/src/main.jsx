import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App.jsx'
import './index.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '851801272480-re4eu38s6hqnl3jb00viarbmcu14n1fg.apps.googleusercontent.com'

console.log('🔑 Google Client ID:', GOOGLE_CLIENT_ID)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider 
      clientId={GOOGLE_CLIENT_ID}
      onScriptLoadError={() => console.error('Failed to load Google OAuth script')}
      onScriptLoadSuccess={() => console.log('✅ Google OAuth script loaded successfully')}
    >
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
)