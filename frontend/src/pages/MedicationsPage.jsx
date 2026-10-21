/**
 * MedicationsPage - the DoseNote module.
 *
 * DoseNote is a personal tracking and reminder tool. It records the schedule
 * you entered; it does not give medical advice and never tells you to change a
 * prescribed medication or dose.
 */

import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  CalendarRange,
  Check,
  History,
  Info,
  Pencil,
  Pill,
  Plus,
  Power,
  RotateCcw,
  SkipForward,
  Trash2,
  TrendingUp,
} from 'lucide-react'

import Toolbar from '../components/common/Toolbar'
import StatusBadge from '../components/common/StatusBadge'
import EmptyState, { ErrorState } from '../components/common/EmptyState'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { ProgressBar, StatTile } from '../components/common/Progress'
import MedicationFormModal from '../components/medications/MedicationFormModal'
import AdherenceChart from '../components/dashboard/AdherenceChart'
import TodayMedicationList from '../components/dashboard/TodayMedicationList'

import {
  MEDICAL_DISCLAIMER,
  createSchedule,
  deleteSchedule,
  fetchAdherence,
  fetchDoseHistory,
  fetchSchedules,
  fetchTodayDoses,
  updateSchedule,
} from '../api/medications'
import { getErrorMessage } from '../api/client'
import useDebounced from '../hooks/useDebounced'
import { useSettings } from '../context/SettingsContext'
import { useToast } from '../context/ToastContext'
import { formatDate, formatTime } from '../utils/format'

