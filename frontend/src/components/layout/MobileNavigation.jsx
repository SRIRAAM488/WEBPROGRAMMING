/** Mobile-only: the sticky header and the bottom tab bar. */

import { NavLink } from 'react-router-dom'
import { Bell, Menu, Sparkles } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'
import { NAV_ITEMS } from './Sidebar'
import { usePageMeta } from './Topbar'

export function MobileTopbar({ onOpenDrawer }) {
  const { title } = usePageMeta()

  return (
    <header className="mobile-topbar">
      <div className="mobile-topbar__logo" aria-hidden="true">
        <Sparkles size={18} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="topbar__title" style={{ fontSize: 'var(--fs-md)' }}>
          {title}
        </div>
      </div>

      <button
        type="button"
        className="topbar__icon-btn"
        onClick={onOpenDrawer}
        aria-label="Open navigation menu"
        aria-expanded={false}
      >
        <Menu size={18} />
      </button>
    </header>
  )
}

export function MobileNavigation() {
  const { reminderCount } = useSettings()

  // Five module tabs fit comfortably on any phone. Reminders get a dot instead
  // of a seventh tab so nothing gets squeezed.
  const items = [NAV_ITEMS[0], NAV_ITEMS[1], NAV_ITEMS[2], NAV_ITEMS[3], NAV_ITEMS[4]]

  return (
    <nav className="mobile-nav" aria-label="Primary">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `mobile-nav__item${isActive ? ' mobile-nav__item--active' : ''}`
            }
          >
            <Icon size={19} />
            <span>{item.short}</span>
          </NavLink>
        )
      })}

      <NavLink
        to="/reminders"
        className={({ isActive }) =>
          `mobile-nav__item${isActive ? ' mobile-nav__item--active' : ''}`
        }
      >
        <Bell size={19} />
        <span>Alerts</span>
        {reminderCount > 0 ? <span className="mobile-nav__dot" aria-hidden="true" /> : null}
      </NavLink>
    </nav>
  )
}