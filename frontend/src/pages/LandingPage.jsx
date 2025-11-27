import { motion } from 'framer-motion'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'
import { Calendar, Mail, Bell, Sparkles, Zap, Shield } from 'lucide-react'

const LandingPage = () => {
  const { login } = useAuth()

  const handleGoogleSuccess = (credentialResponse) => {
    login(credentialResponse)
  }

  const handleServerAuth = () => {
    // Listen for OAuth callback
    const handleMessage = (event) => {
      console.log('🔔 Received postMessage from:', event.origin)
      console.log('📦 Message data:', event.data)
      
      // Accept messages from backend (localhost or Vercel)
      const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
      const allowedOrigins = ['http://localhost:5000', backendUrl.replace(/\/$/, '')]
      
      if (!allowedOrigins.some(origin => event.origin.startsWith(origin))) {
        console.log('⚠️ Ignoring message from:', event.origin)
        return
      }
      
      console.log('✅ Message from allowed origin, processing...')
      
      if (event.data.success) {
        console.log('🎉 OAuth success! Creating credentials...')
        // Create credential response with real user data and access token
        const mockCredential = {
          credential: "server_auth_token",
          userInfo: event.data.user,
          accessToken: event.data.accessToken
        }
        console.log('🔐 Calling login with credentials for:', event.data.user?.email)
        window.removeEventListener('message', handleMessage)
        login(mockCredential)
      } else {
        console.error('❌ Server OAuth failed:', event.data.error)
        alert('Authentication failed: ' + event.data.error)
        window.removeEventListener('message', handleMessage)
      }
    }
    
    window.addEventListener('message', handleMessage)
    
    // Open OAuth in popup with proper dimensions
    const width = 500
    const height = 600
    const left = window.screen.width / 2 - width / 2
    const top = window.screen.height / 2 - height / 2
    
    // Use environment variable for backend URL (supports both local and Vercel)
    const backendUrl = import.meta.env.VITE_API_BASE_URL
    
    window.open(
      `${backendUrl}/auth/google`, 
      'Google OAuth',
      `width=${width},height=${height},left=${left},top=${top}`
    )
  }

  const handleGoogleError = () => {
    console.error('Google Login Failed - Redirect URI Mismatch')
    console.log('🔧 To fix this OAuth error:')
    console.log('1. Go to: https://console.cloud.google.com/apis/credentials')
    console.log('2. Edit your OAuth Client ID')
    console.log('3. Add http://localhost:3000 to Authorized JavaScript Origins')
    console.log('4. Add http://localhost:3000 to Authorized Redirect URIs')
    console.log('5. Save and wait 5 minutes')
    console.log('📱 For now, use Demo Mode to test the system!')
  }

  const handleDemoLogin = () => {
    // Create a demo user for testing
    const demoCredentials = {
      credential: "demo_token_for_testing"
    }
    login(demoCredentials)
  }

  const features = [
    {
      icon: <Mail className="w-8 h-8" />,
      title: "Smart Email Scanning",
      description: "AI-powered analysis of your emails to detect job opportunities and deadlines"
    },
    {
      icon: <Calendar className="w-8 h-8" />,
      title: "Calendar Integration",
      description: "Seamless synchronization with your Google Calendar for deadline tracking"
    },
    {
      icon: <Bell className="w-8 h-8" />,
      title: "Intelligent Reminders", 
      description: "Customizable reminder frequency to ensure you never miss important deadlines"
    }
  ]

  return (
    <div className="min-h-screen bg-dark-500 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-dark-500 via-dark-400 to-dark-300">
        <div className="absolute inset-0 bg-starfield opacity-20"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-500/10 rounded-full blur-3xl animate-pulse-slow delay-1000"></div>
      </div>

      <div className="relative z-10 container mx-auto px-6 py-12 min-h-screen flex flex-col">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="flex items-center justify-between mb-12"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6 text-dark-500" />
            </div>
            <h1 className="text-2xl font-bold text-glow">Smart Job Reminder</h1>
          </div>
          
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="flex items-center space-x-2 glass-card px-4 py-2 rounded-full"
          >
            <Shield className="w-4 h-4 text-primary-500" />
            <span className="text-sm text-text-secondary">Secure with Google</span>
          </motion.div>
        </motion.header>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center">
          <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
            
            {/* Left Column - Content */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="space-y-8"
            >
              <div className="space-y-6">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.3 }}
                  className="flex items-center space-x-2"
                >
                  <Sparkles className="w-6 h-6 text-primary-500" />
                  <span className="text-primary-500 font-medium">AI-Powered Job Tracking</span>
                </motion.div>
                
                <h2 className="text-5xl lg:text-6xl font-bold leading-tight">
                  <span className="text-glow">Never Miss</span>
                  <br />
                  <span className="bg-gradient-to-r from-primary-500 to-accent-500 bg-clip-text text-transparent">
                    A Job Deadline
                  </span>
                  <br />
                  <span className="text-text-primary">Again</span>
                </h2>
                
                <p className="text-xl text-text-secondary leading-relaxed">
                  Intelligent email analysis meets smart calendar integration. 
                  Let AI scan your inbox, detect job opportunities, and automatically 
                  schedule reminders so you can focus on landing your dream job.
                </p>
              </div>

              {/* Sign In Button */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.5 }}
                className="pt-4"
              >
                <div className="inline-block p-1 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl">
                  <div className="bg-dark-500 rounded-lg p-6">
                    <div className="text-center mb-4">
                      <h3 className="text-lg font-semibold text-text-primary mb-2">
                        Get Started in Seconds
                      </h3>
                      <p className="text-text-secondary text-sm mb-2">
                        Sign in with Google to access your personalized dashboard
                      </p>
                      <div className="text-xs text-yellow-400 bg-yellow-400/10 border border-yellow-400/30 rounded-md p-2">
                        ⚠️ OAuth setup required in Google Cloud Console<br/>
                        Use Demo Mode below to test immediately!
                      </div>
                    </div>
                    
                    <button
                      onClick={handleServerAuth}
                      className="w-full bg-white hover:bg-gray-50 text-gray-800 py-3 px-6 rounded-lg transition-all duration-300 font-medium border border-gray-300 flex items-center justify-center space-x-3"
                    >
                      <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                      <span>Sign in with Google</span>
                    </button>
                    
                    <div className="mt-4 text-center">
                      <div className="flex items-center my-4">
                        <div className="flex-1 border-t border-gray-600"></div>
                        <span className="px-3 text-gray-400 text-sm">or</span>
                        <div className="flex-1 border-t border-gray-600"></div>
                      </div>
                      
                      <button
                        onClick={handleDemoLogin}
                        className="w-full bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 text-dark-500 py-3 px-6 rounded-lg transition-all duration-300 font-bold shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
                      >
                        🚀 Enter Demo Mode - Skip OAuth Setup
                      </button>
                      <p className="text-xs text-text-secondary mt-2 text-center">
                        Full system experience with realistic job emails
                        <br />
                        <span className="text-primary-400">No Google setup required!</span>
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>

            {/* Right Column - Features */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="space-y-6"
            >
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.6 + index * 0.1 }}
                  whileHover={{ scale: 1.02, y: -5 }}
                  className="glass-card p-6 rounded-xl neon-glow hover:shadow-xl transition-all duration-300"
                >
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center text-primary-500">
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">
                        {feature.title}
                      </h3>
                      <p className="text-text-secondary">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.9 }}
                className="glass-card p-6 rounded-xl mt-8"
              >
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-primary-500">99%</div>
                    <div className="text-sm text-text-secondary">Accuracy Rate</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-primary-500">24/7</div>
                    <div className="text-sm text-text-secondary">Monitoring</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-primary-500">∞</div>
                    <div className="text-sm text-text-secondary">Deadlines Tracked</div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1 }}
          className="text-center text-text-muted text-sm"
        >
          <p>Powered by advanced AI • Secure Google Integration • Privacy First</p>
        </motion.footer>
      </div>
    </div>
  )
}

export default LandingPage