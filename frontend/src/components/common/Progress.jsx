/**
 * Progress indicators.
 *
 * ProgressRing  - circular, used by AquaHabit and the dose completion card.
 * ProgressBar   - linear, used for smaller values.
 */

export function ProgressBar({
  value = 0,
  max = 100,
  accent = 'primary',
  size = 'default',
  striped = false,
  label,
  showValue = false,
}) {
  const percent = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  const widthClass = size === 'thin' ? ' progress--thin' : size === 'thick' ? ' progress--thick' : ''

  return (
    <div
      className={`progress${widthClass}${striped ? ' progress--striped' : ''}`}
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label || 'Progress'}
      style={{ '--accent': `var(--${accent})` }}
    >
      <div className="progress__bar" style={{ width: `${percent}%` }} />
      {showValue ? (
        <span className="sr-only">{percent} percent complete</span>
      ) : null}
    </div>
  )
}

export function ProgressRing({
  value = 0,
  max = 100,
  size = 132,
  thickness = 11,
  accent = 'aquahabit',
  label,
  valueText,
  labelText,
}) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - percent / 100)

  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden="true">
        <circle
          className="ring__track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={thickness}
        />
        <circle
          className="ring__fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={thickness}
          stroke={`var(--${accent})`}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>

      <div className="ring__center">
        <span className="ring__value" style={{ color: `var(--${accent})` }}>
          {valueText ?? `${Math.round(percent)}%`}
        </span>
        {labelText || label ? (
          <span className="ring__label">{labelText || label}</span>
        ) : null}
      </div>

      <span className="sr-only" role="progressbar" aria-valuenow={Math.round(percent)}>
        {Math.round(percent)} percent complete
      </span>
    </div>
  )
}

/**
 * StatTile - a small labelled number used inside cards.
 */
export function StatTile({ label, value, tone, icon }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        padding: 'var(--sp-3)',
        background: 'var(--surface-alt)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)',
        minWidth: 0,
      }}
    >
      <span className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        {icon}
        {label}
      </span>
      <strong
        className="text-lg text-num"
        style={{ color: tone ? `var(--${tone})` : 'var(--text)' }}
      >
        {value}
      </strong>
    </div>
  )
}