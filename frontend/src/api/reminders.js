/**
 * Unified reminder centre API calls.
 *
 * These are IN-APP reminders. They are generated from current database state
 * while the page is open. DailyFlow does not send push notifications, email or
 * SMS, and nothing runs in the background once the browser tab is closed.
 */

import client from './client'

/** GET /api/reminders */
export function fetchReminders(params = {}) {
  return client.get('/api/reminders', { params }).then((res) => res.data)
}

/** GET /api/reminders/summary - small counts for the sidebar badge. */
export function fetchReminderSummary() {
  return client.get('/api/reminders/summary').then((res) => res.data)
}

/** GET /api/reminders/upcoming */
export function fetchUpcomingReminders(params = {}) {
  return client.get('/api/reminders/upcoming', { params }).then((res) => res.data)
}

export const MODULES = [
  { key: 'billbell', label: 'BillBell', color: 'var(--billbell)', soft: 'var(--billbell-soft)' },
  { key: 'dateguard', label: 'DateGuard', color: 'var(--dateguard)', soft: 'var(--dateguard-soft)' },
  { key: 'dosenote', label: 'DoseNote', color: 'var(--dosenote)', soft: 'var(--dosenote-soft)' },
  { key: 'aquahabit', label: 'AquaHabit', color: 'var(--aquahabit)', soft: 'var(--aquahabit-soft)' },
]

export const PRIORITIES = [
  { value: 'urgent', label: 'Urgent', tone: 'danger' },
  { value: 'high', label: 'High', tone: 'warning' },
  { value: 'medium', label: 'Medium', tone: 'info' },
  { value: 'low', label: 'Low', tone: 'neutral' },
]

export const BUCKETS = [
  { value: 'overdue', label: 'Overdue' },
  { value: 'today', label: 'Today' },
  { value: 'upcoming', label: 'Upcoming' },
]

export const CATEGORY_LABELS = {
  bill_overdue: 'Bill overdue',
  bill_due: 'Bill due',
  document_expired: 'Document expired',
  document_expiring: 'Document expiring',
  dose_due: 'Dose due',
  dose_missed: 'Dose missed',
  hydration_progress: 'Hydration',
}

/**
 * Ask the browser for notification permission.
 *
 * Only ever called after the user explicitly presses the button, because
 * browsers block (and users distrust) unsolicited permission requests. A denial
 * is handled gracefully - the in-app reminder centre keeps working either way.
 */
export async function requestNotificationPermission() {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return { supported: false, granted: false, reason: 'unsupported' }
  }
  try {
    const permission = await window.Notification.requestPermission()
    return {
      supported: true,
      granted: permission === 'granted',
      permission,
    }
  } catch {
    return { supported: true, granted: false, reason: 'error' }
  }
}

/** Show one browser notification, if permission was already granted. */
export function showBrowserNotification(title, body) {
  if (typeof window === 'undefined' || !('Notification' in window)) return false
  if (Notification.permission !== 'granted') return false
  try {
    // eslint-disable-next-line no-new
    new Notification(title, { body, tag: 'dailyflow' })
    return true
  } catch {
    return false
  }
}