import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Scan, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

// The parent owns the sync (scan + create events + refresh). This component only
// triggers it, so a click results in exactly ONE scan.
const EmailScanner = ({ onScan, userId }) => {
  const [isScanning, setIsScanning] = useState(false)
  const [lastScan, setLastScan] = useState(null)

  const handleScanEmails = async () => {
    if (!userId) {
      toast.error('Please sign in to scan emails')
      return
    }

    setIsScanning(true)
    
    try {
      await onScan()
      setLastScan(new Date().toLocaleString())
    } catch (error) {
      console.error('Email scan error:', error)
      toast.error('Failed to scan emails. Please try again.')
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <motion.div
      id="email-scanner-card"
      whileHover={{ scale: 1.02 }}
      className="glass-card p-6 rounded-xl neon-glow"
    >
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center">
          <Mail className="w-5 h-5 text-primary-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text-primary">Email Scanner</h3>
          <p className="text-sm text-text-secondary">AI-powered deadline intelligence</p>
        </div>
      </div>

      <div className="space-y-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          transition={{ duration: 0.15 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleScanEmails}
          disabled={isScanning}
          className="w-full btn-primary flex items-center justify-center space-x-2"
        >
          {isScanning ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Scanning Emails...</span>
            </>
          ) : (
            <>
              <Scan className="w-5 h-5" />
              <span>Scan Recent Emails</span>
            </>
          )}
        </motion.button>

        {lastScan && (
          <div className="text-xs text-text-secondary text-center">
            Last scan: {lastScan}
          </div>
        )}

        <div className="bg-dark-300/30 rounded-lg p-3">
          <h4 className="text-sm font-medium text-text-primary mb-2">What we scan for:</h4>
          <ul className="text-xs text-text-secondary space-y-1">
            <li>• Job & Internship opportunities</li>
            <li>• University assignments & exams</li>
            <li>• Bills, fees & utility payments</li>
            <li>• Interviews, meetings & bookings</li>
          </ul>
        </div>
      </div>
    </motion.div>
  )
}

export default EmailScanner