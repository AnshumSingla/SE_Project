import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Trash2, CheckCircle2, Circle, Flame, Trophy, Target, ChevronRight } from 'lucide-react'
import Navbar from '../components/Navbar'
import toast from 'react-hot-toast'

const STORAGE_KEY = 'smartReminder_habits'
const COMPLETION_KEY = 'smartReminder_completions'

const DEFAULT_HABITS = [
  { id: 'h1', label: 'Applied to 1 opportunity', emoji: '📋' },
  { id: 'h2', label: 'Reviewed pending deadlines', emoji: '📅' },
  { id: 'h3', label: 'Studied / worked on a skill', emoji: '📚' },
  { id: 'h4', label: 'Took a break & stayed healthy', emoji: '🏃' },
]

function getTodayKey() {
  return new Date().toISOString().slice(0, 10)
}

function getWeekDays() {
  const days = []
  const today = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    days.push(d.toISOString().slice(0, 10))
  }
  return days
}

const GoalsPage = () => {
  const [habits, setHabits] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || DEFAULT_HABITS } catch { return DEFAULT_HABITS }
  })
  const [completions, setCompletions] = useState(() => {
    try { return JSON.parse(localStorage.getItem(COMPLETION_KEY)) || {} } catch { return {} }
  })
  const [newHabit, setNewHabit] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [celebrate, setCelebrate] = useState(false)

  const today = getTodayKey()
  const weekDays = getWeekDays()

  // Persist to localStorage
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(habits)) }, [habits])
  useEffect(() => { localStorage.setItem(COMPLETION_KEY, JSON.stringify(completions)) }, [completions])

  const todayCompletions = completions[today] || []
  const completedToday = habits.filter(h => todayCompletions.includes(h.id)).length
  const allDoneToday = completedToday === habits.length && habits.length > 0

  // Streak: count consecutive days with all habits done
  const streak = (() => {
    let count = 0
    const sortedDays = [...weekDays].reverse()
    for (const day of sortedDays) {
      const done = completions[day] || []
      if (done.length >= habits.length && habits.length > 0) count++
      else break
    }
    return count
  })()

  const toggleHabit = (habitId) => {
    const current = completions[today] || []
    const isChecked = current.includes(habitId)
    const updated = isChecked ? current.filter(id => id !== habitId) : [...current, habitId]
    const newCompletions = { ...completions, [today]: updated }
    setCompletions(newCompletions)

    // Celebrate if all done
    if (!isChecked && updated.length === habits.length) {
      setCelebrate(true)
      toast.success('🎉 All habits done today! Amazing work!', { duration: 4000 })
      setTimeout(() => setCelebrate(false), 3000)
    }
  }

  const addHabit = () => {
    if (!newHabit.trim()) return
    const h = { id: `h_${Date.now()}`, label: newHabit.trim(), emoji: '✅' }
    setHabits(prev => [...prev, h])
    setNewHabit('')
    setShowAdd(false)
    toast.success('Habit added!')
  }

  const deleteHabit = (id) => {
    setHabits(prev => prev.filter(h => h.id !== id))
    // Clean completions
    const updated = {}
    for (const [day, ids] of Object.entries(completions)) {
      updated[day] = ids.filter(i => i !== id)
    }
    setCompletions(updated)
  }

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />
      <main className="container mx-auto px-6 pt-24 pb-12 max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>

          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-text-primary mb-1 flex items-center gap-3">
              <Target className="w-8 h-8 text-primary-500" />
              Goals & Habits
            </h1>
            <p className="text-text-secondary">Build consistency, one day at a time.</p>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { icon: <Flame className="w-5 h-5 text-orange-400" />, label: 'Day Streak', value: streak, color: 'text-orange-400' },
              { icon: <CheckCircle2 className="w-5 h-5 text-primary-500" />, label: 'Done Today', value: `${completedToday}/${habits.length}`, color: 'text-primary-500' },
              { icon: <Trophy className="w-5 h-5 text-yellow-400" />, label: 'Best Streak', value: streak, color: 'text-yellow-400' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="glass-card rounded-xl p-4 text-center"
              >
                <div className="flex justify-center mb-2">{stat.icon}</div>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                <p className="text-xs text-text-muted mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Weekly Progress */}
          <div className="glass-card rounded-xl p-5 mb-6">
            <h3 className="text-sm font-semibold text-text-primary mb-3">This Week</h3>
            <div className="flex gap-2 justify-between">
              {weekDays.map(day => {
                const done = (completions[day] || []).length
                const total = habits.length
                const pct = total > 0 ? done / total : 0
                const isToday = day === today
                const label = new Date(day + 'T12:00:00').toLocaleDateString('en', { weekday: 'short' })
                return (
                  <div key={day} className="flex flex-col items-center gap-1.5 flex-1">
                    <div className="w-full bg-dark-400/60 rounded-full h-20 flex flex-col-reverse overflow-hidden">
                      <motion.div
                        className={`w-full rounded-full ${pct === 1 ? 'bg-gradient-to-t from-primary-500 to-accent-500' : 'bg-primary-500/50'}`}
                        initial={{ height: 0 }}
                        animate={{ height: `${pct * 100}%` }}
                        transition={{ duration: 0.8, delay: 0.2 }}
                      />
                    </div>
                    <span className={`text-xs ${isToday ? 'text-primary-400 font-semibold' : 'text-text-muted'}`}>{label}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Today's Habits */}
          <div className="glass-card rounded-xl p-5 mb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-text-primary">Today's Habits</h3>
              <span className="text-xs text-text-muted">{new Date().toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric' })}</span>
            </div>

            <AnimatePresence>
              {allDoneToday && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-4 p-3 bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-500/30 rounded-lg text-center"
                >
                  <p className="text-primary-400 font-medium text-sm">🎉 All done for today! Incredible.</p>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-2">
              {habits.map((habit, i) => {
                const done = todayCompletions.includes(habit.id)
                return (
                  <motion.div
                    key={habit.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer group transition-all duration-200 ${
                      done ? 'bg-primary-500/10' : 'bg-dark-400/30 hover:bg-dark-400/50'
                    }`}
                    onClick={() => toggleHabit(habit.id)}
                  >
                    <span className="text-xl select-none">{habit.emoji}</span>
                    <span className={`flex-1 text-sm font-medium transition-colors ${done ? 'text-text-muted line-through' : 'text-text-primary'}`}>
                      {habit.label}
                    </span>
                    <div className={`transition-all duration-300 ${done ? 'text-primary-500 scale-110' : 'text-dark-300 group-hover:text-text-muted'}`}>
                      {done ? <CheckCircle2 className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); deleteHabit(habit.id) }}
                      className="opacity-0 group-hover:opacity-100 text-red-400/60 hover:text-red-400 transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </motion.div>
                )
              })}
            </div>

            {/* Add Habit */}
            <AnimatePresence>
              {showAdd ? (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-3 flex gap-2"
                >
                  <input
                    autoFocus
                    value={newHabit}
                    onChange={e => setNewHabit(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') addHabit(); if (e.key === 'Escape') setShowAdd(false) }}
                    placeholder="Habit name..."
                    className="flex-1 bg-dark-400/60 border border-primary-500/20 rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500/60"
                  />
                  <button onClick={addHabit} className="btn-primary px-4 py-2 text-sm rounded-lg">Add</button>
                  <button onClick={() => setShowAdd(false)} className="btn-secondary px-3 py-2 text-sm rounded-lg">✕</button>
                </motion.div>
              ) : (
                <motion.button
                  id="add-habit-btn"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onClick={() => setShowAdd(true)}
                  className="mt-3 w-full flex items-center justify-center gap-2 py-2 text-sm text-text-muted hover:text-primary-400 border border-dashed border-dark-300/50 hover:border-primary-500/30 rounded-xl transition-all"
                >
                  <Plus className="w-4 h-4" /> Add a habit
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </main>

      {/* Celebration Overlay */}
      <AnimatePresence>
        {celebrate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 pointer-events-none z-50 flex items-center justify-center"
          >
            {[...Array(20)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-3 h-3 rounded-full"
                style={{ background: ['#00FFFF', '#00FF88', '#FF6B6B', '#FFD700'][i % 4] }}
                initial={{ x: 0, y: 0, opacity: 1 }}
                animate={{
                  x: (Math.random() - 0.5) * 600,
                  y: (Math.random() - 0.5) * 400,
                  opacity: 0,
                  scale: [1, 1.5, 0]
                }}
                transition={{ duration: 1.5, delay: i * 0.05, ease: 'easeOut' }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default GoalsPage
