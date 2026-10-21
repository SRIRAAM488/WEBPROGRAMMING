/**
 * DashboardPage - the DailyFlow home screen.
 *
 * Data comes from three parallel requests:
 *   GET /api/dashboard/summary   -> the four overview cards
 *   GET /api/dashboard/charts    -> every chart
 *   GET /api/dashboard/activity  -> the recent activity feed
 *
 * Every figure shown here is computed by the backend from real database rows.
 * The page also pulls today's doses and the reminder list so the "Mark taken"
 * buttons and the quick water log work without leaving the page.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlarmClock,
  BellRing,
  CalendarClock,
  CheckCircle2,
  Clock3,
  CreditCard,
  Droplets,
  FileText,
  Pill,
  Plus,
  Receipt,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import SummaryCard from '../components/dashboard/SummaryCard'
import UpcomingReminders from '../components/dashboard/UpcomingReminders'
import WeeklyHydrationChart from '../components/dashboard/WeeklyHydrationChart'
import PaymentSummary from '../components/dashboard/PaymentSummary'
import TodayMedicationList from '../components/dashboard/TodayMedicationList'
import DocumentExpiryOverview from '../components/dashboard/DocumentExpiryOverview'
import QuickActions from '../components/dashboard/QuickActions'
import RecentActivity from '../components/dashboard/RecentActivity'
import AdherenceChart from '../components/dashboard/AdherenceChart'

import { DashboardSkeleton } from '../components/common/LoadingSkeleton'
import { ErrorState } from '../components/common/EmptyState'
import Modal from '../components/common/Modal'
import FormField, { fieldProps } from '../components/common/FormField'

import { fetchDashboardBundle } from '../api/dashboard'
import { fetchTodayDoses } from '../api/medications'
import { fetchExpiringDocuments } from '../api/documents'
import { fetchReminders } from '../api/reminders'
import { createIntake, fetchHydrationSettings } from '../api/hydration'
import { getErrorMessage } from '../api/client'
import { useSettings } from '../context/SettingsContext'
import { useToast } from '../context/ToastContext'
import { formatCurrency, formatDate, formatLongToday, formatMl } from '../utils/format'

export default function DashboardPage() {
  const { currency, refreshReminders } = useSettings()
  const toast = useToast()

  const [bundle, setBundle] = useState(null)
  const [todayDoses, setTodayDoses] = useState(null)
  const [reminders, setReminders] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [waterModal, setWaterModal] = useState(false)
  const [waterAmount, setWaterAmount] = useState('250')
  const [savingWater, setSavingWater] = useState(false)
  const [waterError, setWaterError] = useState('')

  const load = useCallback(async () => {
    try {
      setError(null)
      // Fire everything at once rather than in sequence - much faster on load.
      const [data, doses, rems, docs, hydrationSettings] = await Promise.all([
        fetchDashboardBundle(),
        fetchTodayDoses(),
        fetchReminders(),
        fetchExpiringDocuments(60),
        fetchHydrationSettings().catch(() => null),
      ])
      setBundle(data)
      setTodayDoses(doses)
      setReminders(rems.items || [])
      setDocuments(docs)
      if (hydrationSettings) setWaterAmount(String(hydrationSettings.default_serving_ml))
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load the dashboard.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const quickLogWater = useCallback(
    async (amount) => {
      try {
        await createIntake({ amount_ml: amount })
        toast.success(`Logged ${amount} ml of water.`)
        setWaterModal(false)
        await load()
        refreshReminders()
      } catch (err) {
        toast.error(getErrorMessage(err, 'Could not log that amount.'))
      }
    },
    [load, refreshReminders, toast]
  )

  const submitWater = async (event) => {
    event.preventDefault()
    const amount = Number(waterAmount)
    if (!Number.isInteger(amount) || amount <= 0) {
      setWaterError('Enter a whole number of millilitres greater than 0.')
      return
    }
    if (amount > 5000) {
      setWaterError('That is more than 5000 ml. Please enter a smaller amount.')
      return
    }
    setWaterError('')
    setSavingWater(true)
    await quickLogWater(amount)
    setSavingWater(false)
  }

  if (loading) {
    return (
      <>
        <PageHeader loading />
        <DashboardSkeleton />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader loading={false} />
        <div className="card">
          <ErrorState
            title="Could not load the dashboard"
            message={error}
            onRetry={() => {
              setLoading(true)
              load()
            }}
          />
        </div>
      </>
    )
  }

  const summary = bundle.summary
  const charts = bundle.charts
  const activity = bundle.activity

  return (
    <>
      <PageHeader
        greeting={summary.greeting_name}
        reminders={summary.total_pending_reminders}
        overdue={summary.overdue_reminders}
      />

      {/* ---------------- Overview cards ---------------- */}
      <div className="grid grid--summary">
        <SummaryCard
          module="billbell"
          icon={<Receipt size={20} />}
          title="BillBell"
          hint="Bills and payments"
          hero={formatCurrency(summary.bills.total_unpaid_amount, summary.bills.currency, { decimals: 0 })}
          heroUnit="outstanding"
          to="/bills"
          footer="Open BillBell"
          stats={[
            {
              label: 'Unpaid bills',
              value: summary.bills.unpaid_count,
              icon: Clock3,
            },
            summary.bills.overdue_count > 0
              ? {
                  label: 'Overdue',
                  value: summary.bills.overdue_count,
                  icon: AlarmClock,
                  tone: 'danger',
                }
              : {
                  label: 'Overdue',
                  value: 0,
                  icon: CheckCircle2,
                  tone: 'success',
                },
            {
              label: 'Next due',
              value: summary.bills.next_due_date
                ? formatDate(summary.bills.next_due_date)
                : 'Nothing due',
            },
          ]}
        />

        <SummaryCard
          module="dateguard"
          icon={<FileText size={20} />}
          title="DateGuard"
          hint="Document expiry"
          hero={summary.documents.total_documents}
          heroUnit="tracked"
          to="/documents"
          footer="Open DateGuard"
          stats={[
            {
              label: 'Expiring soon',
              value: summary.documents.expiring_in_30_days,
              icon: CalendarClock,
              tone: summary.documents.expiring_in_30_days > 0 ? 'warning' : undefined,
            },
            {
              label: 'Expired',
              value: summary.documents.expired_count,
              icon: AlarmClock,
              tone: summary.documents.expired_count > 0 ? 'danger' : 'success',
            },
            {
              label: 'Next expiry',
              value: summary.documents.next_expiry_date
                ? formatDate(summary.documents.next_expiry_date)
                : 'None',
            },
          ]}
        />

        <SummaryCard
          module="dosenote"
          icon={<Pill size={20} />}
          title="DoseNote"
          hint="Medication schedule"
          hero={todayDoses ? `${todayDoses.taken}/${todayDoses.total_doses}` : '0/0'}
          heroUnit="doses today"
          to="/medications"
          footer="Open DoseNote"
          stats={[
            { label: 'Active schedules', value: summary.medications.active_schedules },
            {
              label: 'Still due today',
              value: summary.medications.doses_pending_today,
              icon: Clock3,
              tone: summary.medications.doses_pending_today > 0 ? 'warning' : 'success',
            },
            {
              label: 'Completion',
              value: `${summary.medications.completion_percent}%`,
              icon: TrendingUp,
            },
          ]}
        />

        <SummaryCard
          module="aquahabit"
          icon={<Droplets size={20} />}
          title="AquaHabit"
          hint="Water intake"
          hero={summary.hydration.percent_complete}
          heroUnit="% of goal"
          to="/hydration"
          footer="Open AquaHabit"
          stats={[
            { label: 'Today', value: formatMl(summary.hydration.consumed_today_ml) },
            { label: 'Goal', value: formatMl(summary.hydration.daily_goal_ml) },
            {
              label: 'Remaining',
              value: formatMl(summary.hydration.remaining_ml),
              tone: summary.hydration.goal_reached ? 'success' : undefined,
            },
          ]}
        />
      </div>

      {/* ---------------- Main grid ---------------- */}
      <div className="grid grid--dashboard">
        {/* Left column */}
        <div className="stack stack--lg">
          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}
              >
                <BellRing size={18} />
              </div>
              <div>
                <h2 className="card__title">Upcoming reminders</h2>
                <p className="card__subtitle">
                  From all four modules · click any row to jump to the record
                </p>
              </div>
              <div className="card__actions">
                <Link to="/reminders" className="btn btn--ghost btn--sm">
                  View all
                </Link>
              </div>
            </div>
            <div className="card__body card__body--tight">
              <UpcomingReminders reminders={reminders} limit={6} />
            </div>
          </section>

          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--aquahabit-soft)', color: 'var(--aquahabit)' }}
              >
                <Droplets size={18} />
              </div>
              <div>
                <h2 className="card__title">Weekly hydration</h2>
                <p className="card__subtitle">Last 7 days · from your water log</p>
              </div>
              <div className="card__actions">
                <Link to="/hydration" className="btn btn--ghost btn--sm">
                  AquaHabit
                </Link>
              </div>
            </div>
            <div className="card__body">
              <WeeklyHydrationChart data={charts.hydration_weekly} />
            </div>
          </section>

          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}
              >
                <Pill size={18} />
              </div>
              <div>
                <h2 className="card__title">Today's medication schedule</h2>
                <p className="card__subtitle">
                  {todayDoses
                    ? `${todayDoses.taken} of ${todayDoses.total_doses} doses taken`
                    : 'No doses scheduled'}
                </p>
              </div>
              <div className="card__actions">
                <Link to="/medications" className="btn btn--ghost btn--sm">
                  DoseNote
                </Link>
              </div>
            </div>
            <div className="card__body card__body--tight">
              <div style={{ padding: '0 var(--sp-2)' }}>
                <TodayMedicationList
                  data={todayDoses}
                  onChanged={async () => {
                    const doses = await fetchTodayDoses()
                    setTodayDoses(doses)
                    await load()
                    refreshReminders()
                  }}
                />
              </div>
            </div>
          </section>
        </div>

        {/* Right column */}
        <div className="stack stack--lg">
          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--billbell-soft)', color: 'var(--billbell)' }}
              >
                <CreditCard size={18} />
              </div>
              <div>
                <h2 className="card__title">Bill payment summary</h2>
                <p className="card__subtitle">Paid versus outstanding</p>
              </div>
            </div>
            <div className="card__body">
              <PaymentSummary summary={summary.bills} currency={summary.bills.currency} />
            </div>
          </section>

          <section className="card">
            <div className="card__header">
              <div
                className="card__icon"
                style={{ background: 'var(--dateguard-soft)', color: 'var(--dateguard)' }}
              >
                <CalendarClock size={18} />
              </div>
              <div>
                <h2 className="card__title">Document expiry</h2>
                <p className="card__subtitle">Expiring in the next 60 days</p>
              </div>
            </div>
            <div className="card__body card__body--tight">
              <DocumentExpiryOverview documents={documents} limit={5} />
            </div>
          </section>

          {charts.bills_by_category?.length ? (
            <section className="card">
              <div className="card__header">
                <div
                  className="card__icon"
                  style={{ background: 'var(--billbell-soft)', color: 'var(--billbell)' }}
                >
                  <Receipt size={18} />
                </div>
                <div>
                  <h2 className="card__title">Bills by category</h2>
                  <p className="card__subtitle">Where the money goes</p>
                </div>
              </div>
              <div className="card__body">
                <CategoryChart data={charts.bills_by_category} currency={currency} />
              </div>
            </section>
          ) : null}

          {charts.medication_weekly?.some((point) => point.scheduled > 0) ? (
            <section className="card">
              <div className="card__header">
                <div
                  className="card__icon"
                  style={{ background: 'var(--dosenote-soft)', color: 'var(--dosenote)' }}
                >
                  <TrendingUp size={18} />
                </div>
                <div>
                  <h2 className="card__title">Weekly adherence</h2>
                  <p className="card__subtitle">Taken, skipped and missed doses</p>
                </div>
              </div>
              <div className="card__body">
                <AdherenceChart data={charts.medication_weekly} height={210} />
              </div>
            </section>
          ) : null}
        </div>
      </div>

      {/* ---------------- Quick actions + recent activity ---------------- */}
      <div className="grid grid--dashboard">
        <section className="card">
          <div className="card__header">
            <div
              className="card__icon"
              style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}
            >
              <Plus size={18} />
            </div>
            <div>
              <h2 className="card__title">Quick actions</h2>
              <p className="card__subtitle">Jump straight into adding a record</p>
            </div>
          </div>
          <div className="card__body">
            <QuickActions onQuickLog={() => setWaterModal(true)} />
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            <div
              className="card__icon"
              style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="card__title">Recent activity</h2>
              <p className="card__subtitle">From your real records</p>
            </div>
          </div>
          <div className="card__body card__body--tight">
            <RecentActivity items={activity.items} limit={7} />
          </div>
        </section>
      </div>

      {/* ---------------- Log water modal ---------------- */}
      <Modal
        open={waterModal}
        onClose={() => setWaterModal(false)}
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
              onClick={() => setWaterModal(false)}
              disabled={savingWater}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="quick-water-form"
              className="btn btn--primary"
              disabled={savingWater}
            >
              {savingWater ? 'Saving…' : 'Log water'}
            </button>
          </>
        }
      >
        <form id="quick-water-form" onSubmit={submitWater} className="stack">
          <div className="quick-add">
            {[150, 250, 350, 500].map((amount) => (
              <button
                key={amount}
                type="button"
                className="quick-add__btn"
                onClick={() => setWaterAmount(String(amount))}
                disabled={savingWater}
              >
                +{amount}
                <small>ml</small>
              </button>
            ))}
          </div>

          <FormField label="Custom amount" htmlFor="quick-water-amount" error={waterError}>
            <div className="input-group">
              <input
                {...fieldProps('amount_ml', waterError ? { amount_ml: true } : {})}
                id="quick-water-amount"
                type="number"
                min="1"
                max="5000"
                step="1"
                value={waterAmount}
                onChange={(event) => {
                  setWaterAmount(event.target.value)
                  setWaterError('')
                }}
                className={waterError ? 'input input--error' : 'input'}
              />
              <span className="input-group__suffix">ml</span>
            </div>
          </FormField>
        </form>
      </Modal>
    </>
  )
}

