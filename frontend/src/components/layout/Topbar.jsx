/** Top bar: page title, today's date, reminder indicator and profile area. */

import { Link, useLocation } from 'react-router-dom'
import { BellRing, Moon, Sun, User } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'
import { formatLongToday } from '../../utils/format'
import { NAV_ITEMS } from './Sidebar'

/** Works out the page title from the current route. */
export function usePageMeta() {
  const { pathname } = useLocation()

  if (pathname === '/') return { title: 'Dashboard', subtitle: 'Your whole day at a glance' }
  if (pathname.startsWith('/not-found')) return { title: 'Page not found', subtitle: '' }

  const item = NAV_ITEMS.find((nav) => nav.to !== '/' && pathname.startsWith(nav.to))
  if (item) {
    return {
      title: item.label,
      subtitle: {
        billbell: 'Bills, due dates and payments',
        dateguard: 'Documents and expiry dates',
        dosenote: 'Medication schedules and dose history',
        aquahabit: 'Water intake and hydration goals',
        reminders: 'Everything that needs your attention',
        settings: 'Preferences and app information',
      }[item.to.slice(1)] || '',
    }
  }
  return { title: 'DailyFlow', subtitle: '' }
}

export default function Topbar() {
  const { theme, toggleTheme, reminderCount } = useSettings()
  const { title, subtitle } = usePageMeta()

  return (
    <header className="topbar">
      <div className="topbar__heading">
        <div className="topbar__title">{title}</div>
        <div className="topbar__date">
          {subtitle ? `${subtitle} · ` : ''}
          {formatLongToday()}
        </div>
      </div>

      <div className="topbar__actions">
        {/* Reminder indicator - only dot-marked when there is something pending */}
        <Link
          to="/reminders"
          className={`topbar__icon-btn has-tip has-tip--below${
            reminderCount > 0 ? ' topbar__icon-btn--has-dot' : ''
          }`}
          aria-label={
            reminderCount > 0
              ? `Reminders: ${reminderCount} need attention`
              : 'Reminders: none pending'
          }
          data-tip={reminderCount > 0 ? `${reminderCount} reminders` : 'No reminders'}
        >
          <BellRing size={18} />
        </Link>

        <button
          type="button"
          className="topbar__icon-btn has-tip has-tip--below"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          data-tip={`${theme === 'dark' ? 'Light' : 'Dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <div className="topbar__profile">
          <div className="topbar__avatar" aria-hidden="true">
            <User size={15} />
          </div>
          <div className="hide-mobile">
            <div className="topbar__profile-name">My Day</div>
            <div className="topbar__profile-role">Local account</div>
          </div>
        </div>
      </div>
    </header>
  )
}