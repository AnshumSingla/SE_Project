import { useState } from 'react'
import { motion } from 'framer-motion'
import { EyeOff } from 'lucide-react'

// Mails the profile filter held back. Nothing is hidden for good: each one shows why,
// with a one-click "Add anyway" for when the filter got it wrong.
const FilteredOut = ({ items, onAddAnyway, onDismiss }) => {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(null)
  if (!items || items.length === 0) return null

  const add = async (item) => {
    const key = `${item.email_id}:${item.event_index}`
    setBusy(key)
    try {
      await onAddAnyway(item)
    } finally {
      setBusy(null)
    }
  }

  return (
    <motion.div id="filtered-out-card" className="glass-card p-6 rounded-xl">
      <button onClick={() => setOpen((o) => !o)} className="w-full flex items-center justify-between text-left">
        <span className="flex items-center space-x-2 text-text-primary font-semibold">
          <EyeOff className="w-4 h-4" />
          <span>Filtered out ({items.length})</span>
        </span>
        <span className="text-xs text-text-secondary">{open ? 'Hide' : 'Show'}</span>
      </button>
      {open && (
        <ul className="mt-4 space-y-3">
          {items.map((item) => {
            const key = `${item.email_id}:${item.event_index}`
            return (
              <li key={key} className="border border-white/10 rounded-lg p-3">
                <p className="text-sm text-text-primary">{item.deadline?.title || item.subject}</p>
                <p className="text-xs text-text-secondary">
                  {item.deadline?.date}
                  {item.deadline?.time ? ` · ${item.deadline.time}` : ''} · {item.subject}
                </p>
                <p className="text-xs text-yellow-400 mt-1">Why: {item.relevance?.reason}</p>
                <button
                  onClick={() => add(item)}
                  disabled={busy === key}
                  className="mt-2 text-xs text-primary-400 hover:underline disabled:opacity-50"
                >
                  {busy === key ? 'Adding...' : 'Add anyway'}
                </button>
                {onDismiss && (
                  <button onClick={() => onDismiss(item)} className="mt-2 ml-4 text-xs text-text-secondary hover:underline">
                    Dismiss
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </motion.div>
  )
}

export default FilteredOut
