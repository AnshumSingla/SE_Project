import { motion } from 'framer-motion'
import { Calendar, Clock, AlertTriangle, CheckCircle } from 'lucide-react'

const StatsCards = ({ events }) => {
  const now = new Date()
  
  // Filter to only include future events (safety net)
  const futureEvents = events.filter(e => new Date(e.start) > now)
  
  const stats = {
    total: futureEvents.length, // Only count future deadlines
    upcoming: futureEvents.length, // Same as total for clarity
    urgent: futureEvents.filter(e => {
      const daysUntil = Math.ceil((new Date(e.start) - now) / (1000 * 60 * 60 * 24))
      return daysUntil <= 3 && daysUntil > 0
    }).length,
    thisWeek: futureEvents.filter(e => {
      const eventDate = new Date(e.start)
      const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
      return eventDate > now && eventDate <= weekFromNow
    }).length
  }

  const cardData = [
    {
      title: 'Total Deadlines',
      value: stats.total,
      icon: <Calendar className="w-6 h-6" />,
      color: 'primary',
      description: 'All tracked deadlines'
    },
    {
      title: 'Upcoming',
      value: stats.upcoming,
      icon: <Clock className="w-6 h-6" />,
      color: 'accent',
      description: 'Future deadlines'
    },
    {
      title: 'Urgent',
      value: stats.urgent,
      icon: <AlertTriangle className="w-6 h-6" />,
      color: 'red',
      description: 'Due within 3 days'
    },
    {
      title: 'This Week',
      value: stats.thisWeek,
      icon: <CheckCircle className="w-6 h-6" />,
      color: 'green',
      description: 'Due in next 7 days'
    }
  ]

  const getColorClasses = (color) => {
    const colors = {
      primary: 'text-primary-500 bg-primary-500/10',
      accent: 'text-accent-500 bg-accent-500/10',
      red: 'text-red-500 bg-red-500/10',
      green: 'text-green-500 bg-green-500/10'
    }
    return colors[color] || colors.primary
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cardData.map((card, index) => (
        <motion.div
          key={card.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: index * 0.1 }}
          whileHover={{ scale: 1.05, y: -5, transition: { duration: 0.2 } }}
          className="glass-card p-4 rounded-xl neon-glow hover:shadow-xl transition-all duration-300"
        >
          <div className="flex items-center justify-between mb-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getColorClasses(card.color)}`}>
              {card.icon}
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-text-primary">{card.value}</div>
            </div>
          </div>
          <div>
            <h3 className="font-semibold text-text-primary text-sm">{card.title}</h3>
            <p className="text-xs text-text-secondary mt-1">{card.description}</p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

export default StatsCards