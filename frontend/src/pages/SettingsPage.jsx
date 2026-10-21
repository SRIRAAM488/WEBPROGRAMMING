/** SettingsPage - application preferences and project information. */

import { useEffect, useState } from 'react'
import {
  Bell,
  CheckCircle2,
  Database,
  Droplets,
  Info,
  Moon,
  Save,
  Settings as SettingsIcon,
  Sun,
  Wallet,
} from 'lucide-react'

import FormField, { FormErrorBanner, selectProps } from '../components/common/FormField'
import { fetchHealth, fetchSettingsMeta } from '../api/settings'
import { fetchHydrationSettings, updateHydrationSettings } from '../api/hydration'
import { getErrorMessage } from '../api/client'
import { useSettings } from '../context/SettingsContext'
import { useToast } from '../context/ToastContext'

export default function SettingsPage() {
  const { settings, save, loading: settingsLoading } = useSettings()
  const toast = useToast()

  const [draft, setDraft] = useState({})
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [meta, setMeta] = useState(null)
  const [health, setHealth] = useState(null)

  const [hydration, setHydration] = useState({ daily_goal_ml: '', default_serving_ml: '' })
  const [hydrationError, setHydrationError] = useState('')
  const [savingHydration, setSavingHydration] = useState(false)

  // Copy the saved settings into the form so the user can edit them.
  useEffect(() => {
    if (settings) {
      setDraft({
        default_currency: settings.default_currency,
        theme: settings.theme,
        bill_reminder_days_before: String(settings.bill_reminder_days_before),
        document_reminder_days_before: String(settings.document_reminder_days_before),
        hydration_reminder_percent: String(settings.hydration_reminder_percent),
        dose_grace_minutes: String(settings.dose_grace_minutes),
        show_medical_disclaimer: settings.show_medical_disclaimer,
      })
    }
  }, [settings])

  useEffect(() => {
    fetchSettingsMeta().then(setMeta).catch(() => setMeta(null))
    fetchHealth().then(setHealth).catch(() => setHealth(null))
    fetchHydrationSettings()
      .then((data) =>
        setHydration({
          daily_goal_ml: String(data.daily_goal_ml),
          default_serving_ml: String(data.default_serving_ml),
        })
      )
      .catch(() => {})
  }, [])

  function update(field, value) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  async function handleSave(event) {
    event.preventDefault()
    setFormError('')

    const patch = {
      default_currency: draft.default_currency,
      theme: draft.theme,
      bill_reminder_days_before: Number(draft.bill_reminder_days_before),
      document_reminder_days_before: Number(draft.document_reminder_days_before),
      hydration_reminder_percent: Number(draft.hydration_reminder_percent),
      dose_grace_minutes: Number(draft.dose_grace_minutes),
      show_medical_disclaimer: draft.show_medical_disclaimer,
    }

    // Local validation mirrors the backend, for instant feedback.
    if (patch.bill_reminder_days_before < 0 || patch.bill_reminder_days_before > 90) {
      setFormError('The bill reminder window must be between 0 and 90 days.')
      return
    }
    if (patch.document_reminder_days_before < 0 || patch.document_reminder_days_before > 365) {
      setFormError('The document reminder window must be between 0 and 365 days.')
      return
    }
    if (patch.hydration_reminder_percent < 10 || patch.hydration_reminder_percent > 100) {
      setFormError('The hydration nudge threshold must be between 10 and 100 percent.')
      return
    }
    if (patch.dose_grace_minutes < 0 || patch.dose_grace_minutes > 1440) {
      setFormError('The dose grace period must be between 0 and 1440 minutes.')
      return
    }

    setSaving(true)
    try {
      await save(patch)
      toast.success('Settings saved.')
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not save your settings.'))
    } finally {
      setSaving(false)
    }
  }

  async function saveHydration(event) {
    event.preventDefault()
    const goal = Number(hydration.daily_goal_ml)
    const serving = Number(hydration.default_serving_ml)

    if (!Number.isInteger(goal) || goal <= 0 || goal > 10000) {
      setHydrationError('The daily goal must be a whole number between 1 and 10000 ml.')
      return
    }
    if (!Number.isInteger(serving) || serving <= 0 || serving > 5000) {
      setHydrationError('The serving size must be a whole number between 1 and 5000 ml.')
      return
    }

    setHydrationError('')
    setSavingHydration(true)
    try {
      await updateHydrationSettings({ daily_goal_ml: goal, default_serving_ml: serving })
      toast.success('Hydration settings saved.')
    } catch (err) {
      setHydrationError(getErrorMessage(err))
    } finally {
      setSavingHydration(false)
    }
  }

  if (settingsLoading || !settings) {
    return (
      <>
        <div className="page-head">
          <div className="page-head__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
            <SettingsIcon size={23} />
          </div>
          <div className="page-head__text">
            <h1 className="page-head__title">Settings</h1>
            <p className="page-head__desc">Loading your preferences…</p>
          </div>
        </div>
        <div className="skeleton" style={{ height: 320 }} />
      </>
    )
  }

  const notes = settings.notes || {}

  return (
    <>
      <div className="page-head">
        <div className="page-head__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
          <SettingsIcon size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">Settings</h1>
          <p className="page-head__desc">
            Preferences are saved in SQLite, so they follow you between sessions.
          </p>
        </div>
      </div>

      <div className="alert alert--warning">
        <Info size={16} aria-hidden="true" />
        <span>
          <strong>DailyFlow is a single-user local app.</strong> There is no login and no data
          separation between users — every record lives in one SQLite file on this machine.
          Do not expose the backend to a public network.
        </span>
      </div>

      <div className="grid grid--dashboard">
        <div className="stack stack--lg">
          {/* Appearance & currency */}
          <section className="card">
            <div className="card__header">
              <div className="card__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
                <Sun size={18} />
              </div>
              <div>
                <h2 className="card__title">Appearance and currency</h2>
                <p className="card__subtitle">How DailyFlow looks and what money symbol it uses</p>
              </div>
            </div>

            <form onSubmit={handleSave} className="card__body stack">
              <FormErrorBanner message={formError} />

              <div className="form-grid">
                <FormField label="Default currency" htmlFor="default_currency" hint={notes.default_currency}>
                  <select
                    {...selectProps('default_currency')}
                    id="default_currency"
                    value={draft.default_currency || 'INR'}
                    onChange={(event) => update('default_currency', event.target.value)}
                  >
                    {(meta?.currencies || ['INR', 'USD', 'EUR', 'GBP']).map((code) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Theme" htmlFor="theme" hint={notes.theme}>
                  <select
                    {...selectProps('theme')}
                    id="theme"
                    value={draft.theme || 'light'}
                    onChange={(event) => update('theme', event.target.value)}
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </FormField>
              </div>

              <div className="row" style={{ gap: 'var(--sp-2)' }}>
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => update('theme', draft.theme === 'dark' ? 'light' : 'dark')}
                >
                  {draft.theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
                  Preview {draft.theme === 'dark' ? 'light' : 'dark'}
                </button>
                <span className="text-xs text-muted">Saves when you press Save.</span>
              </div>
            </form>
          </section>

          {/* Reminders */}
          <section className="card">
            <div className="card__header">
              <div className="card__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
                <Bell size={18} />
              </div>
              <div>
                <h2 className="card__title">Reminder lead times</h2>
                <p className="card__subtitle">
                  How early DailyFlow warns you. These do not change any existing record.
                </p>
              </div>
            </div>

            <div className="card__body stack">
              <div className="form-grid">
                <FormField
                  label="Bills (days before due)"
                  htmlFor="bill_reminder_days_before"
                  hint={notes.bill_reminder_days_before}
                >
                  <input
                    id="bill_reminder_days_before"
                    type="number"
                    min="0"
                    max="90"
                    className="input"
                    value={draft.bill_reminder_days_before ?? ''}
                    onChange={(event) => update('bill_reminder_days_before', event.target.value)}
                  />
                </FormField>

                <FormField
                  label="Documents (days before expiry)"
                  htmlFor="document_reminder_days_before"
                  hint={notes.document_reminder_days_before}
                >
                  <input
                    id="document_reminder_days_before"
                    type="number"
                    min="0"
                    max="365"
                    className="input"
                    value={draft.document_reminder_days_before ?? ''}
                    onChange={(event) => update('document_reminder_days_before', event.target.value)}
                  />
                </FormField>

                <FormField
                  label="Hydration nudge (percent of goal)"
                  htmlFor="hydration_reminder_percent"
                  hint={notes.hydration_reminder_percent}
                >
                  <input
                    id="hydration_reminder_percent"
                    type="number"
                    min="10"
                    max="100"
                    className="input"
                    value={draft.hydration_reminder_percent ?? ''}
                    onChange={(event) => update('hydration_reminder_percent', event.target.value)}
                  />
                </FormField>

                <FormField
                  label="Dose grace period (minutes)"
                  htmlFor="dose_grace_minutes"
                  hint={notes.dose_grace_minutes}
                >
                  <input
                    id="dose_grace_minutes"
                    type="number"
                    min="0"
                    max="1440"
                    className="input"
                    value={draft.dose_grace_minutes ?? ''}
                    onChange={(event) => update('dose_grace_minutes', event.target.value)}
                  />
                </FormField>

                <div className="form-field form-field--full">
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={Boolean(draft.show_medical_disclaimer)}
                      onChange={(event) => update('show_medical_disclaimer', event.target.checked)}
                    />
                    <span>
                      <strong>Show the DoseNote medical disclaimer</strong>
                      <div className="text-xs text-muted">{notes.show_medical_disclaimer}</div>
                    </span>
                  </label>
                </div>
              </div>

              <div className="row row--between">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setDraft({ ...draft })}
                >
                  Reset to saved values
                </button>
                <button type="submit" className="btn btn--primary" disabled={saving} onClick={handleSave}>
                  <Save size={15} />
                  {saving ? 'Saving…' : 'Save settings'}
                </button>
              </div>
            </div>
          </section>
        </div>

        {/* Right column */}
        <div className="stack stack--lg">
          {/* Hydration */}
          <section className="card">
            <div className="card__header">
              <div className="card__icon" style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}>
                <Droplets size={18} />
              </div>
              <div>
                <h2 className="card__title">Hydration goal</h2>
                <p className="card__subtitle">A personal preference, not medical advice</p>
              </div>
            </div>

            <form onSubmit={saveHydration} className="card__body stack">
              <FormErrorBanner message={hydrationError} />

              <FormField label="Daily goal (ml)" htmlFor="goal_ml" required>
                <div className="input-group">
                  <input
                    id="goal_ml"
                    type="number"
                    min="1"
                    max="10000"
                    className="input"
                    value={hydration.daily_goal_ml}
                    onChange={(event) =>
                      setHydration((current) => ({ ...current, daily_goal_ml: event.target.value }))
                    }
                  />
                  <span className="input-group__suffix">ml</span>
                </div>
              </FormField>

              <FormField
                label="Default serving (ml)"
                htmlFor="serving_ml"
                hint="Pre-fills the custom amount field on AquaHabit."
                required
              >
                <div className="input-group">
                  <input
                    id="serving_ml"
                    type="number"
                    min="1"
                    max="5000"
                    className="input"
                    value={hydration.default_serving_ml}
                    onChange={(event) =>
                      setHydration((current) => ({
                        ...current,
                        default_serving_ml: event.target.value,
                      }))
                    }
                  />
                  <span className="input-group__suffix">ml</span>
                </div>
              </FormField>

              <div className="alert alert--neutral">
                <Info size={15} aria-hidden="true" />
                <span className="text-xs">
                  Changing the goal affects how progress is calculated from now on. Your logged
                  water entries are never changed or deleted.
                </span>
              </div>

              <button type="submit" className="btn btn--primary btn--block" disabled={savingHydration}>
                <Droplets size={15} />
                {savingHydration ? 'Saving…' : 'Save hydration settings'}
              </button>
            </form>
          </section>

          {/* Quick-add sizes */}
          <section className="card">
            <div className="card__header">
              <div className="card__icon" style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}>
                <Wallet size={18} />
              </div>
              <div>
                <h2 className="card__title">Quick-add sizes</h2>
                <p className="card__subtitle">One-tap buttons on the AquaHabit page</p>
              </div>
            </div>
            <div className="card__body">
              <div className="quick-add">
                {(meta?.hydration_quick_add_ml || [150, 250, 350, 500]).map((amount) => (
                  <span key={amount} className="badge badge--aquahabit badge--lg">
                    {amount} ml
                  </span>
                ))}
              </div>
            </div>
          </section>

          {/* System info */}
          <section className="card">
            <div className="card__header">
              <div className="card__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
                <Database size={18} />
              </div>
              <div>
                <h2 className="card__title">About this install</h2>
                <p className="card__subtitle">Local project information</p>
              </div>
            </div>
            <div className="card__body stack stack--sm">
              <InfoRow
                label="API status"
                value={
                  health ? (
                    <span className="badge badge--success">
                      <span className="badge__dot" />
                      {health.status}
                    </span>
                  ) : (
                    'Checking…'
                  )
                }
              />
              <InfoRow label="Database" value={health?.database || 'SQLite'} />
              <InfoRow label="Backend version" value={health?.version || '—'} />
              <InfoRow label="Modules" value={health?.modules?.join(', ') || '—'} />
              <InfoRow label="Currency" value={settings.default_currency} />
              <InfoRow
                label="Theme"
                value={
                  <span className="badge badge--primary">{settings.theme}</span>
                }
              />

              <div className="alert alert--neutral" style={{ marginTop: 'var(--sp-2)' }}>
                <CheckCircle2 size={15} aria-hidden="true" />
                <span className="text-xs">
                  Everything is stored in a single <code>dailyflow.db</code> SQLite file in the
                  backend folder. Delete that file and re-run the seed script to reset the demo.
                </span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="row row--between" style={{ gap: 'var(--sp-4)' }}>
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm font-semibold" style={{ textAlign: 'right' }}>
        {value}
      </span>
    </div>
  )
}