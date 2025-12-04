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
          accessToken: event.data.accessToken,
          credentials: event.data.credentials  // Include full credentials with expiry_time
        }
        console.log('🔐 Calling login with credentials for:', event.data.user?.email)
        console.log('⏱️  Token expiry time:', event.data.credentials?.expiry_time)
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
    console.error('Google Login Failed')
    alert('Google authentication failed. Please try again.')
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
        <motion.div 
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl"
          animate={{
            y: [0, -20, 0],
            x: [0, 10, 0],
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.5, 0.3]
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div 
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-500/10 rounded-full blur-3xl"
          animate={{
            y: [0, 20, 0],
            x: [0, -10, 0],
            scale: [1, 1.15, 1],
            opacity: [0.4, 0.6, 0.4]
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
        />
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
            <motion.div 
              className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center shadow-lg shadow-primary-500/50"
              whileHover={{ 
                rotate: [0, -10, 10, -10, 0],
                scale: 1.1
              }}
              transition={{ 
                type: "spring",
                stiffness: 400,
                damping: 10
              }}
            >
              <Zap className="w-6 h-6 text-dark-500" />
            </motion.div>
            <h1 className="text-2xl font-bold text-glow">Smart Job Reminder</h1>
          </div>
          
          <motion.div
            whileHover={{ 
              scale: 1.08,
              boxShadow: "0 0 20px rgba(0, 255, 255, 0.3)"
            }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
            className="flex items-center space-x-2 glass-card px-4 py-2 rounded-full cursor-pointer"
          >
            <motion.div
              whileHover={{ rotate: [0, -15, 15, 0] }}
              transition={{ duration: 0.4 }}
            >
              <Shield className="w-4 h-4 text-primary-500" />
            </motion.div>
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
                  <motion.div
                    animate={{ 
                      rotate: [0, 5, -5, 0],
                      scale: [1, 1.2, 1]
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      repeatDelay: 1
                    }}
                  >
                    <Sparkles className="w-6 h-6 text-primary-500 drop-shadow-[0_0_8px_rgba(0,255,255,0.6)]" />
                  </motion.div>
                  <span className="text-primary-500 font-medium">AI-Powered Job Tracking</span>
                </motion.div>
                
                <h2 className="text-5xl lg:text-6xl font-bold leading-tight">
                  <motion.span 
                    className="text-glow inline-block"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4, duration: 0.6 }}
                  >
                    Never Miss
                  </motion.span>
                  <br />
                  <motion.span 
                    className="bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 bg-clip-text text-transparent inline-block bg-[length:200%_auto]"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ 
                      opacity: 1, 
                      x: 0,
                      backgroundPosition: ['0% center', '100% center', '0% center']
                    }}
                    transition={{ 
                      opacity: { delay: 0.5, duration: 0.6 },
                      x: { delay: 0.5, duration: 0.6 },
                      backgroundPosition: { duration: 3, repeat: Infinity, ease: "linear" }
                    }}
                  >
                    A Job Deadline
                  </motion.span>
                  <br />
                  <motion.span 
                    className="text-text-primary inline-block"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6, duration: 0.6 }}
                  >
                    Again
                  </motion.span>
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
                <motion.div 
                  className="inline-block p-1 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 rounded-xl bg-[length:200%_auto]"
                  animate={{
                    backgroundPosition: ['0% center', '100% center', '0% center']
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                >
                  <div className="bg-dark-500 rounded-lg p-6">
                     {/* Thapar Email Notice */}
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
                      <p className="text-red-400 text-sm text-center font-medium">
                        ⓘ Please use your Thapar email to sign in
                      </p>
                      <p className="text-red-400/70 text-xs text-center mt-1">
                        Only Thapar University emails are allowed to access this service
                      </p>
                    </div>
                    <div className="text-center mb-4">
                      <h3 className="text-lg font-semibold text-text-primary mb-2">
                        Get Started in Seconds
                      </h3>
                      <p className="text-text-secondary text-sm">
                        Sign in with Google to access your personalized dashboard
                      </p>
                    </div>
                    
                    <motion.button
                      onClick={handleServerAuth}
                      className="w-full bg-white text-gray-800 py-3 px-6 rounded-lg font-medium border border-gray-300 flex items-center justify-center space-x-3"
                      whileHover={{ 
                        scale: 1.02,
                        y: -2,
                        boxShadow: "0 10px 30px -5px rgba(0, 255, 255, 0.3)"
                      }}
                      whileTap={{ scale: 0.98, y: 0 }}
                      transition={{ type: "spring", stiffness: 400, damping: 17 }}
                    >
                      <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                      <span>Sign in with Google</span>
                    </motion.button>
                  </div>
                </motion.div>
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
                  whileHover={{ 
                    scale: 1.03, 
                    y: -8,
                    boxShadow: "0 20px 40px -10px rgba(0, 255, 255, 0.4)",
                    borderColor: "rgba(0, 255, 255, 0.5)"
                  }}
                  transition={{ 
                    default: { duration: 0.6, delay: 0.6 + index * 0.1 },
                    scale: { type: "spring", stiffness: 300, damping: 20 },
                    y: { type: "spring", stiffness: 300, damping: 20 }
                  }}
                  className="glass-card p-6 rounded-xl neon-glow border border-transparent cursor-pointer"
                >
                  <div className="flex items-start space-x-4">
                    <motion.div 
                      className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center text-primary-500"
                      whileHover={{ 
                        rotate: [0, -10, 10, -10, 0],
                        scale: 1.1
                      }}
                      transition={{ duration: 0.5 }}
                    >
                      {feature.icon}
                    </motion.div>
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
