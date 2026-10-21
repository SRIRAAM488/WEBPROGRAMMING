/**
 * Toast context - one place to show success / error messages.
 *
 * Any component can call `useToast().success('Saved!')` and the message
 * appears in the corner of the screen. Using this instead of `alert()` keeps
 * the interface calm and does not interrupt the user.
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import Toast from '../components/common/Toast'

const ToastContext = createContext(null)

let nextId = 1

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const push = useCallback(
    (message, { type = 'info', title, duration = 4200 } = {}) => {
      const id = nextId++
      setToasts((current) => [...current, { id, message, type, title }])
      if (duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), duration)
        )
      }
      return id
    },
    [dismiss]
  )

  const success = useCallback(
    (message, options) => push(message, { ...options, type: 'success' }),
    [push]
  )
  const error = useCallback(
    (message, options) => push(message, { ...options, type: 'error', duration: 6500 }),
    [push]
  )
  const warning = useCallback(
    (message, options) => push(message, { ...options, type: 'warning' }),
    [push]
  )
  const info = useCallback((message, options) => push(message, { ...options, type: 'info' }), [push])

  const value = useMemo(
    () => ({ toasts, push, success, error, warning, info, dismiss }),
    [toasts, push, success, error, warning, info, dismiss]
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toast toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used inside a <ToastProvider>.')
  }
  return context
}

export default ToastContext