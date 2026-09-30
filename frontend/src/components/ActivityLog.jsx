import { motion } from 'framer-motion'
import { Activity } from 'lucide-react'

const ago = (iso) => {
  if (!iso) return 'never'
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
  if (mins < 2) return 'just now'
  if (mins < 120) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`
}

// What the background scan has been doing, so automatic actions are never invisible.
const ActivityLog = ({ log, lastScan }) => (
  <motion.div id="activity-log-card" className="glass-card p-6 rounded-xl">
    <div className="flex items-center justify-between mb-3">
      <span className="flex items-center space-x-2 text-text-primary font-semibold">
        <Activity className="w-4 h-4" />
        <span>Automatic scanning</span>
      </span>
      <span className="text-xs text-text-secondary">Last scan: {ago(lastScan)}</span>
    </div>
    {!log || log.length === 0 ? (
      <p className="text-xs text-text-secondary">No scans yet. They run in the background, so you don't need to open this page.</p>
    ) : (
      <ul className="space-y-2">
        {log.slice(0, 5).map((entry) => (
          <li key={entry.at} className="text-xs text-text-secondary">
            <span className="text-text-primary">{ago(entry.at)}</span>: {entry.mails_analysed} mail{entry.mails_analysed === 1 ? '' : 's'} checked,{' '}
            {entry.added} added{entry.for_review ? `, ${entry.for_review} to review` : ''}
            {entry.filtered_out ? `, ${entry.filtered_out} filtered out` : ''}
            {entry.errors ? `, ${entry.errors} error${entry.errors > 1 ? 's' : ''}` : ''}
            {entry.titles?.length ? ` (${entry.titles.join('; ')})` : ''}
          </li>
        ))}
      </ul>
    )}
  </motion.div>
)

export default ActivityLog
