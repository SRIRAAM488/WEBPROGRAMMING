/**
 * QuickActions - four one-click shortcuts.
 *
 * Every button opens the real form for that module, so there are no dead
 * controls anywhere in the dashboard.
 */

import { Link } from 'react-router-dom'
import { Droplets, FileText, Pill, Plus, Receipt } from 'lucide-react'

const ACTIONS = [
  {
    key: 'billbell',
    to: '/bills?action=add',
    label: 'Add a bill',
    description: 'Track a new payment',
    icon: Receipt,
  },
  {
    key: 'dateguard',
    to: '/documents?action=add',
    label: 'Add a document',
    description: 'Get expiry reminders',
    icon: FileText,
  },
  {
    key: 'dosenote',
    to: '/medications?action=add',
    label: 'Add a schedule',
    description: 'Set up dose times',
    icon: Pill,
  },
  {
    key: 'aquahabit',
    to: '/hydration?action=add',
    label: 'Log a glass',
    description: 'Record water intake',
    icon: Droplets,
  },
]

export default function QuickActions({ onQuickLog }) {
  return (
    <div className="grid grid--2" style={{ gap: 'var(--sp-3)' }}>
      {ACTIONS.map((action) => {
        const Icon = action.icon

        // AquaHabit gets a real action (log water) because it is a one-tap action.
        if (action.key === 'aquahabit' && onQuickLog) {
          return (
            <button
              key={action.key}
              type="button"
              className="card card--hoverable"
              onClick={onQuickLog}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--sp-3)',
                padding: 'var(--sp-3) var(--sp-4)',
                textAlign: 'left',
                borderLeft: '3px solid var(--aquahabit)',
              }}
            >
              <span
                className="item-row__icon"
                style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
              >
                <Icon size={17} />
              </span>
              <span style={{ minWidth: 0 }}>
                <span className="item-row__title">{action.label}</span>
                <span className="text-xs text-muted" style={{ display: 'block' }}>
                  {action.description}
                </span>
              </span>
              <Plus size={15} style={{ marginLeft: 'auto', color: 'var(--aquahabit)' }} />
            </button>
          )
        }

        return (
          <Link
            key={action.key}
            to={action.to}
            className="card card--hoverable"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--sp-3)',
              padding: 'var(--sp-3) var(--sp-4)',
              borderLeft: `3px solid var(--${action.key})`,
              textDecoration: 'none',
            }}
          >
            <span
              className="item-row__icon"
              style={{ background: `var(--${action.key}-soft)`, color: `var(--${action.key})` }}
            >
              <Icon size={17} />
            </span>
            <span style={{ minWidth: 0 }}>
              <span className="item-row__title">{action.label}</span>
              <span className="text-xs text-muted" style={{ display: 'block' }}>
                {action.description}
              </span>
            </span>
            <Plus
              size={15}
              style={{ marginLeft: 'auto', color: `var(--${action.key})` }}
              aria-hidden="true"
            />
          </Link>
        )
      })}
    </div>
  )
}