/** The dashboard greeting header. */
function PageHeader({ greeting: greetingText, reminders = 0, overdue = 0, loading = false }) {
  const subtitle =
    overdue > 0
      ? `${overdue} overdue reminder${overdue === 1 ? '' : 's'} need your attention today.`
      : reminders > 0
        ? `${reminders} reminder${reminders === 1 ? '' : 's'} coming up. You're on track.`
        : 'Everything is on track today. Nothing needs your attention.'

  return (
    <div className="page-head">
      <div className="page-head__icon" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>
        <Sparkles size={23} />
      </div>

      <div className="page-head__text">
        <h1 className="page-head__title">
          {loading ? 'Loading your day…' : greetingText || 'Welcome back!'}
        </h1>
        <p className="page-head__desc">{subtitle}</p>
        <p className="text-xs text-faint" style={{ marginTop: 2 }}>
          {formatLongToday()}
        </p>
      </div>

      <div className="page-head__actions">
        <Link to="/reminders" className="btn btn--secondary">
          <BellRing size={16} />
          Reminders
          {reminders > 0 ? (
            <span className="badge badge--danger">{reminders}</span>
          ) : null}
        </Link>
        <Link to="/bills?action=add" className="btn btn--primary">
          <Plus size={16} />
          Add a record
        </Link>
      </div>
    </div>
  )
}

