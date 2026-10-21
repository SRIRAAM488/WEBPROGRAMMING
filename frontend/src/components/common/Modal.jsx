/**
 * Modal - an accessible dialog used for every add/edit form.
 *
 * Behaviour that matters for usability and accessibility:
 *  - closes on Escape
 *  - traps focus inside the dialog while it is open
 *  - clicking the backdrop closes it
 *  - body scroll is locked while open
 *  - returns focus to whatever opened it
 */

import { useCallback, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function Modal({
  open,
  onClose,
  title,
  description,
  icon,
  accent = 'primary',
  size = 'md',
  children,
  footer,
  closeOnBackdrop = true,
}) {
  const dialogRef = useRef(null)
  const previouslyFocused = useRef(null)

  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose?.()
        return
      }

      // Simple focus trap: keep Tab cycling inside the dialog.
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = Array.from(dialogRef.current.querySelectorAll(FOCUSABLE)).filter(
        (element) => element.offsetParent !== null
      )
      if (!focusable.length) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (!open) return undefined

    previouslyFocused.current = document.activeElement
    document.body.style.overflow = 'hidden'

    // Move focus into the dialog once it has rendered.
    const timer = setTimeout(() => {
      const target = dialogRef.current?.querySelector(
        'input:not([type="hidden"]), select, textarea, button'
      )
      target?.focus()
    }, 40)

    return () => {
      clearTimeout(timer)
      document.body.style.overflow = ''
      previouslyFocused.current?.focus?.()
    }
  }, [open])

  if (!open) return null

  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (closeOnBackdrop && event.target === event.currentTarget) onClose?.()
      }}
    >
      <div
        ref={dialogRef}
        className={`modal ${size !== 'md' ? `modal--${size}` : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        onKeyDown={handleKeyDown}
      >
        <header className="modal__header">
          {icon ? (
            <div
              className="modal__icon"
              style={{
                background: `var(--${accent}-soft, var(--primary-soft))`,
                color: `var(--${accent}, var(--primary))`,
              }}
            >
              {icon}
            </div>
          ) : null}

          <div style={{ minWidth: 0 }}>
            <h2 className="modal__title">{title}</h2>
            {description ? <p className="modal__desc">{description}</p> : null}
          </div>

          <button
            type="button"
            className="modal__close"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </header>

        <div className="modal__body">{children}</div>

        {footer ? <footer className="modal__footer">{footer}</footer> : null}
      </div>
    </div>,
    document.body
  )
}