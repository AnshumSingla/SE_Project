import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: false, // auth is a Bearer token, not a cookie
  headers: {
    'Content-Type': 'application/json',
  },
})

// Every request carries the signed API token issued at sign-in. It proves identity
// only: Google credentials live on the server and never reach the browser.
api.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem('jobReminderUser') || '{}')
  if (user.apiToken) config.headers.Authorization = `Bearer ${user.apiToken}`
  return config
})

// A 401 means the token is missing, expired or not the owner's: sign in again.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem('jobReminderUser')) {
      localStorage.removeItem('jobReminderUser')
      localStorage.removeItem('lastSync')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

// Kept so call sites stay unchanged: nothing credential-like is sent in bodies or
// query strings any more. null = not signed in.
const getAuthPayload = () => {
  const user = JSON.parse(localStorage.getItem('jobReminderUser') || '{}')
  return user.apiToken ? {} : null
}
const toQueryAuth = () => ({})

const NOT_SIGNED_IN = 'Please sign in again to continue'

export const apiService = {
  // Health check
  healthCheck: async () => {
    try {
      const response = await api.get('/health')
      return response.data
    } catch (error) {
      throw new Error('API service unavailable')
    }
  },

  // Background-scan features: the server scans, adds confident events, queues the unsure ones.
  runScan: async (options = {}) => {
    if (!getAuthPayload()) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.post('/api/scan/run', { reset_seen: !!options.resetSeen })
      return response.data
    } catch (error) {
      const err = new Error(error.response?.data?.message || error.response?.data?.error || 'Scan failed')
      err.code = error.response?.data?.error
      throw err
    }
  },

  getReview: async () => {
    if (!getAuthPayload()) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.get('/api/review')
      return response.data
    } catch (error) {
      const err = new Error(error.response?.data?.message || error.response?.data?.error || 'Failed to load review queue')
      err.code = error.response?.data?.error
      throw err
    }
  },

  // action: 'accept' (create the calendar event) | 'dismiss' (never show again)
  resolveReview: async (eventId, action) => {
    if (!getAuthPayload()) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.post(`/api/review/${encodeURIComponent(eventId)}/${action}`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Action failed')
    }
  },

  // Delete-my-data: removes the stored token, profile and scan state, then revokes access.
  deleteAccount: async () => {
    if (!getAuthPayload()) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.delete('/api/account')
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Could not delete your data')
    }
  },

  // Profile (role, discipline, graduation year...) stored in the user's own Google Drive
  getProfile: async () => {
    const auth = getAuthPayload()
    if (!auth) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.get('/api/profile', { params: toQueryAuth(auth) })
      return response.data.profile
    } catch (error) {
      const err = new Error(error.response?.data?.message || error.response?.data?.error || 'Failed to load profile')
      err.code = error.response?.data?.error
      throw err
    }
  },

  saveProfile: async (profile) => {
    const auth = getAuthPayload()
    if (!auth) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.put('/api/profile', { profile, ...auth })
      return response.data.profile
    } catch (error) {
      const err = new Error(error.response?.data?.message || error.response?.data?.error || 'Failed to save profile')
      err.code = error.response?.data?.error
      throw err
    }
  },

  // Scan emails for job opportunities (read-only: returns candidates, writes nothing)
  scanEmails: async (userId, options = {}) => {
    const auth = getAuthPayload()
    if (!auth) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.post('/api/emails/scan', {
        user_id: userId,
        max_emails: options.max_emails || 50,
        days_back: options.days_back || 7,
        search_query: options.search_query || '',
        ...auth
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to scan emails')
    }
  },

  // Create calendar events for accepted candidates (idempotent on the backend)
  createCalendarReminders: async (userId, emails, reminderPreferences = {}) => {
    const auth = getAuthPayload()
    if (!auth) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.post('/api/calendar/reminders', {
        user_id: userId,
        emails: emails, // Full email objects with deadline info
        reminder_preferences: {
          default_reminders: reminderPreferences.default_reminders || [1440, 60],
          urgent_reminders: reminderPreferences.urgent_reminders || [10080, 1440, 60]
        },
        ...auth
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to create calendar reminders')
    }
  },

  // Get upcoming deadlines created by this app
  getUpcomingDeadlines: async (userId, daysAhead = 90) => {
    const auth = getAuthPayload()
    if (!auth) return { success: true, upcoming_events: [], note: NOT_SIGNED_IN }
    try {
      const response = await api.get('/api/calendar/upcoming', {
        params: { user_id: userId, days_ahead: daysAhead, ...toQueryAuth(auth) }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to get upcoming deadlines')
    }
  },

  // Delete calendar reminder
  deleteReminder: async (userId, eventId) => {
    const auth = getAuthPayload()
    if (!auth) throw new Error(NOT_SIGNED_IN)
    try {
      const response = await api.delete(`/api/calendar/reminders/${eventId}`, {
        params: { user_id: userId, ...toQueryAuth(auth) }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to delete reminder')
    }
  },



  // Chat with Gemini AI about upcoming deadlines
  chatWithAI: async (userId, message, events = [], history = []) => {
    try {
      const response = await api.post('/api/ai/chat', {
        user_id: userId,
        message,
        events,
        history
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to connect to AI assistant')
    }
  },

  // Get AI-generated priority plan for upcoming deadlines
  getPriorityPlan: async (userId, events = []) => {
    try {
      const response = await api.post('/api/ai/prioritize', {
        user_id: userId,
        events
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to get AI priority plan')
    }
  }
}

export default api