/** Donut chart of bills per category. */
function CategoryChart({ data, currency }) {
  const total = data.reduce((sum, slice) => sum + Number(slice.amount || 0), 0)

  if (!total) return null

  return (
    <div className="stack stack--sm">
      <div className="chart-box" style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="amount"
              nameKey="label"
              innerRadius={48}
              outerRadius={76}
              paddingAngle={3}
              stroke="none"
            >
              {data.map((slice, index) => (
                <Cell key={slice.key} fill={PIE_COLORS[index % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatCurrency(value, currency, { decimals: 0 })}
              contentStyle={{
                background: 'var(--surface)',
                border: '1px solid var(--border-strong)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--fs-sm)',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="stack stack--sm">
        {data.slice(0, 4).map((slice, index) => (
          <div key={slice.key} className="row row--between text-sm">
            <span className="row" style={{ gap: 7 }}>
              <span
                className="chart-legend__swatch"
                style={{ background: PIE_COLORS[index % PIE_COLORS.length] }}
                aria-hidden="true"
              />
              {slice.label}
              <span className="text-faint">({slice.count})</span>
            </span>
            <strong className="text-num">{formatCurrency(slice.amount, currency, { decimals: 0 })}</strong>
          </div>
        ))}
      </div>
    </div>
  )
}

const PIE_COLORS = [
  '#ff8066',
  '#f6b94a',
  '#9875f5',
  '#27c7b8',
  '#5b5fef',
  '#f472b6',
  '#4ade80',
  '#60a5fa',
]