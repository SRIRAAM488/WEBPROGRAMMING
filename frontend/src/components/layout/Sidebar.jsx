/** Sidebar navigation (desktop) / drawer (mobile). */

import { NavLink } from 'react-router-dom'
import {
  BellRing,
  Droplets,
  FileText,
  LayoutDashboard,
  Pill,
  Receipt,
  Settings,
  Sparkles,
} from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'

/**
 * The module list lives in one array so the sidebar, the mobile bottom nav and
 * any future navigation surface stay in sync.
 */
export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true, accent: 'primary', short: 'Home' },
  { to: '/bills', label: 'BillBell', icon: Receipt, accent: 'billbell', short: 'Bills' },
  { to: '/documents', label: 'DateGuard', icon: FileText, accent: 'dateguard', short: 'Docs' },
  { to: '/medications', label: 'DoseNote', icon: Pill, accent: 'dosenote', short: 'Doses' },
  { to: '/hydration', label: 'AquaHabit', icon: Droplets, accent: 'aquahabit', short: 'Water' },
  { to: '/reminders', label: 'Reminders', icon: BellRing, accent: 'primary', badge: true, short: 'Alerts' },
  { to: '/settings', label: 'Settings', icon: Settings, accent: 'primary', short: 'Settings' },
]

export default function Sidebar({ open, onNavigate }) {
  const { reminderCount } = useSettings()

  return (
    <aside className={`sidebar${open ? ' sidebar--open' : ''}`} aria-label="Main navigation">
      <div className="sidebar__brand">
        <div className="sidebar__logo" aria-hidden="true">
          <Sparkles size={21} />
        </div>
        <div>
          <div className="sidebar__title">DailyFlow</div>
          <div className="sidebar__tagline">Stay on top of everyday life.</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        <div className="sidebar__section-label">Overview</div>

        {NAV_ITEMS.slice(0, 1).map((item) => (
          <NavItem key={item.to} item={item} onNavigate={onNavigate} />
        ))}

        <div className="sidebar__section-label">Modules</div>

        {NAV_ITEMS.slice(1, 5).map((item) => (
          <NavItem key={item.to} item={item} onNavigate={onNavigate} />
        ))}

        <div className="sidebar__section-label">More</div>

        {NAV_ITEMS.slice(5).map((item) => (
          <NavItem
            key={item.to}
            item={item}
            onNavigate={onNavigate}
            badgeCount={item.badge ? reminderCount : 0}
          />
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__note">
          <BellRing size={14} aria-hidden="true" />
          <span>
            Reminders are shown while DailyFlow is open. There is no email or SMS
            service configured.
          </span>
        </div>
      </div>
    </aside>
  )
}

function NavItem({ item, onNavigate, badgeCount = 0 }) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
    >
      <span
        className="nav-link__icon"
        style={{
          background: `var(--${item.accent}-soft, var(--primary-soft))`,
          color: `var(--${item.accent})`,
        }}
      >
        <Icon size={15} />
      </span>

      <span className="nav-link__label">{item.label}</span>

      {badgeCount > 0 ? (
        <span className="nav-link__badge" aria-label={`${badgeCount} active reminders`}>
          {badgeCount > 99 ? '99+' : badgeCount}
        </span>
      ) : null}
    </NavLink>
  )
}