/**
 * StatusBadge - a colour-coded pill for every status in the app.
 *
 * One component for every module means colours stay consistent and there is
 * only one place to change if the palette needs adjusting.
 */

import { humanise } from '../../utils/format'

/** Maps a backend status value to a colour tone. */
const TONE_BY_STATUS = {
  // BillBell
  paid: 'success',
  unpaid: 'warning',
  overdue: 'danger',
  // DateGuard
  valid: 'success',
  expiring_soon: 'warning',
  expired: 'danger',
  // DoseNote
  taken: 'success',
  pending: 'warning',
  skipped: 'neutral',
  // Generic
  active: 'success',
  inactive: 'neutral',
  completed: 'success',
  cancelled: 'neutral',
}

/** Colour schemes for the four modules. */
const MODULE_TONES = {
  billbell: 'billbell',
  dateguard: 'dateguard',
  dosenote: 'dosenote',
  aquahabit: 'aquahabit',
}

export default function StatusBadge({ status, label, tone, module: moduleKey, size, dot = true }) {
  const resolvedTone = tone || TONE_BY_STATUS[status] || MODULE_TONES[moduleKey] || 'neutral'
  const resolvedLabel = label || humanise(status)

  return (
    <span className={`badge badge--${resolvedTone}${size === 'lg' ? ' badge--lg' : ''}`}>
      {dot ? <span className="badge__dot" aria-hidden="true" /> : null}
      {resolvedLabel}
    </span>
  )
}

/** Priority pill for the reminder centre. */
export function PriorityBadge({ priority }) {
  const icon = { urgent: '●', high: '◆', medium: '▲', low: '○' }[priority] || '○'
  return (
    <span className={`priority priority--${priority}`}>
      <span aria-hidden="true">{icon}</span>
      {humanise(priority)}
    </span>
  )
}

/** Expiry countdown chip: "3 days left" / "Expired 2 days ago". */
export function ExpiryChip({ daysRemaining, compact = false }) {
  const days = Number(daysRemaining ?? 0)

  if (days < 0) {
    const n = Math.abs(days)
    return (
      <span className="badge badge--danger">
        {compact ? `${n}d ago` : `Expired ${n} day${n === 1 ? '' : 's'} ago`}
      </span>
    )
  }
  if (days === 0) return <span className="badge badge--danger">Expires today</span>
  if (days === 1) return <span className="badge badge--warning">Expires tomorrow</span>
  if (days <= 7) return <span className="badge badge--warning">{days} days left</span>
  if (days <= 30) return <span className="badge badge--info">{days} days left</span>
  return <span className="badge badge--success">{days} days left</span>
}