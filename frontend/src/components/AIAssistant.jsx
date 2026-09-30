import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageCircle, X, Send, Loader2, Bot, User, Sparkles } from 'lucide-react'
import { apiService } from '../services/apiService'
import { useAuth } from '../context/AuthContext'

const SUGGESTED_PROMPTS = [
  "What should I focus on today?",
  "Which deadline is most urgent?",
  "Help me plan my week",
  "What tasks can I complete in 1 hour?",
]

const AIAssistant = ({ events = [], externalMessage = null, onExternalMessageConsumed }) => {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'model',
      text: "Hi! I'm your AI productivity companion powered by Gemini. I can see your upcoming deadlines and help you prioritise, plan, and stay on track. What can I help you with? 🚀"
    }
  ])
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus()
  }, [open])

  // Handle external message from other components (e.g. TaskPriorityPanel)
  useEffect(() => {
    if (externalMessage) {
      setOpen(true)
      // Small delay to let panel open first
      setTimeout(() => sendMessage(externalMessage), 100)
      if (onExternalMessageConsumed) onExternalMessageConsumed()
    }
  }, [externalMessage])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const messageText = (text || input).trim()
    if (!messageText || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: messageText }])
    setLoading(true)

    try {
      const result = await apiService.chatWithAI(user?.id, messageText, events, history)
      if (result.success) {
        setMessages(prev => [...prev, { role: 'model', text: result.response }])
        setHistory(result.updated_history || [])
      } else {
        setMessages(prev => [...prev, { role: 'model', text: "Sorry, I couldn't connect to the AI right now. Please try again." }])
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'model', text: `Sorry, something went wrong: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* Floating Button */}
      <motion.button
        id="ai-assistant-toggle"
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/40 text-dark-500"
        whileHover={{ scale: 1.1, boxShadow: '0 0 24px rgba(0,255,255,0.5)' }}
        whileTap={{ scale: 0.95 }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {open
            ? <motion.span key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.2 }}><X className="w-6 h-6" /></motion.span>
            : <motion.span key="chat" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.2 }}><MessageCircle className="w-6 h-6" /></motion.span>
          }
        </AnimatePresence>
      </motion.button>

      {/* Chat Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            id="ai-assistant-panel"
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-24 right-6 z-50 w-96 max-h-[560px] flex flex-col glass-card rounded-2xl border border-primary-500/30 shadow-2xl shadow-primary-500/20 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-primary-500/10 to-accent-500/10 border-b border-primary-500/20">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-dark-500" />
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">Gemini AI Assistant</p>
                <p className="text-xs text-text-secondary">{events.length} deadline{events.length !== 1 ? 's' : ''} in context</p>
              </div>
              <motion.div
                className="ml-auto w-2 h-2 rounded-full bg-green-400"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs ${
                    msg.role === 'user'
                      ? 'bg-primary-500/20 text-primary-400'
                      : 'bg-accent-500/20 text-accent-500'
                  }`}>
                    {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                  </div>
                  <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-primary-500/20 text-text-primary rounded-tr-sm'
                      : 'bg-dark-400/60 text-text-secondary rounded-tl-sm'
                  }`}>
                    {msg.text}
                  </div>
                </motion.div>
              ))}

              {loading && (
                <div className="flex gap-2">
                  <div className="w-7 h-7 rounded-full bg-accent-500/20 flex items-center justify-center">
                    <Bot className="w-3.5 h-3.5 text-accent-500" />
                  </div>
                  <div className="bg-dark-400/60 px-3 py-2 rounded-xl rounded-tl-sm flex items-center gap-1">
                    {[0,1,2].map(i => (
                      <motion.div key={i} className="w-1.5 h-1.5 rounded-full bg-primary-500"
                        animate={{ y: [0, -5, 0] }}
                        transition={{ duration: 0.6, delay: i * 0.15, repeat: Infinity }}
                      />
                    ))}
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Suggested Prompts (only if conversation is fresh) */}
            {messages.length <= 1 && (
              <div className="px-4 pb-2 flex flex-wrap gap-1.5">
                {SUGGESTED_PROMPTS.map(p => (
                  <button
                    key={p}
                    onClick={() => sendMessage(p)}
                    className="text-xs bg-primary-500/10 hover:bg-primary-500/20 border border-primary-500/20 text-primary-400 rounded-full px-3 py-1 transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="px-3 pb-3 pt-2 border-t border-primary-500/20 flex gap-2">
              <input
                ref={inputRef}
                id="ai-chat-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your deadlines..."
                className="flex-1 bg-dark-400/60 border border-primary-500/20 rounded-xl px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary-500/60 focus:ring-1 focus:ring-primary-500/30 transition-all"
                disabled={loading}
              />
              <motion.button
                id="ai-send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-dark-500 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export default AIAssistant
