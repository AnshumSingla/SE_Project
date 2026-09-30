import React, { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

const STORAGE_KEY = 'jobReminderUser'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000').replace(/\/$/, '')

const readStoredUser = () => {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    // Only accept the current shape: an identity plus the signed API token.
    return stored?.apiToken && stored?.email ? stored : null
  } catch {
    return null
  }
}

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate()
  const [user, setUser] = useState(readStoredUser)
  const [loading, setLoading] = useState(false)

  const clearSession = () => {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem('lastSync')
    setUser(null)
  }

  // A token can expire or stop being valid (e.g. the owner changed): check it once on load.
  useEffect(() => {
    if (!user?.apiToken) return
    let cancelled = false
    fetch(`${API_BASE_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${user.apiToken}` } })
      .then((res) => {
        if (res.status === 401 && !cancelled) {
          clearSession()
          navigate('/')
        }
      })
      .catch(() => {}) // offline: keep the session, requests will fail visibly
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // `result` is what the backend's sign-in popup posted: { user, apiToken }.
  const login = async (result) => {
    try {
      setLoading(true)
      const info = result?.user || {}
      if (!result?.apiToken || !info.email) throw new Error('Incomplete sign-in result')
      const userData = {
        id: info.sub || info.email,
        email: info.email,
        name: info.name || info.email,
        picture: info.picture || '',
        apiToken: result.apiToken,
        loginTime: new Date().toISOString()
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userData))
      setUser(userData)
      toast.success(`Welcome ${userData.name}!`)
      navigate('/dashboard')
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    clearSession()
    toast.success('Successfully logged out')
    navigate('/')
  }

  return <AuthContext.Provider value={{ user, login, logout, loading }}>{children}</AuthContext.Provider>
}