export default function MedicationsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { settings, refreshReminders } = useSettings()
  const showDisclaimer = settings?.show_medical_disclaimer !== false

  const [search, setSearch] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)

  const [schedules, setSchedules] = useState([])
  const [today, setToday] = useState(null)
  const [adherence, setAdherence] = useState(null)
  const [history, setHistory] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const debouncedSearch = useDebounced(search, 320)
  const focusDoseId = searchParams.get('dose')

  useEffect(() => {
    if (searchParams.get('action') === 'add') {
      setEditing(null)
      setFormOpen(true)
      searchParams.delete('action')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const load = useCallback(async () => {
    try {
      setError(null)
      const [scheduleList, todayDoses, weeklyAdherence, doseHistory] = await Promise.all([
        fetchSchedules({ search: debouncedSearch || undefined, active_only: activeOnly }),
        fetchTodayDoses(),
        fetchAdherence(7),
        fetchDoseHistory(),
      ])
      setSchedules(scheduleList)
      setToday(todayDoses)
      setAdherence(weeklyAdherence)
      setHistory(doseHistory)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load your medication schedules.'))
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, activeOnly])

  useEffect(() => {
    load()
  }, [load])

  // ---- actions -------------------------------------------------------------

  async function handleCreate(payload) {
    const created = await createSchedule(payload)
    toast.success(`Added "${created.medication_name}".`)
    setFormOpen(false)
    await load()
    refreshReminders()
  }

  async function handleUpdate(payload) {
    const updated = await updateSchedule(editing.id, payload)
    toast.success(`Updated "${updated.medication_name}".`)
    setFormOpen(false)
    setEditing(null)
    await load()
    refreshReminders()
  }

  async function toggleActive(schedule) {
    try {
      const updated = await updateSchedule(schedule.id, { active: !schedule.active })
      toast.success(
        updated.active
          ? `"${updated.medication_name}" is active again.`
          : `"${updated.medication_name}" deactivated. Past dose logs are kept.`
      )
      await load()
      refreshReminders()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteSchedule(deleteTarget.id)
      toast.success(`Deleted "${deleteTarget.medication_name}" and its dose logs.`)
      setDeleteTarget(null)
      await load()
      refreshReminders()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  // ---- render --------------------------------------------------------------

  return (
    <>
      <div className="page-head">
        <div className="page-head__icon" style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}>
          <Pill size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">DoseNote</h1>
          <p className="page-head__desc">
            Track the medication schedule you follow and log each dose.
          </p>
        </div>
        <div className="page-head__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus size={16} />
            Add schedule
          </button>
        </div>
      </div>

      {showDisclaimer ? (
        <div className="alert alert--warning">
          <Info size={16} aria-hidden="true" />
          <span>{MEDICAL_DISCLAIMER}</span>
        </div>
      ) : null}

      {/* Today's doses */}
      <section className="card">
        <div className="card__header">
          <div
            className="card__icon"
            style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}
          >
            <CalendarRange size={18} />
          </div>
          <div>
            <h2 className="card__title">Today's doses</h2>
            <p className="card__subtitle">
              {today ? formatDate(today.date) : 'Loading…'} ·{' '}
              {today ? `${today.taken} of ${today.total_doses} taken` : ''}
            </p>
          </div>
        </div>
        <div className="card__body">
          <TodayMedicationList
            data={today}
            loading={loading}
            showDisclaimer={false}
            onChanged={load}
          />
        </div>
      </section>

      {/* Stats */}
      {today ? (
        <div className="grid grid--summary">
          <StatTile
            label="Active schedules"
            value={schedules.filter((schedule) => schedule.active).length}
            icon={<Pill size={12} />}
          />
          <StatTile label="Doses today" value={today.total_doses} />
          <StatTile
            label="Taken today"
            value={today.taken}
            tone="success"
            icon={<Check size={12} />}
          />
          <StatTile
            label="Completion"
            value={`${today.completion_percent}%`}
            tone={today.completion_percent >= 80 ? 'success' : 'dosenote'}
            icon={<TrendingUp size={12} />}
          />
        </div>
      ) : null}

      {/* Weekly adherence */}
      <div className="grid grid--dashboard">
        <section className="card">
          <div className="card__header">
            <div className="card__icon" style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}>
              <TrendingUp size={18} />
            </div>
            <div>
              <h2 className="card__title">Weekly adherence</h2>
              <p className="card__subtitle">
                {adherence
                  ? `${adherence.overall_adherence_percent}% of resolved doses were taken`
                  : 'Loading…'}
              </p>
            </div>
          </div>
          <div className="card__body">
            <AdherenceChart data={adherence?.daily || []} loading={loading} height={220} />
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            <div className="card__icon" style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}>
              <History size={18} />
            </div>
            <div>
              <h2 className="card__title">Adherence summary</h2>
              <p className="card__subtitle">Last 7 days, from stored dose logs</p>
            </div>
          </div>
          <div className="card__body">
            <div className="stack stack--sm">
              <ProgressBar
                value={adherence?.overall_adherence_percent || 0}
                accent="dosenote"
                label="Overall adherence"
              />
              <div className="grid grid--2" style={{ gap: 'var(--sp-2)' }}>
                <StatTile label="Scheduled" value={adherence?.total_scheduled ?? 0} />
                <StatTile label="Taken" value={adherence?.total_taken ?? 0} tone="success" />
                <StatTile label="Skipped" value={adherence?.daily?.reduce((sum, d) => sum + d.skipped, 0) ?? 0} />
                <StatTile
                  label="Missed"
                  value={adherence?.daily?.reduce((sum, d) => sum + d.missed, 0) ?? 0}
                  tone="danger"
                />
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Schedules */}
      <Toolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search by medication name…"
      >
        <label className="checkbox" style={{ whiteSpace: 'nowrap' }}>
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(event) => setActiveOnly(event.target.checked)}
          />
          <span>Active only</span>
        </label>
      </Toolbar>

      <section className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">
              {loading ? 'Loading schedules…' : `${schedules.length} schedule${schedules.length === 1 ? '' : 's'}`}
            </h2>
            <p className="card__subtitle">Dose logs are generated daily and stored in SQLite</p>
          </div>
        </div>

        <div className="card__body card__body--tight">
          {loading ? (
            <div className="stack stack--sm" style={{ padding: 'var(--sp-3)' }} aria-hidden="true">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="skeleton" style={{ height: 62 }} />
              ))}
            </div>
          ) : error ? (
            <ErrorState message={error} onRetry={load} />
          ) : schedules.length === 0 ? (
            <EmptyState
              icon={<Pill size={26} />}
              title={search ? 'No schedules match your search' : 'No medication schedules yet'}
              description={
                search
                  ? 'Try a different medication name.'
                  : 'Add a schedule with one or more times of day. DailyFlow generates the dose logs and you tick them off.'
              }
              action={
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => {
                    setEditing(null)
                    setFormOpen(true)
                  }}
                >
                  <Plus size={14} />
                  Add a schedule
                </button>
              }
            />
          ) : (
            <div className="item-list">
              {schedules.map((schedule) => (
                <div
                  key={schedule.id}
                  className="item-row"
                  style={
                    focusDoseId && schedule.doses_today_total > 0
                      ? { boxShadow: 'inset 3px 0 0 var(--dosenote)' }
                      : undefined
                  }
                >
                  <span
                    className="item-row__icon"
                    style={{
                      background: schedule.active ? 'var(--dosenote-soft)' : 'var(--surface-sunken)',
                      color: schedule.active ? 'var(--dosenote)' : 'var(--text-faint)',
                    }}
                  >
                    <Pill size={17} />
                  </span>

                  <span className="item-row__body">
                    <span className="item-row__title">
                      {schedule.medication_name}
                      <StatusBadge
                        status={schedule.active ? 'active' : 'inactive'}
                        label={schedule.active ? 'Active' : 'Inactive'}
                      />
                    </span>
                    <span className="item-row__meta">
                      <span>
                        {schedule.dosage} {schedule.dosage_unit}
                      </span>
                      <span className="dot-sep">
                        {schedule.time_labels.length
                          ? schedule.time_labels.join(' · ')
                          : 'No times set'}
                      </span>
                      <span className="dot-sep">From {formatDate(schedule.start_date)}</span>
                      {schedule.instructions ? (
                        <span className="dot-sep text-truncate" style={{ maxWidth: 220 }}>
                          {schedule.instructions}
                        </span>
                      ) : null}
                    </span>
                  </span>

                  <span className="item-row__right hide-mobile">
                    <div className="text-xs text-muted">
                      Today: {schedule.doses_today_taken}/{schedule.doses_today_total}
                    </div>
                    {schedule.adherence_percent !== null ? (
                      <div className="text-xs font-semibold" style={{ color: 'var(--dosenote)' }}>
                        {schedule.adherence_percent}% adherence
                      </div>
                    ) : null}
                  </span>

                  <span className="item-row__actions">
                    <button
                      type="button"
                      className="icon-action"
                      onClick={() => toggleActive(schedule)}
                      title={schedule.active ? 'Deactivate (keeps history)' : 'Activate'}
                      aria-label={
                        schedule.active
                          ? `Deactivate ${schedule.medication_name}`
                          : `Activate ${schedule.medication_name}`
                      }
                    >
                      <Power size={15} />
                    </button>
                    <button
                      type="button"
                      className="icon-action icon-action--primary"
                      onClick={() => {
                        setEditing(schedule)
                        setFormOpen(true)
                      }}
                      title="Edit schedule"
                      aria-label={`Edit ${schedule.medication_name}`}
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      className="icon-action icon-action--danger"
                      onClick={() => setDeleteTarget(schedule)}
                      title="Delete schedule and its dose logs"
                      aria-label={`Delete ${schedule.medication_name}`}
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

      {/* Recent history */}
      {history && history.recent.length > 0 ? (
        <section className="card">
          <div className="card__header">
            <div className="card__icon" style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}>
              <History size={18} />
            </div>
            <div>
              <h2 className="card__title">Recent dose history</h2>
              <p className="card__subtitle">
                {formatDate(history.start_date)} to {formatDate(history.end_date)}
              </p>
            </div>
          </div>
          <div className="card__body card__body--tight">
            <div className="item-list">
              {history.recent.slice(0, 12).map((dose) => (
                <div key={dose.id} className="item-row">
                  <span
                    className="item-row__icon"
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 9,
                      background:
                        dose.status === 'taken'
                          ? 'var(--success-soft)'
                          : dose.status === 'skipped'
                            ? 'var(--surface-sunken)'
                            : dose.is_missed
                              ? 'var(--danger-soft)'
                              : 'var(--dosenote-soft)',
                      color:
                        dose.status === 'taken'
                          ? 'var(--success)'
                          : dose.is_missed
                            ? 'var(--danger)'
                            : dose.status === 'skipped'
                              ? 'var(--text-faint)'
                              : 'var(--dosenote)',
                    }}
                  >
                    {dose.status === 'taken' ? (
                      <Check size={15} />
                    ) : dose.status === 'skipped' ? (
                      <SkipForward size={15} />
                    ) : (
                      <Pill size={15} />
                    )}
                  </span>

                  <span className="item-row__body">
                    <span className="item-row__title" style={{ fontSize: 'var(--fs-base)' }}>
                      {dose.medication_name}
                    </span>
                    <span className="item-row__meta text-xs">
                      <span className="text-num">{formatDate(dose.scheduled_date)}</span>
                      <span className="dot-sep">{formatTime(dose.scheduled_time)}</span>
                      <span className="dot-sep">
                        {dose.dosage} {dose.dosage_unit}
                      </span>
                    </span>
                  </span>

                  <span className="item-row__right">
                    <StatusBadge
                      status={dose.is_missed && dose.status === 'pending' ? 'overdue' : dose.status}
                      label={dose.is_missed && dose.status === 'pending' ? 'Missed' : dose.status_label}
                    />
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <div className="alert alert--neutral">
        <AlertTriangle size={16} aria-hidden="true" />
        <span className="text-xs">
          A pending dose becomes &quot;missed&quot; on screen once it is more than{' '}
          {settings?.dose_grace_minutes ?? 60} minutes past its time. DailyFlow never marks a dose
          as taken for you, and never advises changing a prescribed medication.
        </span>
      </div>

      <MedicationFormModal
        open={formOpen}
        schedule={editing}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={editing ? handleUpdate : handleCreate}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        busy={deleting}
        title="Delete this schedule?"
        description={`"${deleteTarget?.medication_name}" and all of its dose logs will be permanently removed. To keep the history, cancel and deactivate it instead.`}
        confirmLabel="Delete schedule"
        cancelLabel="Keep it"
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </>
  )
}