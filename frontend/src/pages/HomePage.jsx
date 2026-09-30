import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Calendar, momentLocalizer } from 'react-big-calendar'
import moment from 'moment'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import EmailScanner from '../components/EmailScanner'
import CustomReminderModal from '../components/CustomReminderModal'
import StatsCards from '../components/StatsCards'
import UpcomingDeadlines from '../components/UpcomingDeadlines'
import AIAssistant from '../components/AIAssistant'
import TaskPriorityPanel from '../components/TaskPriorityPanel'
import ProfileCard from '../components/ProfileCard'
import FilteredOut from '../components/FilteredOut'
import ReviewQueue from '../components/ReviewQueue'
import ActivityLog from '../components/ActivityLog'
import { apiService } from '../services/apiService'
import toast from 'react-hot-toast'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
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
  const [review, setReview] = useState({ review: [], filtered_out: [], log: [], last_scan: null })
  const [aiMessage, setAiMessage] = useState(null) // pre-fills AI chat from other components
  const syncing = useRef(false) // guards against overlapping syncs (double click, StrictMode double effect)

  useEffect(() => {
    if (user) runSync()
  }, [user])

  const startOnboardingTour = () => {
    const driverObj = driver({
      showProgress: true,
      animate: true,
      overlayColor: 'rgba(0, 0, 0, 0.75)',
      steps: [
        {
          element: '#welcome-header',
          popover: {
            title: 'Welcome to Smart Reminder! 🚀',
            description: 'Let\'s take a quick 1-minute tour of your new AI-powered productivity workspace.',
            side: 'bottom',
            align: 'start'
          }
        },
        {
          element: '#email-scanner-card',
          popover: {
            title: 'AI Email Scanner 📧',
            description: 'Scan your Gmail inbox. Our intelligent pipeline automatically parses, filters, and creates calendar deadlines for jobs, assignments, bills, and interviews.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#ai-priority-panel',
          popover: {
            title: 'Gemini Priority Planner 🎯',
            description: 'Gemini automatically ranks all your upcoming tasks by urgency and importance, showing you exactly what to focus on today.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#quick-actions-card',
          popover: {
            title: 'Quick Actions ➕',
            description: 'Manually add custom deadlines directly to your Google Calendar and toggle calendar views.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#upcoming-deadlines',
          popover: {
            title: 'Upcoming Deadlines ⏱️',
            description: 'View chronological deadlines with automated urgency indicators. You can delete or ask the AI helper directly about any task.',
            side: 'left',
            align: 'start'
          }
        },
        {
          element: '#calendar-timeline-card',
          popover: {
            title: 'Calendar Timeline 📅',
            description: 'An interactive monthly planner plotting all scheduled deadlines. Keep track of visual color blocks corresponding to task priority.',
            side: 'top',
            align: 'center'
          }
        },
        {
          element: '#ai-assistant-toggle',
          popover: {
            title: 'Floating AI Companion 💬',
            description: 'Our conversational Gemini agent is always in reach! Chat with it to brainstorm, plan your week, or check calendar entries.',
            side: 'left',
            align: 'center'
          }
        }
      ]
    })
    driverObj.drive()
  }

  useEffect(() => {
    if (!loading && user) {
      const hasOnboarded = localStorage.getItem('smartReminder_onboarded')
      if (!hasOnboarded) {
        const timer = setTimeout(() => {
          startOnboardingTour()
          localStorage.setItem('smartReminder_onboarded', 'true')
        }, 1000)
        return () => clearTimeout(timer)
      }
    }
  }, [loading, user])

  // Google Calendar is the single source of truth for what is on the list.
  const toCalendarEvents = (response, now) =>
    response.success
      ? response.upcoming_events
          .map(event => ({
            id: event.event_id,
            title: event.title.trim(),
            start: new Date(event.start_time),
            end: new Date(event.start_time),
            description: event.description,
            extendedProperties: event.extendedProperties,
            resource: {
              type: event.deadline_type,
              urgency: event.urgency,
              originalEmail: event.original_email,
              daysUntil: event.days_until
            }
          }))
          .filter(e => e.start >= now)
      : []

  const loadReview = async () => {
    try {
      const data = await apiService.getReview()
      if (data.success) setReview(data)
    } catch (err) {
      console.error('Could not load review queue:', err.message) // not fatal: calendar still shows
    }
  }

  const refreshEvents = async () =>
    setEvents(toCalendarEvents(await apiService.getUpcomingDeadlines(user.id), new Date()))

  // Opening the page only READS: the scheduled background scan already added new mail.
  // "Scan now" asks the server to run that same scan immediately.
  const runSync = async ({ force = false } = {}) => {
    if (syncing.current) return
    syncing.current = true
    setLoading(true)
    try {
      await refreshEvents()
      if (force) {
        toast.loading('Scanning emails...')
        const result = await apiService.runScan()
        toast.dismiss()
        if (result.status === 'paused') toast('Scanning is paused in your profile')
        else if (result.added) toast.success(`Added ${result.added} new event${result.added > 1 ? 's' : ''} to your calendar`)
        else toast.success('No new events found')
        if (result.for_review) toast(`${result.for_review} item${result.for_review > 1 ? 's' : ''} need your review`)
        await refreshEvents()
      }
      await loadReview()
    } catch (err) {
      console.error('❌ Error syncing reminders:', err)
      toast.dismiss()
      toast.error(err.message || 'Failed to sync reminders')
    } finally {
      syncing.current = false
      setLoading(false)
    }
  }

  // Accept = create the event now; dismiss = never show it again.
  const resolveItem = async (item, action) => {
    try {
      const res = await apiService.resolveReview(item.event_id, action)
      if (action === 'accept') toast.success(res.status === 'created' ? 'Added to your calendar' : 'Already on (or removed from) your calendar')
      await Promise.all([loadReview(), action === 'accept' ? refreshEvents() : Promise.resolve()])
    } catch (err) {
      toast.error(err.message || 'Could not update this item')
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
          <div id="welcome-header" className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-text-primary mb-2">
                Welcome back, {user?.name?.split(' ')[0]}! 👋
              </h1>
              <p className="text-text-secondary">
                Stay ahead of your schedule, tasks, and deadlines.
              </p>
            </div>
            <button
              onClick={startOnboardingTour}
              className="self-start sm:self-center bg-gradient-to-r from-primary-500/10 to-accent-500/10 hover:from-primary-500/20 hover:to-accent-500/20 border border-primary-500/30 text-primary-400 font-medium px-4 py-2 rounded-full text-xs flex items-center gap-1.5 transition-all duration-200"
            >
              🗺️ Take a Tour
            </button>
          </div>

          {/* Stats Cards */}
          <StatsCards events={events} />

          {/* Main Content Grid */}
          <div className="grid lg:grid-cols-3 gap-8 mb-8">
            
            {/* Left Column - Actions & Settings */}
            <div className="space-y-6">
              {/* Email Scanner */}
              <EmailScanner 
                onScan={() => runSync({ force: true })}
                userId={user?.id}
              />
              
              <ProfileCard />

              <ReviewQueue items={review.review} onResolve={resolveItem} />

              <FilteredOut items={review.filtered_out} onAddAnyway={(item) => resolveItem(item, 'accept')} onDismiss={(item) => resolveItem(item, 'dismiss')} />

              <ActivityLog log={review.log} lastScan={review.last_scan} />

              {/* Task Priority Panel */}
              <TaskPriorityPanel
                events={events}
                onAskAI={(msg) => setAiMessage(msg)}
              />

              {/* Quick Actions */}
              <motion.div
                id="quick-actions-card"
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.1 }}
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
            id="calendar-timeline-card"
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

      {/* Gemini AI Assistant */}
      <AIAssistant
        events={events}
        externalMessage={aiMessage}
        onExternalMessageConsumed={() => setAiMessage(null)}
      />
    </div>
  )
}

export default HomePage