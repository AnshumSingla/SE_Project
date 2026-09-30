import { motion } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LogOut, Zap, LayoutDashboard, Target } from 'lucide-react'

const Navbar = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/goals', label: 'Goals', icon: <Target className="w-4 h-4" /> },
  ]

  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed top-0 w-full z-50 glass-nav border-b border-primary-500/30"
    >
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-dark-500" />
            </div>
            <span className="text-xl font-bold text-glow">Smart Reminder</span>
          </div>

          {/* Nav Links */}
          {user && (
            <div className="flex items-center gap-1">
              {navLinks.map(link => {
                const active = location.pathname === link.to
                return (
                  <Link key={link.to} to={link.to}>
                    <motion.div
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                        active
                          ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                          : 'text-text-secondary hover:text-text-primary hover:bg-dark-400/40'
                      }`}
                    >
                      {link.icon}
                      {link.label}
                    </motion.div>
                  </Link>
                )
              })}
            </div>
          )}

          {/* User Profile */}
          <div className="flex items-center space-x-4">
            {user && (
              <>
                <div className="flex items-center space-x-3 glass-card px-4 py-2 rounded-full">
                  <img
                    src={user.picture}
                    alt={user.name}
                    className="w-8 h-8 rounded-full ring-2 ring-primary-500/50"
                  />
                  <div className="hidden sm:block">
                    <p className="text-sm font-medium text-text-primary">{user.name}</p>
                    <p className="text-xs text-text-secondary">{user.email}</p>
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={logout}
                  className="p-2 text-text-secondary hover:text-primary-500 transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </motion.button>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.nav>
  )
}

export default Navbar