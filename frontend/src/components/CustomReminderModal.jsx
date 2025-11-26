import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Calendar, Clock, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

const CustomReminderModal = ({ onClose, onSave }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    time: '',
    urgency: 'medium'
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (!formData.title || !formData.date) {
      toast.error('Please fill in all required fields')
      return
    }

    const reminderDateTime = new Date(`${formData.date}T${formData.time || '09:00'}`)
    
    if (reminderDateTime <= new Date()) {
      toast.error('Please select a future date and time')
      return
    }

    onSave({
      ...formData,
      date: reminderDateTime.toISOString()
    })
  }

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        />
        
        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full max-w-md glass-card p-6 rounded-xl neon-glow"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center">
                <Calendar className="w-4 h-4 text-primary-500" />
              </div>
              <h2 className="text-xl font-bold text-text-primary">Add Custom Reminder</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-text-secondary hover:text-primary-500 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Title *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="e.g., Follow up with HR at Company X"
                className="w-full bg-dark-300/50 border border-primary-500/30 rounded-lg px-4 py-3 text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500/70 transition-colors"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Additional notes or context..."
                rows={3}
                className="w-full bg-dark-300/50 border border-primary-500/30 rounded-lg px-4 py-3 text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500/70 transition-colors resize-none"
              />
            </div>

            {/* Date and Time */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Date *
                </label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => handleChange('date', e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full bg-dark-300/50 border border-primary-500/30 rounded-lg px-4 py-3 text-text-primary focus:outline-none focus:border-primary-500/70 transition-colors"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Time
                </label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => handleChange('time', e.target.value)}
                  className="w-full bg-dark-300/50 border border-primary-500/30 rounded-lg px-4 py-3 text-text-primary focus:outline-none focus:border-primary-500/70 transition-colors"
                />
              </div>
            </div>

            {/* Urgency */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Priority Level
              </label>
              <select
                value={formData.urgency}
                onChange={(e) => handleChange('urgency', e.target.value)}
                className="w-full bg-dark-300/50 border border-primary-500/30 rounded-lg px-4 py-3 text-text-primary focus:outline-none focus:border-primary-500/70 transition-colors"
              >
                <option value="low">Low Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="high">High Priority</option>
              </select>
            </div>

            {/* Actions */}
            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 btn-primary"
              >
                Save Reminder
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default CustomReminderModal