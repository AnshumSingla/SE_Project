import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true, // ✅ Enable credentials for CORS
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token if available
api.interceptors.request.use(
  (config) => {
    const user = JSON.parse(localStorage.getItem('jobReminderUser') || '{}')
    if (user.token) {
      config.headers.Authorization = `Bearer ${user.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('jobReminderUser')
      window.location.href = '/'
    }
    
    return Promise.reject(error)
  }
)

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

  // Scan emails for job opportunities
  scanEmails: async (userId, options = {}) => {
    try {
      const user = JSON.parse(localStorage.getItem('jobReminderUser') || '{}')
      const payload = {
        user_id: userId,
        max_emails: options.max_emails || 50,
        days_back: options.days_back || 7,
        search_query: options.search_query || ''
      }
      
      // Send full credentials if available, otherwise fallback to access token
      if (user.credentials) {
        payload.credentials = user.credentials
      } else {
        payload.access_token = user.accessToken || user.token || 'demo_token_for_testing'
      }
      
      const response = await api.post('/api/emails/scan', payload)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to scan emails')
    }
  },

  // Create calendar reminders
  createCalendarReminders: async (userId, emails, reminderPreferences = {}) => {
    try {
      const response = await api.post('/api/calendar/reminders', {
        user_id: userId,
        emails: emails, // Full email objects with deadline info
        reminder_preferences: {
          default_reminders: reminderPreferences.default_reminders || [1440, 60],
          urgent_reminders: reminderPreferences.urgent_reminders || [10080, 1440, 60]
        }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to create calendar reminders')
    }
  },

  // Get upcoming deadlines
  getUpcomingDeadlines: async (userId, daysAhead = 90) => {
    try {
      const user = JSON.parse(localStorage.getItem('jobReminderUser') || '{}')
      const params = {
        user_id: userId,
        days_ahead: daysAhead
      }
      
      // If we have full credentials, send them as JSON string
      if (user.credentials) {
        params.credentials = JSON.stringify(user.credentials)
      } else {
        params.access_token = user.accessToken || user.token
      }
      
      const response = await api.get('/api/calendar/upcoming', { params })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to get upcoming deadlines')
    }
  },

  // Delete calendar reminder
  deleteReminder: async (userId, eventId) => {
    try {
      const response = await api.delete(`/api/calendar/reminders/${eventId}`, {
        params: {
          user_id: userId
        }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to delete reminder')
    }
  },

  // Send notification
  sendNotification: async (userId, notificationData) => {
    try {
      const response = await api.post('/api/notifications/send', {
        user_id: userId,
        notification_type: notificationData.type,
        message: notificationData.message,
        event_id: notificationData.eventId,
        channels: notificationData.channels || ['push']
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to send notification')
    }
  },

  // Get dashboard analytics
  getDashboardAnalytics: async (userId, period = 'month') => {
    try {
      const response = await api.get('/api/analytics/dashboard', {
        params: {
          user_id: userId,
          period: period
        }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to get dashboard analytics')
    }
  },

  // Setup user credentials (for OAuth)
  setupUserCredentials: async (userId, credentials) => {
    try {
      const response = await api.post('/api/auth/setup', {
        user_id: userId,
        gmail_credentials: credentials.gmail,
        calendar_credentials: credentials.calendar
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Failed to setup user credentials')
    }
  }
}

export default api