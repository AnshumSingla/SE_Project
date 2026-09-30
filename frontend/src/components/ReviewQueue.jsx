import { useState } from 'react'
import { motion } from 'framer-motion'
import { ClipboardCheck } from 'lucide-react'

const describe = (item) => {
  const d = item.deadline || {}
  const when = [d.date, d.time && `${d.time}${d.end_time ? '–' + d.end_time : ''}`].filter(Boolean).join(' · ')
  const why = (d.flags || []).filter((f) => f !== 'weekday_ok').map((f) => f.replace(/_/g, ' ')).join(', ')
  return { when, why, unsure: d.confidence != null && d.confidence < 0.75 }
}

// Events the scan found but wasn't sure enough about to add by itself.
const ReviewQueue = ({ items, onResolve }) => {
  const [busy, setBusy] = useState(null)
  if (!items || items.length === 0) return null

  const act = async (item, action) => {
    setBusy(item.event_id)
    try {
      await onResolve(item, action)
    } finally {
      setBusy(null)
    }
  }

  return (
    <motion.div id="review-queue-card" className="glass-card p-6 rounded-xl border border-yellow-500/30">
      <div className="flex items-center space-x-2 mb-3 text-text-primary font-semibold">
        <ClipboardCheck className="w-4 h-4 text-yellow-400" />
        <span>Needs your review ({items.length})</span>
      </div>
      <ul className="space-y-3">
        {items.map((item) => {
          const { when, why, unsure } = describe(item)
          return (
            <li key={item.event_id} className="border border-white/10 rounded-lg p-3">
              <p className="text-sm text-text-primary">{item.deadline?.title || item.subject}</p>
              <p className="text-xs text-text-secondary">{when} · {item.subject}</p>
              {(unsure || why) && (
                <p className="text-xs text-yellow-400 mt-1">Check the date{why ? `: ${why}` : ''}</p>
              )}
              {item.deadline?.text && (
                <p className="text-xs text-text-secondary mt-1 italic">“{item.deadline.text.slice(0, 140)}”</p>
              )}
              <div className="mt-2 flex gap-4 text-xs">
                <button disabled={busy === item.event_id} onClick={() => act(item, 'accept')} className="text-primary-400 hover:underline disabled:opacity-50">
                  Add to calendar
                </button>
                <button disabled={busy === item.event_id} onClick={() => act(item, 'dismiss')} className="text-text-secondary hover:underline disabled:opacity-50">
                  Dismiss
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </motion.div>
  )
}

export default ReviewQueue
