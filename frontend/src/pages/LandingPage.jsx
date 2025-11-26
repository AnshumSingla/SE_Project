import { motion } from 'framer-motion'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'
import { Calendar, Mail, Bell, Sparkles, Zap, Shield } from 'lucide-react'

const LandingPage = () => {
  const { login } = useAuth()

  const handleGoogleSuccess = (credentialResponse) => {
    login(credentialResponse)
  }

  const handleGoogleError = () => {
    console.error('Google Login Failed')
    // For development, let's show the error and offer a demo mode
    alert('Google OAuth configuration issue detected. Please check the console for setup instructions.')
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
                      <p className="text-text-secondary text-sm">
                        Sign in with Google to access your personalized dashboard
                      </p>
                    </div>
                    
                    <GoogleLogin
                      onSuccess={handleGoogleSuccess}
                      onError={handleGoogleError}
                      theme="filled_black"
                      shape="rectangular"
                      size="large"
                      width="100%"
                      useOneTap={false}
                      auto_select={false}
                      flow="implicit"
                      type="standard"
                    />
                    
                    <div className="mt-4 text-center">
                      <div className="flex items-center my-4">
                        <div className="flex-1 border-t border-gray-600"></div>
                        <span className="px-3 text-gray-400 text-sm">or</span>
                        <div className="flex-1 border-t border-gray-600"></div>
                      </div>
                      
                      <button
                        onClick={handleDemoLogin}
                        className="w-full bg-gradient-to-r from-primary-500/20 to-accent-500/20 hover:from-primary-500/30 hover:to-accent-500/30 border border-primary-500/50 text-text-primary py-3 px-6 rounded-lg transition-all duration-300 font-medium"
                      >
                        🚀 Try Demo Mode
                      </button>
                      <p className="text-xs text-text-muted mt-2">
                        Experience the system with sample data
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