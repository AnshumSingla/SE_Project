import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Zap, Clock, ChevronDown, ChevronUp, RefreshCw, Target } from 'lucide-react'
import { apiService } from '../services/apiService'
import { useAuth } from '../context/AuthContext'

import { Skeleton } from '@/components/ui/skeleton'

const URGENCY_COLORS = {
  high: 'text-red-400 bg-red-500/10 border-red-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  low: 'text-green-400 bg-green-500/10 border-green-500/30',
}

const TaskPriorityPanel = ({ events = [], onAskAI }) => {
  const { user } = useAuth()
  const [priorities, setPriorities] = useState([])
  const [focusToday, setFocusToday] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(true)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  const fetchPriorities = async () => {
    if (!user || events.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const result = await apiService.getPriorityPlan(user.id, events)
      if (result.success) {
        setPriorities(result.priorities || [])
        setFocusToday(result.focus_today || null)
        setSummary(result.summary || null)
        setLoaded(true)
      } else {
        setError('Could not load AI priorities')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Auto-fetch once events are available
  useEffect(() => {
    if (!loaded && events.length > 0 && user) {
      fetchPriorities()
    }
  }, [events.length, user])

  const rankColors = ['from-red-500 to-orange-500', 'from-orange-500 to-yellow-500', 'from-yellow-500 to-green-500']

  return (
    <motion.div
      id="ai-priority-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="glass-card rounded-xl overflow-hidden border border-primary-500/20"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
            <Brain className="w-4 h-4 text-primary-500" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">AI Priority Planner</h3>
            <p className="text-xs text-text-muted">Powered by Gemini</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            id="refresh-priorities-btn"
            onClick={e => { e.stopPropagation(); fetchPriorities() }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="text-text-muted hover:text-primary-500 transition-colors"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </motion.button>
          {expanded ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 space-y-3">
              {/* Loading State */}
              {loading && (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="flex gap-2.5 p-3 bg-dark-400/20 rounded-lg">
                      <Skeleton className="h-6 w-6 rounded-full flex-shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-5/6" />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Error State */}
              {!loading && error && (
                <div className="text-center py-4">
                  <p className="text-red-400 text-sm mb-2">{error}</p>
                  <button onClick={fetchPriorities} className="text-xs text-primary-500 hover:underline">Try again</button>
                </div>
              )}

              {/* Empty / Not loaded State */}
              {!loading && !error && !loaded && events.length === 0 && (
                <p className="text-text-muted text-sm text-center py-3">
                  No deadlines to prioritise yet. Scan your emails to get started.
                </p>
              )}

              {/* Focus Today Banner */}
              {!loading && focusToday && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-start gap-2 bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-500/30 rounded-lg px-3 py-2"
                >
                  <Target className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-primary-400 uppercase tracking-wide mb-0.5">Focus Today</p>
                    <p className="text-sm text-text-primary font-medium">{focusToday}</p>
                  </div>
                </motion.div>
              )}

              {/* Priority List */}
              {!loading && priorities.length > 0 && (
                <div className="space-y-2">
                  {priorities.slice(0, 4).map((item, idx) => (
                    <motion.div
                      key={item.event_id || idx}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.07 }}
                      className="flex gap-2.5 p-3 bg-dark-400/30 rounded-lg group hover:bg-dark-400/50 transition-colors"
                    >
                      {/* Rank badge */}
                      <div className={`flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br ${rankColors[Math.min(idx, 2)]} flex items-center justify-center text-xs font-bold text-white`}>
                        {item.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-text-primary font-medium truncate">{item.title}</p>
                        <p className="text-xs text-text-muted leading-relaxed mt-0.5 line-clamp-2">{item.reason}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          {item.time_estimate && (
                            <span className="flex items-center gap-1 text-xs text-text-muted">
                              <Clock className="w-3 h-3" />{item.time_estimate}
                            </span>
                          )}
                          {item.suggested_action && (
                            <span className="text-xs text-primary-400 truncate flex items-center gap-1">
                              <Zap className="w-3 h-3 flex-shrink-0" />{item.suggested_action}
                            </span>
                          )}
                        </div>
                      </div>
                      {onAskAI && (
                        <button
                          onClick={() => onAskAI(`Tell me more about: ${item.title}`)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-primary-500 hover:text-primary-400 flex-shrink-0 self-start mt-0.5"
                        >
                          Ask AI
                        </button>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Summary */}
              {!loading && summary && (
                <p className="text-xs text-text-muted leading-relaxed pt-1 border-t border-dark-300/30">
                  {summary}
                </p>
              )}

              {/* Plan My Week CTA */}
              {!loading && loaded && onAskAI && (
                <motion.button
                  id="plan-week-btn"
                  onClick={() => onAskAI('Help me plan my week based on my deadlines')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full py-2 text-sm font-medium bg-gradient-to-r from-primary-500/10 to-accent-500/10 hover:from-primary-500/20 hover:to-accent-500/20 border border-primary-500/20 text-primary-400 rounded-lg transition-all"
                >
                  ✨ Plan my week with AI
                </motion.button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default TaskPriorityPanel
