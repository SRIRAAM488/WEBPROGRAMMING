/** HydrationPage - the AquaHabit module. */

import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Droplets,
  Info,
  Pencil,
  Plus,
  Settings2,
  Target,
  Trash2,
  TrendingUp,
} from 'lucide-react'

import StatusBadge from '../components/common/StatusBadge'
import EmptyState, { ErrorState } from '../components/common/EmptyState'
import ConfirmDialog from '../components/common/ConfirmDialog'
import Modal from '../components/common/Modal'
import FormField, { FormErrorBanner, fieldProps } from '../components/common/FormField'
import { ProgressRing, StatTile } from '../components/common/Progress'
import WeeklyHydrationChart from '../components/dashboard/WeeklyHydrationChart'

import {
  HYDRATION_NOTE,
  QUICK_ADD_ML,
  createIntake,
  deleteIntake,
  fetchMonthlyHydration,
  fetchHydrationSettings,
  fetchTodayHydration,
  fetchWeeklyHydration,
  updateHydrationSettings,
  updateIntake,
} from '../api/hydration'
import { getErrorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { formatDate, formatMl, formatTime } from '../utils/format'

export default function HydrationPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const [today, setToday] = useState(null)
  const [weekly, setWeekly] = useState(null)
  const [monthly, setMonthly] = useState(null)
  const [settings, setSettings] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [savingIntake, setSavingIntake] = useState(false)

  const [customOpen, setCustomOpen] = useState(false)
  const [customAmount, setCustomAmount] = useState('')
  const [customError, setCustomError] = useState('')

  const [editingEntry, setEditingEntry] = useState(null)
  const [editAmount, setEditAmount] = useState('')
  const [editError, setEditError] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [goalDraft, setGoalDraft] = useState({ daily_goal_ml: '', default_serving_ml: '' })
  const [settingsError, setSettingsError] = useState('')
  const [savingSettings, setSavingSettings] = useState(false)

  // A dashboard quick action can arrive here with ?action=add
  useEffect(() => {
    if (searchParams.get('action') === 'add') {
      setCustomOpen(true)
      searchParams.delete('action')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const load = useCallback(async () => {
    try {
      setError(null)
      const [todayData, weeklyData, monthlyData, settingsData] = await Promise.all([
        fetchTodayHydration(),
        fetchWeeklyHydration(7),
        fetchMonthlyHydration().catch(() => null),
        fetchHydrationSettings(),
      ])
      setToday(todayData)
      setWeekly(weeklyData)
      setMonthly(monthlyData)
      setSettings(settingsData)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load your hydration data.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // ---- actions -------------------------------------------------------------

  async function quickAdd(amount) {
    setSavingIntake(true)
    try {
      await createIntake({ amount_ml: amount })
      toast.success(`Logged ${amount} ml. ${formatMl(today?.total_ml + amount)} so far today.`)
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not log that amount.'))
    } finally {
      setSavingIntake(false)
    }
  }

  async function submitCustom(event) {
    event.preventDefault()
    const amount = Number(customAmount)
    if (!Number.isInteger(amount) || amount <= 0) {
      setCustomError('Enter a whole number of millilitres greater than 0.')
      return
    }
    if (amount > 5000) {
      setCustomError('That is more than 5000 ml. Please enter a smaller amount.')
      return
    }
    setCustomError('')
    await quickAdd(amount)
    setCustomAmount('')
    setCustomOpen(false)
  }

  async function submitEdit(event) {
    event.preventDefault()
    const amount = Number(editAmount)
    if (!Number.isInteger(amount) || amount <= 0 || amount > 5000) {
      setEditError('Enter a whole number between 1 and 5000.')
      return
    }
    setEditError('')
    setSavingEdit(true)
    try {
      await updateIntake(editingEntry.id, { amount_ml: amount })
      toast.success(`Updated to ${amount} ml.`)
      setEditingEntry(null)
      await load()
    } catch (err) {
      setEditError(getErrorMessage(err))
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteIntake(deleteTarget.id)
      toast.success(`Deleted the ${deleteTarget.amount_ml} ml entry.`)
      setDeleteTarget(null)
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  async function submitSettings(event) {
    event.preventDefault()
    const goal = Number(goalDraft.daily_goal_ml)
    const serving = Number(goalDraft.default_serving_ml)

    if (!Number.isInteger(goal) || goal <= 0 || goal > 10000) {
      setSettingsError('The daily goal must be a whole number between 1 and 10000 ml.')
      return
    }
    if (!Number.isInteger(serving) || serving <= 0 || serving > 5000) {
      setSettingsError('The serving size must be a whole number between 1 and 5000 ml.')
      return
    }

    setSettingsError('')
    setSavingSettings(true)
    try {
      await updateHydrationSettings({ daily_goal_ml: goal, default_serving_ml: serving })
      toast.success('Hydration settings saved.')
      setSettingsOpen(false)
      await load()
    } catch (err) {
      setSettingsError(getErrorMessage(err))
    } finally {
      setSavingSettings(false)
    }
  }

  // ---- render --------------------------------------------------------------

  return (
    <>
      <div className="page-head">
        <div className="page-head__icon" style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}>
          <Droplets size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">AquaHabit</h1>
          <p className="page-head__desc">
            Log your water intake and keep an eye on your daily goal.
          </p>
        </div>
        <div className="page-head__actions">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => {
              setGoalDraft({
                daily_goal_ml: String(settings?.daily_goal_ml ?? 2000),
                default_serving_ml: String(settings?.default_serving_ml ?? 250),
              })
              setSettingsError('')
              setSettingsOpen(true)
            }}
          >
            <Settings2 size={16} />
            Goal settings
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid--2">
          <div className="skeleton" style={{ height: 260 }} />
          <div className="skeleton" style={{ height: 260 }} />
        </div>
      ) : error ? (
        <div className="card">
          <ErrorState message={error} onRetry={load} />
        </div>
      ) : (
        <>
          {/* Progress + quick add */}
          <div className="grid grid--2">
            <section className="card">
              <div className="card__header">
                <div
                  className="card__icon"
                  style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
                >
                  <Target size={18} />
                </div>
                <div>
                  <h2 className="card__title">Today's progress</h2>
                  <p className="card__subtitle">{formatDate(today.date)}</p>
                </div>
              </div>

              <div className="card__body">
                <div
                  className="row"
                  style={{ gap: 'var(--sp-5)', alignItems: 'center', flexWrap: 'wrap' }}
                >
                  <ProgressRing
                    value={today.total_ml}
                    max={today.goal_ml || 1}
                    accent="aquahabit"
                    size={148}
                    label="of your goal"
                    valueText={`${today.percent_complete}%`}
                  />

                  <div className="stack stack--sm" style={{ flex: 1, minWidth: 150 }}>
                    <div>
                      <div className="text-3xl font-bold text-num" style={{ letterSpacing: '-0.03em' }}>
                        {formatMl(today.total_ml)}
                      </div>
                      <div className="text-sm text-muted">of {formatMl(today.goal_ml)} goal</div>
                    </div>

                    {today.goal_reached ? (
                      <div className="alert alert--success">
                        <TrendingUp size={15} aria-hidden="true" />
                        <span className="text-xs font-semibold">
                          Goal reached! {formatMl(today.total_ml)} logged today.
                        </span>
                      </div>
                    ) : (
                      <div className="text-sm text-muted">
                        <strong className="text-num" style={{ color: 'var(--text)' }}>
                          {formatMl(today.remaining_ml)}
                        </strong>{' '}
                        to go
                      </div>
                    )}

                    <div className="text-xs text-muted">
                      {today.entries.length} {today.entries.length === 1 ? 'entry' : 'entries'} today
                      {weekly ? ` · 7-day average ${formatMl(weekly.average_ml)}` : ''}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="card__header">
                <div
                  className="card__icon"
                  style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
                >
                  <Plus size={18} />
                </div>
                <div>
                  <h2 className="card__title">Log a glass</h2>
                  <p className="card__subtitle">One tap, no typing</p>
                </div>
              </div>

              <div className="card__body stack">
                <div className="quick-add">
                  {QUICK_ADD_ML.map((amount) => (
                    <button
                      key={amount}
                      type="button"
                      className="quick-add__btn"
                      onClick={() => quickAdd(amount)}
                      disabled={savingIntake}
                    >
                      +{amount}
                      <small>ml</small>
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  className="btn btn--secondary btn--block"
                  onClick={() => {
                    setCustomAmount(String(settings?.default_serving_ml ?? 250))
                    setCustomError('')
                    setCustomOpen(true)
                  }}
                >
                  <Droplets size={15} />
                  Log a custom amount
                </button>

                <div className="alert alert--neutral">
                  <Info size={15} aria-hidden="true" />
                  <span className="text-xs">{HYDRATION_NOTE}</span>
                </div>
              </div>
            </section>
          </div>

          {/* Stats */}
          <div className="grid grid--summary">
            <StatTile
              label="Today"
              value={formatMl(today.total_ml)}
              tone="aquahabit"
              icon={<Droplets size={12} />}
            />
            <StatTile
              label="Daily goal"
              value={formatMl(today.goal_ml)}
              icon={<Target size={12} />}
            />
            <StatTile
              label="7-day average"
              value={formatMl(weekly?.average_ml ?? 0)}
              icon={<TrendingUp size={12} />}
            />
            <StatTile
              label="Days goal reached"
              value={`${weekly?.days_goal_reached ?? 0} of 7`}
              tone="success"
              icon={<TrendingUp size={12} />}
            />
          </div>

          {/* Weekly chart */}
          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
              >
                <TrendingUp size={18} />
              </div>
              <div>
                <h2 className="card__title">Last 7 days</h2>
                <p className="card__subtitle">
                  {weekly ? `${formatMl(weekly.total_ml)} total · best day ${formatMl(weekly.best_day?.total_ml ?? 0)}` : 'Loading…'}
                </p>
              </div>
            </div>
            <div className="card__body">
              <WeeklyHydrationChart data={weekly?.daily || []} height={250} />
            </div>
          </section>

          {/* Today's entries */}
          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
              >
                <Droplets size={18} />
              </div>
              <div>
                <h2 className="card__title">Today's entries</h2>
                <p className="card__subtitle">Correct or remove anything you logged by mistake</p>
              </div>
            </div>

            <div className="card__body card__body--tight">
              {today.entries.length === 0 ? (
                <EmptyState
                  compact
                  icon={<Droplets size={24} />}
                  title="Nothing logged today"
                  description="Tap one of the quick-add buttons to record your first glass."
                />
              ) : (
                <div className="item-list">
                  {today.entries.map((entry) => (
                    <div key={entry.id} className="item-row">
                      <span
                        className="item-row__icon"
                        style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
                      >
                        <Droplets size={16} />
                      </span>

                      <span className="item-row__body">
                        <span className="item-row__title">{formatMl(entry.amount_ml)}</span>
                        <span className="item-row__meta text-xs">
                          <span className="text-num">{formatTime(entry.consumed_at)}</span>
                          {entry.notes ? <span className="dot-sep">{entry.notes}</span> : null}
                        </span>
                      </span>

                      <span className="item-row__actions">
                        <button
                          type="button"
                          className="icon-action icon-action--primary"
                          onClick={() => {
                            setEditingEntry(entry)
                            setEditAmount(String(entry.amount_ml))
                            setEditError('')
                          }}
                          title="Correct this entry"
                          aria-label={`Edit the ${entry.amount_ml} ml entry`}
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          type="button"
                          className="icon-action icon-action--danger"
                          onClick={() => setDeleteTarget(entry)}
                          title="Delete this entry"
                          aria-label={`Delete the ${entry.amount_ml} ml entry`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Month overview */}
          {monthly ? (
            <section className="card">
              <div className="card__header">
                <div
                  className="card__icon"
                  style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
                >
                  <Target size={18} />
                </div>
                <div>
                  <h2 className="card__title">{monthly.month} {monthly.year}</h2>
                  <p className="card__subtitle">Month to date</p>
                </div>
              </div>
              <div className="card__body">
                <div className="grid grid--3" style={{ gap: 'var(--sp-3)' }}>
                  <StatTile label="Total" value={formatMl(monthly.total_ml)} tone="aquahabit" />
                  <StatTile label="Daily average" value={formatMl(monthly.average_ml)} />
                  <StatTile
                    label="Days goal reached"
                    value={monthly.days_goal_reached}
                    tone="success"
                  />
                </div>
              </div>
            </section>
          ) : null}
        </>
      )}

      {/* ---------- Custom amount modal ---------- */}
      <Modal
        open={customOpen}
        onClose={() => setCustomOpen(false)}
        title="Log water"
        description="Millilitres is the unit DailyFlow stores."
        icon={<Droplets size={20} />}
        accent="aquahabit"
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setCustomOpen(false)}
              disabled={savingIntake}
            >
              Cancel
            </button>
            <button type="submit" form="custom-water-form" className="btn btn--primary" disabled={savingIntake}>
              {savingIntake ? 'Saving…' : 'Log water'}
            </button>
          </>
        }
      >
        <form id="custom-water-form" onSubmit={submitCustom} className="stack">
          <div className="quick-add">
            {QUICK_ADD_ML.map((amount) => (
              <button
                key={amount}
                type="button"
                className="quick-add__btn"
                onClick={() => setCustomAmount(String(amount))}
                disabled={savingIntake}
              >
                {amount}
                <small>ml</small>
              </button>
            ))}
          </div>

          <FormField label="Amount" htmlFor="custom_ml" error={customError} required>
            <div className="input-group">
              <input
                id="custom_ml"
                type="number"
                min="1"
                max="5000"
                step="1"
                value={customAmount}
                onChange={(event) => {
                  setCustomAmount(event.target.value)
                  setCustomError('')
                }}
                className={customError ? 'input input--error' : 'input'}
                aria-invalid={customError ? 'true' : undefined}
              />
              <span className="input-group__suffix">ml</span>
            </div>
          </FormField>
        </form>
      </Modal>

      {/* ---------- Edit entry modal ---------- */}
      <Modal
        open={Boolean(editingEntry)}
        onClose={() => setEditingEntry(null)}
        title="Correct this entry"
        description="Change the amount you logged."
        icon={<Pencil size={20} />}
        accent="aquahabit"
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setEditingEntry(null)}
              disabled={savingEdit}
            >
              Cancel
            </button>
            <button type="submit" form="edit-water-form" className="btn btn--primary" disabled={savingEdit}>
              {savingEdit ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <form id="edit-water-form" onSubmit={submitEdit} className="stack">
          <FormErrorBanner message={editError} />
          <FormField label="Amount" htmlFor="edit_ml" error={editError} required>
            <div className="input-group">
              <input
                id="edit_ml"
                type="number"
                min="1"
                max="5000"
                step="1"
                value={editAmount}
                onChange={(event) => {
                  setEditAmount(event.target.value)
                  setEditError('')
                }}
                className={editError ? 'input input--error' : 'input'}
              />
              <span className="input-group__suffix">ml</span>
            </div>
          </FormField>
          {editingEntry ? (
            <p className="text-xs text-muted">
              Logged at {formatTime(editingEntry.consumed_at)} on {formatDate(editingEntry.entry_date)}.
            </p>
          ) : null}
        </form>
      </Modal>

      {/* ---------- Settings modal ---------- */}
      <Modal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Hydration settings"
        description="These affect progress from now on. Existing entries are never changed."
        icon={<Settings2 size={20} />}
        accent="aquahabit"
        size="sm"
        footer={
          <>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setSettingsOpen(false)}
              disabled={savingSettings}
            >
              Cancel
            </button>
            <button type="submit" form="hydration-settings-form" className="btn btn--primary" disabled={savingSettings}>
              {savingSettings ? 'Saving…' : 'Save settings'}
            </button>
          </>
        }
      >
        <form id="hydration-settings-form" onSubmit={submitSettings} className="stack">
          <FormErrorBanner message={settingsError} />

          <FormField
            label="Daily goal (ml)"
            htmlFor="goal_ml"
            hint="Your personal target. Not medical advice."
            required
          >
            <div className="input-group">
              <input
                {...fieldProps('goal_ml')}
                id="goal_ml"
                type="number"
                min="1"
                max="10000"
                step="1"
                value={goalDraft.daily_goal_ml}
                onChange={(event) => setGoalDraft((d) => ({ ...d, daily_goal_ml: event.target.value }))}
              />
              <span className="input-group__suffix">ml</span>
            </div>
          </FormField>

          <FormField
            label="Default serving size (ml)"
            htmlFor="serving_ml"
            hint="Pre-filled in the custom amount field."
            required
          >
            <div className="input-group">
              <input
                {...fieldProps('serving_ml')}
                id="serving_ml"
                type="number"
                min="1"
                max="5000"
                step="1"
                value={goalDraft.default_serving_ml}
                onChange={(event) =>
                  setGoalDraft((d) => ({ ...d, default_serving_ml: event.target.value }))
                }
              />
              <span className="input-group__suffix">ml</span>
            </div>
          </FormField>

          <div className="alert alert--info">
            <Info size={15} aria-hidden="true" />
            <span className="text-xs">{HYDRATION_NOTE}</span>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        busy={deleting}
        title="Delete this entry?"
        description={`The ${deleteTarget?.amount_ml} ml entry will be removed from today's total. Other days are not affected.`}
        confirmLabel="Delete entry"
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </>
  )
}