/** A single toast message. Positioned by the Toast region component. */

import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

export default function Toast({ toasts = [], onDismiss }) {
  if (!toasts.length) return null

  return (
    <div className="toast-region" role="region" aria-label="Notifications">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type] || Info
        return (
          <div
            key={toast.id}
            className={`toast toast--${toast.type}`}
            role={toast.type === 'error' ? 'alert' : 'status'}
            aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
          >
            <Icon size={18} className="toast__icon" aria-hidden="true" />
            <div className="toast__body">
              {toast.title ? <div className="toast__title">{toast.title}</div> : null}
              <div className={toast.title ? 'toast__msg' : 'toast__title'}>{toast.message}</div>
            </div>
            <button
              type="button"
              className="toast__close"
              onClick={() => onDismiss(toast.id)}
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}