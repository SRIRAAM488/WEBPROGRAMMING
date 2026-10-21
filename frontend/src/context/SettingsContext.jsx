/**
 * Settings context.
 *
 * Holds the user's preferences (currency, theme, reminder windows) plus the
 * sidebar reminder badge count. The data comes from the backend, so the theme
 * and currency you choose follow you between sessions.
 *
 * The theme is also mirrored into localStorage, which index.html reads before
 * React boots. That is what stops a white flash when you switch to dark mode.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { fetchSettings, updateSettings } from '../api/settings'
import { fetchReminderSummary } from '../api/reminders'

const SettingsContext = createContext(null)

export const THEME_STORAGE_KEY = 'dailyflow-theme'

/** Apply a theme to <html> and remember it for the next page load. */
export function applyTheme(theme) {
  const value = theme === 'dark' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', value)
  try {
    localStorage.setItem(THEME_STORAGE_KEY, value)
  } catch {
    // Private browsing mode can block localStorage; the theme still applies
    // for this session, it just will not be remembered.
  }
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reminderCount, setReminderCount] = useState(0)

  const refreshReminders = useCallback(async () => {
    try {
      const summary = await fetchReminderSummary()
      setReminderCount(summary.total || 0)
    } catch {
      // The badge is decoration; if it fails, simply show no badge.
      setReminderCount(0)
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      setError(null)
      const data = await fetchSettings()
      setSettings(data)
      applyTheme(data.theme)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    refreshReminders()
  }, [refresh, refreshReminders])

  /** Apply a partial settings change and persist it to SQLite. */
  const save = useCallback(async (patch) => {
    const previous = settings
    // Optimistic update so the UI feels instant.
    const optimistic = { ...(settings || {}), ...patch }
    setSettings(optimistic)
    if ('theme' in patch) applyTheme(patch.theme)

    try {
      const saved = await updateSettings(patch)
      setSettings(saved)
      return saved
    } catch (err) {
      setSettings(previous) // roll back on failure
      if ('theme' in patch && previous?.theme) applyTheme(previous.theme)
      throw err
    }
  }, [settings])

  const toggleTheme = useCallback(
    () => save({ theme: settings?.theme === 'dark' ? 'light' : 'dark' }),
    [save, settings]
  )

  const value = useMemo(
    () => ({
      settings,
      loading,
      error,
      currency: settings?.default_currency || 'INR',
      theme: settings?.theme || 'light',
      reminderCount,
      refresh,
      refreshReminders,
      save,
      toggleTheme,
    }),
    [settings, loading, error, reminderCount, refresh, refreshReminders, save, toggleTheme]
  )

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used inside a <SettingsProvider>.')
  }
  return context
}

export default SettingsContext