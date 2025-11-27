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
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for stored user data on app load
    const storedUser = localStorage.getItem('jobReminderUser')
    console.log('🔍 AuthContext: Checking stored user...', storedUser ? 'Found' : 'None')
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        console.log('✅ AuthContext: User loaded from localStorage:', parsedUser.email)
        setUser(parsedUser)
      } catch (error) {
        console.error('❌ Error parsing stored user data:', error)
        localStorage.removeItem('jobReminderUser')
      }
    }
    setLoading(false)
  }, [])

  const login = async (credentialResponse) => {
    try {
      setLoading(true)
      
      // Handle demo mode
      if (credentialResponse.credential === "demo_token_for_testing") {
        const userData = {
          id: 'demo_user_123',
          email: 'demo@jobreminder.com',
          name: 'Demo User',
          picture: 'https://via.placeholder.com/96x96/00FFFF/1A1A1A?text=Demo',
          token: 'demo_token_for_testing',
          loginTime: new Date().toISOString(),
          isDemoMode: true
        }
        
        setUser(userData)
        localStorage.setItem('jobReminderUser', JSON.stringify(userData))
        toast.success(`Welcome to Demo Mode! 🚀`)
        navigate('/dashboard')
        return
      }
      
      // Handle server-side OAuth
      if (credentialResponse.credential === "server_auth_token") {
        const userInfo = credentialResponse.userInfo || {}
        const userData = {
          id: userInfo.sub || 'authenticated_user_456',
          email: userInfo.email || 'user@gmail.com',
          name: userInfo.name || 'Gmail User',
          picture: userInfo.picture || 'https://via.placeholder.com/96x96/00FF00/FFFFFF?text=✓',
          token: 'server_auth_token',
          accessToken: credentialResponse.accessToken || 'demo_access_token',
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