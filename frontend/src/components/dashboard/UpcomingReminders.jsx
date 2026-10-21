/**
 * UpcomingReminders - the combined feed from all four modules.
 *
 * Reminder rows are clickable and navigate straight to the record they came
 * from (the backend supplies the `link` for each one).
 */

import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, BellRing, Droplets, FileText, Pill, Receipt } from 'lucide-react'
import { PriorityBadge } from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { formatDate, formatRelative } from '../../utils/format'

const MODULE_ICONS = {
  billbell: Receipt,
  dateguard: FileText,
  dosenote: Pill,
  aquahabit: Droplets,
}

export default function UpcomingReminders({ reminders = [], loading = false, limit = 6, compact = false }) {
  const navigate = useNavigate()
  const visible = reminders.slice(0, limit)

  if (loading) {
    return (
      <div className="stack stack--sm" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: 58 }} />
        ))}
      </div>
    )
  }

  if (!reminders.length) {
    return (
      <EmptyState
        compact
        icon={<BellRing size={24} />}
        title="Nothing needs attention"
        description="Bills, document expiries, doses and water goals are all on track right now."
      />
    )
  }

  return (
    <div className="item-list">
      {visible.map((reminder) => {
        const Icon = MODULE_ICONS[reminder.module] || BellRing

        return (
          <button
            key={reminder.id}
            type="button"
            className="item-row"
            style={{ width: '100%', textAlign: 'left', cursor: 'pointer' }}
            onClick={() => navigate(reminder.link)}
          >
            <span
              className="item-row__icon"
              style={{
                background: `var(--${reminder.module}-soft)`,
                color: `var(--${reminder.module})`,
              }}
            >
              <Icon size={17} />
            </span>

            <span className="item-row__body">
              <span className="item-row__title">{reminder.title}</span>
              <span className="item-row__meta">
                <PriorityBadge priority={reminder.priority} />
                <span className="dot-sep">{formatDate(reminder.due_date)}</span>
                {!compact && reminder.description ? (
                  <span className="text-truncate" style={{ maxWidth: 320 }}>
                    {reminder.description}
                  </span>
                ) : null}
              </span>
            </span>

            <span className="item-row__right">
              <span className="text-xs text-muted text-nowrap">{formatRelative(reminder.due_at)}</span>
              <ArrowRight
                size={14}
                style={{ marginLeft: 'auto', marginTop: 3, color: 'var(--text-faint)' }}
                aria-hidden="true"
              />
            </span>
          </button>
        )
      })}
    </div>
  )
}

/** The reminder centre's grouped view (overdue / today / upcoming). */
export function ReminderGroup({ title, items = [], tone = 'neutral', emptyText }) {
  const navigate = useNavigate()

  return (
    <section className="stack stack--sm">
      <div className="row row--between">
        <h3 className="row" style={{ gap: 8, fontSize: 'var(--fs-md)' }}>
          {tone === 'danger' ? (
            <AlertTriangle size={16} style={{ color: 'var(--danger)' }} />
          ) : null}
          {title}
          <span className="badge badge--neutral">{items.length}</span>
        </h3>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted" style={{ padding: 'var(--sp-3) 0' }}>
          {emptyText}
        </p>
      ) : (
        <div className="item-list card" style={{ borderRadius: 'var(--radius)' }}>
          {items.map((reminder) => {
            const Icon = MODULE_ICONS[reminder.module] || BellRing
            return (
              <button
                key={reminder.id}
                type="button"
                className="item-row"
                style={{ width: '100%', textAlign: 'left', cursor: 'pointer' }}
                onClick={() => navigate(reminder.link)}
              >
                <span
                  className="item-row__icon"
                  style={{
                    background: `var(--${reminder.module}-soft)`,
                    color: `var(--${reminder.module})`,
                  }}
                >
                  <Icon size={16} />
                </span>

                <span className="item-row__body">
                  <span className="item-row__title">{reminder.title}</span>
                  <span className="item-row__meta">
                    <PriorityBadge priority={reminder.priority} />
                    <span className="dot-sep">{formatDate(reminder.due_date)}</span>
                    <span className="dot-sep text-truncate">{reminder.description}</span>
                  </span>
                </span>

                <ArrowRight size={15} style={{ color: 'var(--text-faint)' }} aria-hidden="true" />
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}