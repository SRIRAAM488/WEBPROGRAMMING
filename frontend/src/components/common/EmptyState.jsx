/**
 * EmptyState - shown when a list has no records yet.
 *
 * An empty screen should explain *why* it is empty and offer the action that
 * fills it, rather than just showing a blank panel.
 */

export default function EmptyState({
  icon,
  title,
  description,
  action,
  compact = false,
}) {
  return (
    <div className={`empty-state${compact ? ' empty-state--compact' : ''}`}>
      {icon ? <div className="empty-state__icon">{icon}</div> : null}
      <div>
        <div className="empty-state__title">{title}</div>
        {description ? (
          <p className="empty-state__text" style={{ marginTop: 4 }}>
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div style={{ marginTop: 4 }}>{action}</div> : null}
    </div>
  )
}

/**
 * ErrorState - shown when a request failed.
 * Always offers a retry, so a temporary network blip is recoverable.
 */
export function ErrorState({ title = 'Could not load this', message, onRetry, compact = false }) {
  return (
    <div className={`error-state${compact ? ' empty-state--compact' : ''}`} role="alert">
      <div className="error-state__icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <div className="error-state__title">{title}</div>
      {message ? <p className="error-state__text">{message}</p> : null}
      {onRetry ? (
        <button type="button" className="btn btn--secondary btn--sm" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  )
}