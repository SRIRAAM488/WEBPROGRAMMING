/**
 * RecentActivity - a feed built from real database timestamps.
 *
 * The backend reads the `created_at`, `payment_date`, `taken_at` and
 * `consumed_at` columns on existing records, so this list can never disagree
 * with the module data.
 */

import { Link } from 'react-router-dom'
import { Activity, Droplets, FileText, Pill, Receipt } from 'lucide-react'
import EmptyState from '../common/EmptyState'
import { formatRelative } from '../../utils/format'

const MODULE_ICONS = {
  billbell: Receipt,
  dateguard: FileText,
  dosenote: Pill,
  aquahabit: Droplets,
}

export default function RecentActivity({ items = [], loading = false, limit = 10 }) {
  if (loading) {
    return (
      <div className="stack stack--sm" aria-hidden="true">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: 40 }} />
        ))}
      </div>
    )
  }

  if (!items.length) {
    return (
      <EmptyState
        compact
        icon={<Activity size={24} />}
        title="No activity yet"
        description="Add a bill, document, dose or glass of water and your actions will appear here."
      />
    )
  }

  return (
    <div className="item-list">
      {items.slice(0, limit).map((item) => {
        const Icon = MODULE_ICONS[item.module] || Activity

        return (
          <Link
            key={item.id}
            to={item.link}
            className="item-row"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <span
              className="item-row__icon"
              style={{
                background: `var(--${item.accent}-soft, var(--primary-soft))`,
                color: `var(--${item.accent}, var(--primary))`,
                width: 32,
                height: 32,
                borderRadius: 9,
              }}
            >
              <Icon size={15} />
            </span>

            <span className="item-row__body">
              <span className="item-row__title" style={{ fontSize: 'var(--fs-base)' }}>
                {item.title}
              </span>
              <span className="item-row__meta text-xs">
                <span className="font-semibold" style={{ color: `var(--${item.accent})` }}>
                  {item.action}
                </span>
                {item.detail ? <span className="dot-sep">{item.detail}</span> : null}
              </span>
            </span>

            <span className="item-row__right">
              <span className="text-xs text-muted text-nowrap">{formatRelative(item.occurred_at)}</span>
            </span>
          </Link>
        )
      })}
    </div>
  )
}