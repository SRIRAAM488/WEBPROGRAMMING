/**
 * PaymentSummary - paid vs unpaid totals for BillBell.
 *
 * Shows the real split as a stacked bar plus the two totals, so the dashboard
 * never has to hide a number behind a chart.
 */

import { CheckCircle2, Clock, Receipt } from 'lucide-react'
import { ProgressBar, StatTile } from '../common/Progress'
import { formatCurrency } from '../../utils/format'
import EmptyState from '../common/EmptyState'

export default function PaymentSummary({ summary, currency = 'INR', loading = false }) {
  if (loading) {
    return (
      <div className="stack stack--sm" aria-hidden="true">
        <div className="skeleton" style={{ height: 16, width: '55%' }} />
        <div className="skeleton" style={{ height: 12 }} />
        <div className="grid grid--2">
          <div className="skeleton" style={{ height: 68 }} />
          <div className="skeleton" style={{ height: 68 }} />
        </div>
      </div>
    )
  }

  if (!summary || summary.total_bills === 0) {
    return (
      <EmptyState
        compact
        icon={<Receipt size={24} />}
        title="No bills yet"
        description="Add your first bill to see paid versus unpaid totals here."
      />
    )
  }

  const paid = Number(summary.total_paid_this_month || 0)
  const unpaid = Number(summary.total_unpaid_amount || 0)
  const total = paid + unpaid
  const paidPercent = total > 0 ? Math.round((paid / total) * 100) : 0

  return (
    <div className="stack">
      <div>
        <div className="row row--between" style={{ marginBottom: 8 }}>
          <span className="text-sm text-muted">Paid this month</span>
          <strong className="text-num">{formatCurrency(paid, currency)}</strong>
        </div>

        {/* Stacked bar: green = paid, coral = still outstanding. */}
        <div
          style={{
            display: 'flex',
            height: 12,
            borderRadius: 'var(--radius-pill)',
            overflow: 'hidden',
            background: 'var(--surface-sunken)',
          }}
          role="img"
          aria-label={`${paidPercent}% paid, ${100 - paidPercent}% outstanding`}
        >
          <div
            style={{
              width: `${paidPercent}%`,
              background: 'var(--success)',
              transition: 'width var(--t-slow)',
            }}
          />
          <div
            style={{
              width: `${100 - paidPercent}%`,
              background: 'var(--billbell)',
              opacity: 0.75,
              transition: 'width var(--t-slow)',
            }}
          />
        </div>

        <div className="row" style={{ gap: 'var(--sp-4)', marginTop: 8, fontSize: 'var(--fs-xs)' }}>
          <span className="chart-legend__item">
            <span
              className="chart-legend__swatch"
              style={{ background: 'var(--success)' }}
              aria-hidden="true"
            />
            Paid ({paidPercent}%)
          </span>
          <span className="chart-legend__item">
            <span className="chart-legend__swatch" style={{ background: 'var(--billbell)' }} aria-hidden="true" />
            Outstanding ({100 - paidPercent}%)
          </span>
        </div>
      </div>

      <div className="grid grid--2">
        <StatTile
          label="Outstanding"
          value={formatCurrency(unpaid, currency, { decimals: 0 })}
          tone="billbell"
          icon={<Clock size={12} />}
        />
        <StatTile
          label="Paid this month"
          value={formatCurrency(paid, currency, { decimals: 0 })}
          tone="success"
          icon={<CheckCircle2 size={12} />}
        />
      </div>

      <ProgressBar
        value={summary.unpaid_count || 0}
        max={summary.total_bills || 1}
        accent="billbell"
        size="thin"
        label="Bills still unpaid"
      />

      <p className="text-xs text-muted">
        {summary.unpaid_count} unpaid of {summary.total_bills} total
        {summary.overdue_count > 0 ? (
          <span className="text-danger"> · {summary.overdue_count} overdue</span>
        ) : null}
      </p>
    </div>
  )
}