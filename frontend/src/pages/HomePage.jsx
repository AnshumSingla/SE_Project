import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Calendar, momentLocalizer } from 'react-big-calendar'
import moment from 'moment'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import EmailScanner from '../components/EmailScanner'
import CustomReminderModal from '../components/CustomReminderModal'
import StatsCards from '../components/StatsCards'
import UpcomingDeadlines from '../components/UpcomingDeadlines'
import { apiService } from '../services/apiService'
import toast from 'react-hot-toast'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import '../styles/calendar.css'

const localizer = momentLocalizer(moment)

const HomePage = () => {
  const { user } = useAuth()
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showReminderModal, setShowReminderModal] = useState(false)
  const [calendarView, setCalendarView] = useState('month')
  const [selectedDate, setSelectedDate] = useState(new Date())

  useEffect(() => {
    if (user) initializeSync()
  }, [user])

  const initializeSync = async () => {
    setLoading(true)

    try {
      // Check if we need to scan Gmail (once per day)
      const lastSync = localStorage.getItem('lastSync')
      const nowTimestamp = Date.now()
      const oneDay = 24 * 60 * 60 * 1000 // 1 day in ms
      const shouldScanEmails = !lastSync || nowTimestamp - lastSync > oneDay
      
      // 1️⃣ Load all existing reminders from Google Calendar
      const calendarResponse = await apiService.getUpcomingDeadlines(user.id)
      const now = new Date()
      const existingEvents = calendarResponse.success
        ? calendarResponse.upcoming_events
            .map(event => ({
              id: event.event_id,
              title: event.title.trim(),
              start: new Date(event.start_time),
              end: new Date(event.start_time),
              resource: {
                type: event.deadline_type,
                urgency: event.urgency,
                originalEmail: event.original_email,
                daysUntil: event.days_until
              }
            }))
            .filter(e => e.start >= now)
        : []

      setEvents(existingEvents)
      console.log(`✅ Loaded ${existingEvents.length} existing Google Calendar reminders.`)

      // 2️⃣ Only scan Gmail if it's been more than 24 hours
      if (!shouldScanEmails) {
        console.log('✅ Skipping Gmail scan – recent session')
        toast.dismiss()
        toast.success('Calendar synced successfully 🎉')
        setLoading(false)
        return
      }
      
      console.log('🔄 Long gap detected – scanning Gmail for new emails...')
      toast.loading('Syncing latest emails...')
      const scanResults = await apiService.scanEmails(user.id)

      if (!scanResults.success) {
        toast.dismiss()
        toast.error('Failed to scan Gmail for new deadlines')
        setLoading(false)
        return
      }

      // 3️⃣ Filter out expired and duplicate deadlines
      const futureEmails = scanResults.emails.filter(email => {
        if (!email.deadline?.has_deadline || !email.deadline?.date) return false
        const date = new Date(email.deadline.date)
        return date >= now
      })

      // 4️⃣ Identify new reminders not already on the calendar
      const existingTitles = new Set(existingEvents.map(e => e.title.toLowerCase().replace(/📧\s*/g, '')))
      const newDeadlines = futureEmails.filter(email => {
        const normalizedTitle = email.subject.toLowerCase().trim()
        return !Array.from(existingTitles).some(title => 
          title.includes(normalizedTitle) || normalizedTitle.includes(title)
        )
      })

      console.log(`📬 Found ${newDeadlines.length} new deadlines not in Google Calendar.`)

      if (newDeadlines.length === 0) {
        toast.dismiss()
        toast.success('All reminders are already synced 🎉')
        setLoading(false)
        return
      }

      // 5️⃣ Create new events on Google Calendar
      await apiService.createCalendarReminders(user.id, newDeadlines, {
        default_reminders: [10080, 1440], // 1 week and 1 day before
        urgent_reminders: [10080, 1440, 60]
      })

      // 6️⃣ Add to local state
      const newEvents = newDeadlines.map(email => {
        const dateStr = email.deadline.date
        const timeStr = email.deadline.time || '23:59:00'
        const deadlineDate = new Date(`${dateStr}T${timeStr}`)
        return {
          id: email.email_id,
          title: `📧 ${email.subject}`,
          start: deadlineDate,
          end: deadlineDate,
          resource: {
            type: email.deadline.type || 'application',
            urgency: email.classification.urgency || 'medium',
            originalEmail: {
              subject: email.subject,
              sender: email.sender,
              snippet: email.snippet
            },
            daysUntil: email.deadline.urgency_days || 0
          }
        }
      })

      setEvents(prev => {
        const all = [...prev, ...newEvents]
        const unique = all.filter(
          (e, i, arr) =>
            i === arr.findIndex(x => x.title === e.title && x.start.getTime() === e.start.getTime())
        )
        return unique.filter(e => e.start >= now)
      })

      // Update last sync timestamp
      localStorage.setItem('lastSync', nowTimestamp.toString())

      toast.dismiss()
      toast.success(`Synced ${newDeadlines.length} new deadlines to calendar! 📅`)
    } catch (err) {
      console.error('❌ Error syncing reminders:', err)
      toast.dismiss()
      toast.error('Failed to sync reminders')
    } finally {
      setLoading(false)
    }
  }

  const handleEmailScanComplete = async () => {
    // Force a fresh scan, bypassing the 24-hour check
    await forceScan()
  }

  const forceScan = async () => {
    setLoading(true)
    
    try {
      // 1️⃣ Load all existing reminders from Google Calendar
      const calendarResponse = await apiService.getUpcomingDeadlines(user.id)
      const now = new Date()
      const existingEvents = calendarResponse.success
        ? calendarResponse.upcoming_events
            .map(event => ({
              id: event.event_id,
              title: event.title.trim(),
              start: new Date(event.start_time),
              end: new Date(event.start_time),
              resource: {
                type: event.deadline_type,
                urgency: event.urgency,
                originalEmail: event.original_email,
                daysUntil: event.days_until
              }
            }))
            .filter(e => e.start >= now)
        : []

      setEvents(existingEvents)
      console.log(`✅ Loaded ${existingEvents.length} existing Google Calendar reminders.`)

      // 2️⃣ Force Gmail scan (bypass 24-hour check)
      console.log('🔄 Force scanning Gmail for new emails...')
      toast.loading('Scanning emails...')
      const scanResults = await apiService.scanEmails(user.id)

      if (!scanResults.success) {
        toast.dismiss()
        toast.error('Failed to scan Gmail for new deadlines')
        setLoading(false)
        return
      }

      // 3️⃣ Filter out expired and duplicate deadlines
      const futureEmails = scanResults.emails.filter(email => {
        if (!email.deadline?.has_deadline || !email.deadline?.date) return false
        const date = new Date(email.deadline.date)
        return date >= now
      })

      // 4️⃣ Identify new reminders not already on the calendar
      const existingTitles = new Set(existingEvents.map(e => e.title.toLowerCase().replace(/📧\s*/g, '')))
      const newDeadlines = futureEmails.filter(email => {
        const normalizedTitle = email.subject.toLowerCase().trim()
        return !Array.from(existingTitles).some(title => 
          title.includes(normalizedTitle) || normalizedTitle.includes(title)
        )
      })

      console.log(`📬 Found ${newDeadlines.length} new deadlines not in Google Calendar.`)

      if (newDeadlines.length === 0) {
        toast.dismiss()
        toast.success('All reminders are already synced 🎉')
        setLoading(false)
        return
      }

      // 5️⃣ Create new events on Google Calendar
      await apiService.createCalendarReminders(user.id, newDeadlines, {
        default_reminders: [10080, 1440], // 1 week and 1 day before
        urgent_reminders: [10080, 1440, 60]
      })

      // 6️⃣ Add to local state
      const newEvents = newDeadlines.map(email => {
        const dateStr = email.deadline.date
        const timeStr = email.deadline.time || '23:59:00'
        const deadlineDate = new Date(`${dateStr}T${timeStr}`)
        return {
          id: email.email_id,
          title: `📧 ${email.subject}`,
          start: deadlineDate,
          end: deadlineDate,
          resource: {
            type: email.deadline.type || 'application',
            urgency: email.classification.urgency || 'medium',
            originalEmail: {
              subject: email.subject,
              sender: email.sender,
              snippet: email.snippet
            },
            daysUntil: email.deadline.urgency_days || 0
          }
        }
      })

      setEvents(prev => {
        const all = [...prev, ...newEvents]
        const unique = all.filter(
          (e, i, arr) =>
            i === arr.findIndex(x => x.title === e.title && x.start.getTime() === e.start.getTime())
        )
        return unique.filter(e => e.start >= now)
      })

      // Update last sync timestamp
      const nowTimestamp = Date.now()
      localStorage.setItem('lastSync', nowTimestamp.toString())

      toast.dismiss()
      toast.success(`Synced ${newDeadlines.length} new deadlines to calendar! 📅`)
      
      // 7️⃣ Refresh calendar events from Google Calendar to get actual event IDs
      console.log('🔄 Refreshing calendar events from Google Calendar...')
      const refreshedCalendar = await apiService.getUpcomingDeadlines(user.id)
      if (refreshedCalendar.success) {
        const refreshedEvents = refreshedCalendar.upcoming_events
          .map(event => ({
            id: event.event_id,
            title: event.title.trim(),
            start: new Date(event.start_time),
            end: new Date(event.start_time),
            resource: {
              type: event.deadline_type,
              urgency: event.urgency,
              originalEmail: event.original_email,
              daysUntil: event.days_until
            }
          }))
          .filter(e => e.start >= now)
        
        setEvents(refreshedEvents)
        console.log(`✅ Refreshed ${refreshedEvents.length} events from Google Calendar`)
      }
      
    } catch (err) {
      console.error('❌ Error syncing reminders:', err)
      toast.dismiss()
      toast.error('Failed to sync reminders')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteEvent = async (eventId, eventTitle) => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      `Are you sure you want to delete this reminder?\n\n"${eventTitle}"\n\nThis will remove it from your calendar and cannot be undone.`
    )
    
    if (!confirmed) return
    
    try {
      // Show loading toast
      const loadingToast = toast.loading('Deleting reminder...')
      
      // Delete from backend/Google Calendar
      await apiService.deleteReminder(user.id, eventId)
      
      // Remove from local state
      setEvents(prev => prev.filter(event => event.id !== eventId))
      
      toast.dismiss(loadingToast)
      toast.success('Reminder deleted successfully! 🗑️')
    } catch (error) {
      console.error('Error deleting reminder:', error)
      toast.error('Failed to delete reminder. Please try again.')
    }
  }

  const handleAddCustomReminder = async (reminderData) => {
    try {
      // In a real app, you'd send this to your backend
      const newEvent = {
        id: `custom_${Date.now()}`,
        title: reminderData.title,
        start: new Date(reminderData.date),
        end: new Date(reminderData.date),
        resource: {
          type: 'custom',
          urgency: reminderData.urgency || 'medium',
          description: reminderData.description
        }
      }
      
      setEvents(prev => [...prev, newEvent])
      toast.success('Custom reminder added successfully')
      setShowReminderModal(false)
    } catch (error) {
      console.error('Error adding custom reminder:', error)
      toast.error('Failed to add custom reminder')
    }
  }

  const eventStyleGetter = (event) => {
    const urgencyColors = {
      high: 'bg-red-500/80',
      medium: 'bg-yellow-500/80',
      low: 'bg-green-500/80',
      custom: 'bg-primary-500/80'
    }
    
    return {
      className: `${urgencyColors[event.resource?.urgency || 'medium']} text-white border-none rounded-lg`
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-500 flex items-center justify-center">
        <Navbar />
        <div className="flex flex-col items-center justify-center">
          {/* Animated Job Hunt Loader */}
          <div className="relative w-32 h-32 mb-6">
            {/* Briefcase */}
            <motion.div
              animate={{ 
                y: [0, -20, 0],
                rotate: [0, 5, -5, 0]
              }}
              transition={{ 
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="text-7xl">💼</div>
            </motion.div>
            
            {/* Flying Emails */}
            <motion.div
              animate={{ 
                x: [-40, 40],
                y: [-20, 20],
                opacity: [0, 1, 0]
              }}
              transition={{ 
                duration: 2.5,
                repeat: Infinity,
                ease: "linear"
              }}
              className="absolute top-0 left-0 text-3xl"
            >
              📧
            </motion.div>
            
            <motion.div
              animate={{ 
                x: [40, -40],
                y: [20, -20],
                opacity: [0, 1, 0]
              }}
              transition={{ 
                duration: 2.5,
                delay: 1.2,
                repeat: Infinity,
                ease: "linear"
              }}
              className="absolute bottom-0 right-0 text-3xl"
            >
              📨
            </motion.div>
          </div>
          
          {/* Loading Text */}
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-center"
          >
            <h2 className="text-2xl font-bold text-primary-500 mb-2">
              🔍 Hunting for opportunities...
            </h2>
            <p className="text-text-secondary">
              Syncing your emails and calendar
            </p>
          </motion.div>
          
          {/* Progress Dots */}
          <div className="flex space-x-2 mt-6">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                animate={{ 
                  scale: [1, 1.5, 1],
                  backgroundColor: ['#00FFFF', '#00FF88', '#00FFFF']
                }}
                transition={{ 
                  duration: 1,
                  delay: i * 0.3,
                  repeat: Infinity
                }}
                className="w-3 h-3 rounded-full bg-primary-500"
              />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      
      <main className="container mx-auto px-6 pt-24 pb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-text-primary mb-2">
              Welcome back, {user?.name?.split(' ')[0]}! 👋
            </h1>
            <p className="text-text-secondary">
              Stay on top of your job applications and never miss a deadline
            </p>
          </div>

          {/* Stats Cards */}
          <StatsCards events={events} />

          {/* Main Content Grid */}
          <div className="grid lg:grid-cols-3 gap-8 mb-8">
            
            {/* Left Column - Actions & Settings */}
            <div className="space-y-6">
              {/* Email Scanner */}
              <EmailScanner 
                onScanComplete={handleEmailScanComplete}
                userId={user?.id}
              />

              {/* Quick Actions */}
              <motion.div
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.2 }}
                className="glass-card p-6 rounded-xl"
              >
                <h3 className="text-lg font-semibold text-text-primary mb-4">
                  Quick Actions
                </h3>
                <div className="space-y-3">
                  <button
                    onClick={() => setShowReminderModal(true)}
                    className="w-full btn-secondary text-left"
                  >
                    ➕ Add Custom Reminder
                  </button>
                  <button
                    onClick={() => setCalendarView(calendarView === 'month' ? 'agenda' : 'month')}
                    className="w-full btn-secondary text-left"
                  >
                    📅 Switch to {calendarView === 'month' ? 'List' : 'Calendar'} View
                  </button>
                </div>
              </motion.div>
            </div>

            {/* Right Column - Upcoming Deadlines */}
            <div className="lg:col-span-2">
              <UpcomingDeadlines 
                events={events} 
                onDeleteEvent={handleDeleteEvent}
              />
            </div>
          </div>

          {/* Calendar Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="glass-card p-6 rounded-xl"
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-text-primary">
                Calendar Timeline
              </h2>
              <div className="flex items-center space-x-4">
                <select
                  value={calendarView}
                  onChange={(e) => setCalendarView(e.target.value)}
                  className="bg-dark-400 border border-primary-500/30 rounded-lg px-3 py-2 text-text-primary"
                >
                  <option value="month">Month View</option>
                  <option value="week">Week View</option>
                  <option value="agenda">Agenda View</option>
                </select>
              </div>
            </div>

            <div className="calendar-container" style={{ height: '600px' }}>
              <Calendar
                localizer={localizer}
                events={events}
                startAccessor="start"
                endAccessor="end"
                view={calendarView}
                onView={setCalendarView}
                date={selectedDate}
                onNavigate={setSelectedDate}
                eventPropGetter={eventStyleGetter}
                className="dark-calendar"
                components={{
                  toolbar: (props) => (
                    <div className="flex justify-between items-center mb-4 p-4 bg-dark-400/50 rounded-lg">
                      <button
                        onClick={() => props.onNavigate('PREV')}
                        className="btn-secondary px-4 py-2"
                      >
                        ‹ Previous
                      </button>
                      <h3 className="text-lg font-semibold text-text-primary">
                        {moment(props.date).format('MMMM YYYY')}
                      </h3>
                      <button
                        onClick={() => props.onNavigate('NEXT')}
                        className="btn-secondary px-4 py-2"
                      >
                        Next ›
                      </button>
                    </div>
                  )
                }}
              />
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Custom Reminder Modal */}
      {showReminderModal && (
        <CustomReminderModal
          onClose={() => setShowReminderModal(false)}
          onSave={handleAddCustomReminder}
        />
      )}
    </div>
  )
}

export default HomePage