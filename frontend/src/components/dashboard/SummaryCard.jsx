/**
 * SummaryCard - the four dashboard overview cards.
 *
 * Every number passed in here comes from GET /api/dashboard/summary. Nothing on
 * this component is hard-coded.
 *
 * Icon props come in two different shapes, which is worth knowing:
 *   - `icon`      a ready-made JSX element, e.g.  icon={<Receipt size={20} />}
 *   - `stats[].icon`  the component *reference*, e.e.  icon: Receipt
 *
 * The stats list passes the reference because each entry needs a smaller size
 * than the card header, so the component is rendered here with its own props.
 * Passing `<Receipt size={13} />` instead would hand React an already-created
 * element where it expects a component type, which crashes the render.
 */

import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'

export default function SummaryCard({
  module: moduleKey,
  icon,
  title,
  hint,
  hero,
  heroUnit,
  stats = [],
  to,
  footer,
}) {
  return (
    <Link
      to={to}
      className="summary-card"
      style={{ '--accent': `var(--${moduleKey})`, '--accent-soft': `var(--${moduleKey}-soft)` }}
    >
      <div className="summary-card__top">
        <div className="summary-card__icon">{icon}</div>
        <div style={{ minWidth: 0 }}>
          <div className="summary-card__name">{title}</div>
          {hint ? <div className="summary-card__hint">{hint}</div> : null}
        </div>
      </div>

      {hero !== undefined && hero !== null ? (
        <div className="summary-card__hero">
          <span className="summary-card__value">{hero}</span>
          {heroUnit ? <span className="summary-card__unit">{heroUnit}</span> : null}
        </div>
      ) : null}

      {stats.length ? (
        <div className="summary-card__stats">
          {stats.map((stat) => {
            // Capitalised so JSX treats it as a component, not a DOM tag name.
            const StatIcon = stat.icon
            return (
              <div
                key={stat.label}
                className={`summary-card__stat${stat.tone ? ` summary-card__stat--${stat.tone}` : ''}`}
              >
                {StatIcon ? <StatIcon size={13} aria-hidden="true" /> : null}
                <span>{stat.label}</span>
                <strong>{stat.value}</strong>
              </div>
            )
          })}
        </div>
      ) : null}

      {footer ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 'var(--fs-xs)',
            color: `var(--${moduleKey})`,
            fontWeight: 650,
            paddingTop: 4,
          }}
        >
          {footer}
          <ArrowRight size={12} aria-hidden="true" />
        </div>
      ) : null}
    </Link>
  )
}