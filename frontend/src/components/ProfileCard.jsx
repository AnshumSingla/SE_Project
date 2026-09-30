import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { UserCog } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiService } from '../services/apiService'
import { useAuth } from '../context/AuthContext'

const EMPTY = {
  roles: '',
  disciplines: '',
  graduation_year: '',
  cgpa: '',
  exclude_keywords: '',
  strictness: 'balanced',
  auto_add: 'confident',
  scan_paused: false,
  roll_number: '',
  other_emails: ''
}

const toForm = (p) => ({
  roles: (p?.roles || []).join(', '),
  disciplines: (p?.disciplines || []).join(', '),
  graduation_year: p?.graduation_year || '',
  cgpa: p?.cgpa ?? '',
  exclude_keywords: (p?.exclude_keywords || []).join(', '),
  strictness: p?.strictness || 'balanced',
  auto_add: p?.auto_add || 'confident',
  scan_paused: !!p?.scan_paused,
  roll_number: p?.roll_number || '',
  other_emails: (p?.other_emails || []).join(', ')
})

const inputClass =
  'w-full bg-dark-400/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-500'

// Who you are, so mails meant for other branches/batches are kept out of your calendar.
// Stored in your own Google Drive (app data folder), never in a database.
const ProfileCard = ({ onSaved }) => {
  const { logout } = useAuth()
  const [form, setForm] = useState(EMPTY)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [needsReauth, setNeedsReauth] = useState(false)

  useEffect(() => {
    let cancelled = false
    apiService
      .getProfile()
      .then((p) => !cancelled && setForm(toForm(p)))
      .catch((err) => {
        if (err.code === 'drive_permission_needed') setNeedsReauth(true)
      })
      .finally(() => !cancelled && setLoaded(true))
    return () => {
      cancelled = true
    }
  }, [])

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const deleteMyData = async () => {
    const ok = window.confirm(
      'Delete your stored access token, profile and scan history, and revoke this app\'s access to your Google account?\n\nCalendar events already created stay on your calendar.'
    )
    if (!ok) return
    try {
      await apiService.deleteAccount()
      logout()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const saved = await apiService.saveProfile(form)
      setForm(toForm(saved))
      setNeedsReauth(false)
      toast.success('Profile saved to your Google Drive')
      onSaved?.(saved)
    } catch (err) {
      if (err.code === 'drive_permission_needed') setNeedsReauth(true)
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div id="profile-card" className="glass-card p-6 rounded-xl">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-lg flex items-center justify-center">
          <UserCog className="w-5 h-5 text-primary-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text-primary">Your profile</h3>
          <p className="text-xs text-text-secondary">Used to hide mails meant for other branches or batches.</p>
        </div>
      </div>

      {needsReauth && (
        <p className="text-sm text-yellow-400 mb-3">
          To save your profile, sign out and sign in again and allow access to this app's private Drive storage.
        </p>
      )}

      <form onSubmit={save} className="space-y-3">
        <label className="block text-xs text-text-secondary">
          Role(s) you want
          <input className={inputClass} value={form.roles} onChange={set('roles')} placeholder="Software Engineer, Data Analyst" />
        </label>
        <label className="block text-xs text-text-secondary">
          Branch / discipline
          <input className={inputClass} value={form.disciplines} onChange={set('disciplines')} placeholder="Computer Science" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs text-text-secondary">
            Graduation year
            <input className={inputClass} type="number" min="2000" max="2100" value={form.graduation_year} onChange={set('graduation_year')} placeholder="2027" />
          </label>
          <label className="block text-xs text-text-secondary">
            CGPA
            <input className={inputClass} type="number" min="0" max="10" step="0.01" value={form.cgpa} onChange={set('cgpa')} placeholder="8.2" />
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs text-text-secondary">
            Roll / enrollment no.
            <input className={inputClass} value={form.roll_number} onChange={set('roll_number')} placeholder="102103456" />
          </label>
          <label className="block text-xs text-text-secondary">
            Other email(s)
            <input className={inputClass} value={form.other_emails} onChange={set('other_emails')} placeholder="you@thapar.edu" />
          </label>
        </div>
        <p className="text-xs text-text-secondary -mt-1">
          Used only to check whether you are on a shortlist attached to a mail. Read in memory, never sent anywhere.
        </p>
        <label className="block text-xs text-text-secondary">
          Always hide mails containing
          <input className={inputClass} value={form.exclude_keywords} onChange={set('exclude_keywords')} placeholder="sales, telecaller" />
        </label>
        <label className="block text-xs text-text-secondary">
          How strict?
          <select className={inputClass} value={form.strictness} onChange={set('strictness')}>
            <option value="lenient">Lenient: only hide my exclusions</option>
            <option value="balanced">Balanced: also hide other branches and batches</option>
            <option value="strict">Strict: also hide CGPA cut-offs I don't meet</option>
          </select>
        </label>
        <label className="block text-xs text-text-secondary">
          Automatic scanning
          <select className={inputClass} value={form.auto_add} onChange={set('auto_add')}>
            <option value="confident">Add clear events, ask me about unsure ones</option>
            <option value="all">Add everything relevant</option>
            <option value="off">Never add automatically (review everything)</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-xs text-text-secondary">
          <input type="checkbox" checked={form.scan_paused} onChange={(e) => setForm((f) => ({ ...f, scan_paused: e.target.checked }))} />
          Pause automatic scanning
        </label>
        <button type="submit" disabled={saving || !loaded} className="w-full btn-secondary">
          {saving ? 'Saving...' : 'Save profile'}
        </button>
        <button type="button" onClick={deleteMyData} className="w-full text-xs text-red-400 hover:underline">
          Delete my data and sign out
        </button>
      </form>
    </motion.div>
  )
}

export default ProfileCard
