/** RemindersPage - the unified reminder centre across all four modules. */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { BellRing, Check, Info, ShieldQuestion, Volume2, VolumeX } from 'lucide-react'

import EmptyState, { ErrorState } from '../components/common/EmptyState'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { StatTile } from '../components/common/Progress'
import { ReminderGroup } from '../components/dashboard/UpcomingReminders'

import {
  BUCKETS,
  CATEGORY_LABELS,
  MODULES,
  PRIORITIES,
  fetchReminders,
  requestNotificationPermission,
} from '../api/reminders'
import { getErrorMessage } from '../api/client'
import { useToast } from '../context/ToastContext'
import { formatDate, humanise } from '../utils/format'

export default function RemindersPage() {
  const toast = useToast()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [moduleFilter, setModuleFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')

  const [notifyState, setNotifyState] = useState('unknown') // unknown | granted | denied | unsupported
  const [notifyOpen, setNotifyOpen] = useState(false)

  // Ask the browser for its current permission without prompting the user.
  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      setNotifyState('unsupported')
      return
    }
    setNotifyState(Notification.permission)
  }, [])

  const load = useCallback(async () => {
    try {
      setError(null)
      const result = await fetchReminders()
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load your reminders.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    // Refresh every 60 seconds so "due today" stays honest while the page is open.
    const timer = setInterval(load, 60000)
    return () => clearInterval(timer)
  }, [load])

  // ---- filtering -----------------------------------------------------------

  const filtered = useMemo(() => {
    if (!data) return null
    let items = data.items || []

    if (moduleFilter !== 'all') items = items.filter((r) => r.module === moduleFilter)
    if (priorityFilter !== 'all') items = items.filter((r) => r.priority === priorityFilter)

    return {
      ...data,
      items,
      total: items.length,
      overdue_count: items.filter((r) => r.bucket === 'overdue').length,
      today_count: items.filter((r) => r.bucket === 'today').length,
      upcoming_count: items.filter((r) => r.bucket === 'upcoming').length,
      groups: {
        overdue: items.filter((r) => r.bucket === 'overdue'),
        today: items.filter((r) => r.bucket === 'today'),
        upcoming: items.filter((r) => r.bucket === 'upcoming'),
      },
    }
  }, [data, moduleFilter, priorityFilter])

  // ---- browser notification permission -------------------------------------

  async function askForNotifications() {
    const result = await requestNotificationPermission()
    setNotifyState(result.granted ? 'granted' : result.permission === 'denied' ? 'denied' : 'unknown')
    setNotifyOpen(false)

    if (result.granted) {
      toast.success('Browser notifications enabled for this session.')
    } else if (result.permission === 'denied') {
      toast.warning(
        'Notifications are blocked in your browser settings. The in-app reminder centre still works.'
      )
    } else if (!result.supported) {
      toast.warning('This browser does not support notifications. The in-app reminders still work.')
    }
  }

  // ---- render --------------------------------------------------------------

  return (
    <>
      <div className="page-head">
        <div className="page-head__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
          <BellRing size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">Reminders</h1>
          <p className="page-head__desc">
            One place for everything due across BillBell, DateGuard, DoseNote and AquaHabit.
          </p>
        </div>
      </div>

      <div className="alert alert--info">
        <Info size={16} aria-hidden="true" />
        <span>
          <strong>In-app reminders.</strong> These are generated from your current data while
          DailyFlow is open. DailyFlow does not send email, SMS or background push
          notifications — a browser must stay open for anything to appear.
        </span>
      </div>

      {data ? (
        <div className="grid grid--summary">
          <StatTile label="Total reminders" value={data.total} icon={<BellRing size={12} />} />
          <StatTile
            label="Overdue"
            value={data.overdue_count}
            tone={data.overdue_count > 0 ? 'danger' : 'success'}
          />
          <StatTile
            label="Due today"
            value={data.today_count}
            tone={data.today_count > 0 ? 'warning' : 'success'}
          />
          <StatTile label="Upcoming" value={data.upcoming_count} icon={<BellRing size={12} />} />
        </div>
      ) : null}

      {/* Browser notifications - always opt-in, never automatic */}
      <div className="card">
        <div className="card__body">
          <div className="row row--between" style={{ flexWrap: 'wrap', gap: 'var(--sp-3)' }}>
            <div className="row" style={{ gap: 'var(--sp-3)', minWidth: 0 }}>
              <span
                className="item-row__icon"
                style={{
                  background:
                    notifyState === 'granted' ? 'var(--success-soft)' : 'var(--surface-sunken)',
                  color: notifyState === 'granted' ? 'var(--success)' : 'var(--text-muted)',
                }}
              >
                {notifyState === 'granted' ? <Volume2 size={17} /> : <VolumeX size={17} />}
              </span>
              <div style={{ minWidth: 0 }}>
                <div className="item-row__title">Browser notifications</div>
                <div className="text-xs text-muted">
                  {notifyState === 'granted'
                    ? 'Enabled. Only works while a DailyFlow tab is open.'
                    : notifyState === 'denied'
                      ? 'Blocked by your browser settings. You can re-enable it in the browser site settings.'
                      : notifyState === 'unsupported'
                        ? 'This browser does not support notifications.'
                        : 'Optional. DailyFlow asks your permission first and never sends anything on its own.'}
                </div>
              </div>
            </div>

            {notifyState === 'default' || notifyState === 'unknown' ? (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setNotifyOpen(true)}
              >
                <Volume2 size={14} />
                Enable
              </button>
            ) : null}
            {notifyState === 'granted' ? (
              <span className="badge badge--success">
                <span className="badge__dot" />
                Enabled
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="toolbar">
        <div>
          <div className="form-label" style={{ marginBottom: 6 }}>
            Module
          </div>
          <div className="chips">
            <button
              type="button"
              className={`chip${moduleFilter === 'all' ? ' chip--active' : ''}`}
              onClick={() => setModuleFilter('all')}
            >
              All modules
            </button>
            {MODULES.map((module) => (
              <button
                key={module.key}
                type="button"
                className={`chip${moduleFilter === module.key ? ' chip--active' : ''}`}
                onClick={() => setModuleFilter(module.key)}
                style={
                  moduleFilter === module.key
                    ? { background: `var(--${module.key})`, borderColor: `var(--${module.key})` }
                    : undefined
                }
              >
                {module.label}
                {data?.items ? (
                  <span className="chip__count">
                    {data.items.filter((r) => r.module === module.key).length}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginLeft: 'auto' }}>
          <div className="form-label" style={{ marginBottom: 6 }}>
            Priority
          </div>
          <select
            className="select"
            value={priorityFilter}
            onChange={(event) => setPriorityFilter(event.target.value)}
            aria-label="Filter by priority"
          >
            <option value="all">All priorities</option>
            {PRIORITIES.map((priority) => (
              <option key={priority.value} value={priority.value}>
                {priority.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Reminder groups */}
      {loading ? (
        <div className="stack stack--md" aria-hidden="true">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : error ? (
        <div className="card">
          <ErrorState message={error} onRetry={load} />
        </div>
      ) : filtered.total === 0 ? (
        <div className="card">
          <EmptyState
            icon={<Check size={26} />}
            title={
              moduleFilter !== 'all' || priorityFilter !== 'all'
                ? 'No reminders match these filters'
                : 'You are all caught up'
            }
            description={
              moduleFilter !== 'all' || priorityFilter !== 'all'
                ? 'Try a different module or priority.'
                : 'No bills due, no documents expiring, no doses pending. Enjoy the quiet.'
            }
            action={
              moduleFilter !== 'all' || priorityFilter !== 'all' ? (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => {
                    setModuleFilter('all')
                    setPriorityFilter('all')
                  }}
                >
                  Clear filters
                </button>
              ) : null
            }
          />
        </div>
      ) : (
        <div className="stack stack--lg">
          {BUCKETS.map((bucket) => {
            const items = filtered.groups[bucket.value] || []
            if (!items.length && bucket.value === 'upcoming') return null

            return (
              <ReminderGroup
                key={bucket.value}
                title={bucket.label}
                items={items}
                tone={bucket.value === 'overdue' ? 'danger' : 'neutral'}
                emptyText={
                  bucket.value === 'overdue'
                    ? 'Nothing overdue. Good.'
                    : bucket.value === 'today'
                      ? 'Nothing due today.'
                      : 'Nothing coming up.'
                }
              />
            )
          })}
        </div>
      )}

      {/* Category legend, so the reminder types are self-explanatory */}
      {data && data.items.length ? (
        <div className="card">
          <div className="card__header">
            <div>
              <h2 className="card__title">Reminder types in use</h2>
              <p className="card__subtitle">
                Generated from your records · last checked {filtered ? formatDate(new Date()) : ''}
              </p>
            </div>
          </div>
          <div className="card__body">
            <div className="chips">
              {Object.entries(
                filtered.items.reduce((acc, reminder) => {
                  acc[reminder.category] = (acc[reminder.category] || 0) + 1
                  return acc
                }, {})
              ).map(([category, count]) => (
                <span key={category} className="badge badge--neutral">
                  {CATEGORY_LABELS[category] || humanise(category)}
                  <span className="chip__count">{count}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={notifyOpen}
        tone="primary"
        title="Enable browser notifications?"
        description="DailyFlow will ask your browser for permission. Notifications only appear while a DailyFlow tab is open — there is no background service."
        confirmLabel="Ask permission"
        cancelLabel="Not now"
        onClose={() => setNotifyOpen(false)}
        onConfirm={askForNotifications}
      >
        <div className="row" style={{ gap: 'var(--sp-2)', marginTop: 'var(--sp-3)', fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>
          <ShieldQuestion size={14} />
          You can change this later in your browser's site settings.
        </div>
      </ConfirmDialog>
    </>
  )
}