import { motion } from 'framer-motion'
import { Calendar, Clock, Mail, AlertTriangle, CheckCircle, Star } from 'lucide-react'
import moment from 'moment'

const UpcomingDeadlines = ({ events }) => {
  const now = new Date()
  const upcomingEvents = events
    .filter(event => new Date(event.start) > now)
    .sort((a, b) => new Date(a.start) - new Date(b.start))
    .slice(0, 6) // Show top 6 upcoming events

  const getUrgencyColor = (urgency) => {
    const colors = {
      high: 'text-red-400 bg-red-500/10 border-red-500/30',
      medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
      low: 'text-green-400 bg-green-500/10 border-green-500/30',
      custom: 'text-primary-400 bg-primary-500/10 border-primary-500/30'
    }
    return colors[urgency] || colors.medium
  }

  const getUrgencyIcon = (urgency) => {
    const icons = {
      high: <AlertTriangle className="w-4 h-4" />,
      medium: <Clock className="w-4 h-4" />,
      low: <CheckCircle className="w-4 h-4" />,
      custom: <Star className="w-4 h-4" />
    }
    return icons[urgency] || icons.medium
  }

  const getTimeUntil = (date) => {
    const eventDate = moment(date)
    const now = moment()
    const duration = moment.duration(eventDate.diff(now))
    
    if (duration.asDays() >= 1) {
      const days = Math.floor(duration.asDays())
      return `${days} day${days !== 1 ? 's' : ''}`
    } else if (duration.asHours() >= 1) {
      const hours = Math.floor(duration.asHours())
      return `${hours} hour${hours !== 1 ? 's' : ''}`
    } else {
      const minutes = Math.floor(duration.asMinutes())
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`
    }
  }

  if (upcomingEvents.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-8 rounded-xl text-center"
      >
        <Calendar className="w-16 h-16 text-text-muted mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          No Upcoming Deadlines
        </h3>
        <p className="text-text-secondary">
          Great! You're all caught up. Use the email scanner to find new opportunities.
        </p>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.1 }}
      className="glass-card p-6 rounded-xl"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-text-primary">Upcoming Deadlines</h2>
        <span className="text-sm text-text-secondary">
          {upcomingEvents.length} upcoming
        </span>
      </div>

      <div className="space-y-4">
        {upcomingEvents.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            whileHover={{ scale: 1.02, x: 5 }}
            className="bg-dark-300/30 border border-primary-500/20 rounded-lg p-4 hover:border-primary-500/40 transition-all duration-300"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs border ${getUrgencyColor(event.resource?.urgency)}`}>
                    {getUrgencyIcon(event.resource?.urgency)}
                    <span className="capitalize">{event.resource?.urgency || 'medium'}</span>
                  </div>
                  
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    event.resource?.type === 'application' ? 'bg-blue-500/20 text-blue-400' :
                    event.resource?.type === 'interview' ? 'bg-purple-500/20 text-purple-400' :
                    event.resource?.type === 'assessment' ? 'bg-orange-500/20 text-orange-400' :
                    'bg-primary-500/20 text-primary-400'
                  }`}>
                    {event.resource?.type || 'reminder'}
                  </span>
                </div>
                
                <h3 className="font-semibold text-text-primary mb-1 line-clamp-2">
                  {event.title}
                </h3>
                
                {event.resource?.originalEmail && (
                  <div className="flex items-center space-x-1 text-xs text-text-secondary mb-2">
                    <Mail className="w-3 h-3" />
                    <span>{event.resource.originalEmail.sender}</span>
                  </div>
                )}
                
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-1 text-text-secondary">
                    <Calendar className="w-4 h-4" />
                    <span>{moment(event.start).format('MMM DD, YYYY')}</span>
                  </div>
                  <div className="flex items-center space-x-1 text-text-secondary">
                    <Clock className="w-4 h-4" />
                    <span>{moment(event.start).format('h:mm A')}</span>
                  </div>
                </div>
              </div>
              
              <div className="text-right ml-4">
                <div className="text-sm font-medium text-primary-400">
                  in {getTimeUntil(event.start)}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      
      {events.filter(e => new Date(e.start) > now).length > 6 && (
        <div className="text-center mt-4">
          <span className="text-sm text-text-secondary">
            +{events.filter(e => new Date(e.start) > now).length - 6} more deadlines in calendar
          </span>
        </div>
      )}
    </motion.div>
  )
}

export default UpcomingDeadlines