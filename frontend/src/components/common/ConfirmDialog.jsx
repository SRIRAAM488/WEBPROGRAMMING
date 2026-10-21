/**
 * ConfirmDialog - asks before anything destructive happens.
 *
 * Every delete in DailyFlow goes through this. It focuses the "cancel" button
 * by default so a stray Enter keypress cannot delete data.
 */

import { AlertTriangle, HelpCircle, Trash2 } from 'lucide-react'
import Modal from './Modal'

const ICONS = {
  danger: { Icon: Trash2, tone: 'danger' },
  warning: { Icon: AlertTriangle, tone: 'warning' },
  primary: { Icon: HelpCircle, tone: 'primary' },
}

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  description,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  tone = 'danger',
  busy = false,
  children,
}) {
  const { Icon, tone: toneClass } = ICONS[tone] || ICONS.danger

  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onClose}
      title={title}
      size="sm"
      closeOnBackdrop={!busy}
      footer={
        <>
          <button type="button" className="btn btn--secondary" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={tone === 'danger' ? 'btn btn--danger' : 'btn btn--primary'}
            onClick={onConfirm}
            disabled={busy}
            autoFocus
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <div className="row" style={{ gap: 'var(--sp-4)', alignItems: 'flex-start' }}>
        <div className={`confirm-icon confirm-icon--${toneClass}`}>
          <Icon size={22} />
        </div>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 'var(--fs-md)', lineHeight: 1.5 }}>{description}</p>
          {children}
        </div>
      </div>
    </Modal>
  )
}