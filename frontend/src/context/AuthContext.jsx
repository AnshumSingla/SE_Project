import React, { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { googleLogout } from '@react-oauth/google'
import toast from 'react-hot-toast'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate()
  // Initialize user from localStorage immediately to prevent flash
  const [user, setUser] = useState(() => {
    try {
      const storedUser = localStorage.getItem('jobReminderUser')
      if (storedUser) {
        const parsedUser = JSON.parse(storedUser)
        console.log('🔍 AuthContext: User loaded from localStorage on init:', parsedUser.email)
        return parsedUser
      }
    } catch (error) {
      console.error('❌ Error parsing stored user data:', error)
      localStorage.removeItem('jobReminderUser')
    }
    return null
  })
  const [loading, setLoading] = useState(false)

  // Check and refresh token on mount if needed
  useEffect(() => {
    console.log('✅ AuthContext mounted, user:', user?.email || 'None')
    
    const checkAndRefreshToken = async () => {
      if (!user?.credentials?.refresh_token) return
      
      // Check if token might be expired (stored tokens from Google are typically 1 hour)
      const loginTime = user.loginTime ? new Date(user.loginTime).getTime() : 0
      const now = Date.now()
      const hoursSinceLogin = (now - loginTime) / (1000 * 60 * 60)
      
      // Proactively refresh if logged in more than 50 minutes ago
      if (hoursSinceLogin > 0.83) { // 50 minutes
        console.log('🔄 Token may be expired, refreshing proactively...')
        try {
          const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              refresh_token: user.credentials.refresh_token,
              client_id: user.credentials.client_id,
              client_secret: user.credentials.client_secret
            })
          })
          
          const data = await response.json()
          if (data.success) {
            const updatedUser = {
              ...user,
              credentials: {
                ...user.credentials,
                token: data.access_token
              },
              accessToken: data.access_token,
              loginTime: new Date().toISOString()
            }
            setUser(updatedUser)
            localStorage.setItem('jobReminderUser', JSON.stringify(updatedUser))
            console.log('✅ Token refreshed proactively on mount')
          }
        } catch (error) {
          console.error('⚠️ Proactive token refresh failed:', error)
        }
      }
    }
    
    checkAndRefreshToken()
  }, [])

  const login = async (credentialResponse) => {
    try {
      setLoading(true)
      
      // Handle server-side OAuth
      if (credentialResponse.credential === "server_auth_token") {
        const userInfo = credentialResponse.userInfo || {}
        const userData = {
          id: userInfo.sub || 'authenticated_user_456',
          email: userInfo.email || 'user@gmail.com',
          name: userInfo.name || 'Gmail User',
          picture: userInfo.picture || 'https://via.placeholder.com/96x96/00FF00/FFFFFF?text=\u2713',
          token: 'server_auth_token',
          accessToken: credentialResponse.accessToken || 'demo_access_token',
          credentials: credentialResponse.credentials || null,
          loginTime: new Date().toISOString(),
          isDemoMode: false,
          hasGmailAccess: true
        }
        
        console.log('💾 AuthContext: Saving user to localStorage:', userData.email)
        setUser(userData)
        localStorage.setItem('jobReminderUser', JSON.stringify(userData))
        console.log('✅ AuthContext: User saved, navigating to dashboard...')
        toast.success(`Welcome ${userData.name}! Gmail access enabled 📧`)
        
        // Use setTimeout to ensure state updates before navigation
        setTimeout(() => {
          navigate('/dashboard')
        }, 100)
        return
      }
      
      // Decode the JWT token to get user info
      const token = credentialResponse.credential
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      
      const userInfo = JSON.parse(jsonPayload)
      
      const userData = {
        id: userInfo.sub,
        email: userInfo.email,
        name: userInfo.name,
        picture: userInfo.picture,
        token: token,
        loginTime: new Date().toISOString(),
        isDemoMode: false
      }
      
      setUser(userData)
      localStorage.setItem('jobReminderUser', JSON.stringify(userData))
      
      toast.success(`Welcome back, ${userData.name}!`)
      navigate('/dashboard')
      
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    try {
      googleLogout()
      setUser(null)
      localStorage.removeItem('jobReminderUser')
      localStorage.removeItem('lastSync') // Clear sync timestamp on logout
      toast.success('Successfully logged out')
    } catch (error) {
      console.error('Logout error:', error)
      toast.error('Error during logout')
    }
  }

  const value = {
    user,
    login,
    logout,
    loading
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}