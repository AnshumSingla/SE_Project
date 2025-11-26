import { motion } from 'framer-motion'
import { Bell, Settings, Clock } from 'lucide-react'

const ReminderSettings = ({ frequency, onChange }) => {
  const frequencyOptions = [
    { value: 1, label: 'Once', description: '1 day before', times: ['1 day'] },
    { value: 2, label: 'Twice', description: '1 week & 1 day before', times: ['1 week', '1 day'] },
    { value: 3, label: 'Thrice', description: '1 week, 1 day & 1 hour before', times: ['1 week', '1 day', '1 hour'] }
  ]

  const currentOption = frequencyOptions.find(opt => opt.value === frequency)

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="glass-card p-6 rounded-xl"
    >
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center">
          <Bell className="w-5 h-5 text-primary-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text-primary">Reminder Settings</h3>
          <p className="text-sm text-text-secondary">Customize notification frequency</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Frequency Selector */}
        <div className="space-y-3">
          {frequencyOptions.map((option) => (
            <motion.button
              key={option.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onChange(option.value)}
              className={`w-full p-4 rounded-lg border-2 transition-all duration-300 ${
                frequency === option.value
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-primary-500/20 bg-dark-300/20 hover:border-primary-500/40'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-left">
                  <div className="font-medium text-text-primary">{option.label}</div>
                  <div className="text-sm text-text-secondary">{option.description}</div>
                </div>
                <div className={`w-4 h-4 rounded-full border-2 ${
                  frequency === option.value
                    ? 'border-primary-500 bg-primary-500'
                    : 'border-primary-500/30'
                }`}>
                  {frequency === option.value && (
                    <div className="w-2 h-2 bg-white rounded-full m-0.5" />
                  )}
                </div>
              </div>
            </motion.button>
          ))}
        </div>

        {/* Current Setting Display */}
        <div className="bg-dark-300/30 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Clock className="w-4 h-4 text-primary-500" />
            <span className="text-sm font-medium text-text-primary">Current Setting</span>
          </div>
          <div className="text-xs text-text-secondary">
            You'll receive {frequency} reminder{frequency > 1 ? 's' : ''} for each deadline:
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {currentOption?.times.map((time, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-primary-500/20 text-primary-400 text-xs rounded-full"
              >
                {time}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default ReminderSettings