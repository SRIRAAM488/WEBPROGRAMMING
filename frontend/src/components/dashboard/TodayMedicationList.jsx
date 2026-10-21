/**
 * TodayMedicationList - today's schedule with working "Mark taken" actions.
 *
 * Buttons are disabled while a request is in flight so a double click cannot
 * create two updates, and the list refreshes from the server afterwards so the
 * completion bar always matches the database.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Info, Pill, RotateCcw, SkipForward } from 'lucide-react'
import StatusBadge from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { ProgressBar } from '../common/Progress'
import { updateDoseLog } from '../../api/medications'
import { useToast } from '../../context/ToastContext'
import { formatTime } from '../../utils/format'
import { MEDICAL_DISCLAIMER } from '../../api/medications'

export default function TodayMedicationList({
  data,
  loading = false,
  onChanged,
  showDisclaimer = true,
}) {
  const toast = useToast()
  const [busyId, setBusyId] = useState(null)

  async function setStatus(dose, status) {
    setBusyId(dose.id)
    try {
      await updateDoseLog(dose.id, { status })
      toast.success(
        status === 'taken'
          ? `Marked ${dose.medication_name} as taken.`
          : status === 'skipped'
            ? `Marked ${dose.medication_name} as skipped.`
            : 'Dose moved back to pending.'
      )
      await onChanged?.()
    } catch (error) {
      toast.error(error.message || 'Could not update the dose.')
    } finally {
      setBusyId(null)
    }
  }

  if (loading) {
    return (
      <div className="stack stack--sm" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: 52 }} />
        ))}
      </div>
    )
  }

  if (!data || data.doses.length === 0) {
    return (
      <EmptyState
        compact
        icon={<Pill size={24} />}
        title="No doses scheduled today"
        description="Add a medication schedule on the DoseNote page and today's doses will appear here automatically."
        action={
          <Link to="/medications" className="btn btn--soft btn--sm">
            Add a schedule
          </Link>
        }
      />
    )
  }

  return (
    <div className="stack stack--sm">
      <div className="row row--between">
        <div className="text-sm text-muted">
          <strong className="text-num" style={{ color: 'var(--text)' }}>
            {data.taken}
          </strong>{' '}
          of{' '}
          <strong className="text-num" style={{ color: 'var(--text)' }}>
            {data.total_doses}
          </strong>{' '}
          doses taken today
          {data.missed > 0 ? (
            <span className="text-danger"> · {data.missed} missed</span>
          ) : null}
        </div>
        <span className="text-sm text-num font-semibold" style={{ color: 'var(--dosenote)' }}>
          {data.completion_percent}%
        </span>
      </div>

      <ProgressBar
        value={data.taken}
        max={data.total_doses}
        accent="dosenote"
        size="thin"
        label="Today's dose completion"
      />

      <div className="item-list">
        {data.doses.map((dose) => {
          const busy = busyId === dose.id
          return (
            <div key={dose.id} className="item-row">
              <span
                className="item-row__icon"
                style={{
                  background:
                    dose.status === 'taken'
                      ? 'var(--success-soft)'
                      : dose.is_missed
                        ? 'var(--danger-soft)'
                        : 'var(--dosenote-soft)',
                  color:
                    dose.status === 'taken'
                      ? 'var(--success)'
                      : dose.is_missed
                        ? 'var(--danger)'
                        : 'var(--dosenote)',
                }}
              >
                {dose.status === 'taken' ? (
                  <Check size={17} />
                ) : dose.status === 'skipped' ? (
                  <SkipForward size={17} />
                ) : (
                  <Pill size={17} />
                )}
              </span>

              <span className="item-row__body">
                <span className="item-row__title">
                  {dose.medication_name}
                  <StatusBadge
                    status={dose.is_missed && dose.status === 'pending' ? 'overdue' : dose.status}
                    label={
                      dose.is_missed && dose.status === 'pending'
                        ? 'Missed'
                        : dose.status_label
                    }
                  />
                </span>
                <span className="item-row__meta">
                  <span className="text-num font-semibold">
                    {formatTime(dose.scheduled_time)}
                  </span>
                  <span className="dot-sep">
                    {dose.dosage} {dose.dosage_unit}
                  </span>
                  {dose.instructions ? (
                    <span className="dot-sep text-truncate" style={{ maxWidth: 260 }}>
                      {dose.instructions}
                    </span>
                  ) : null}
                </span>
              </span>

              <span className="item-row__actions">
                {dose.status === 'taken' ? (
                  <>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() => setStatus(dose, 'skipped')}
                      disabled={busy}
                      title="Mark as skipped"
                    >
                      <SkipForward size={14} />
                      <span className="hide-mobile">Skip</span>
                    </button>
                    <button
                      type="button"
                      className="icon-action"
                      onClick={() => setStatus(dose, 'pending')}
                      disabled={busy}
                      title="Undo, mark as pending again"
                      aria-label={`Undo taken status for ${dose.medication_name}`}
                    >
                      <RotateCcw size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="btn btn--sm"
                      style={{
                        background: 'var(--success)',
                        color: '#fff',
                      }}
                      onClick={() => setStatus(dose, 'taken')}
                      disabled={busy}
                      title="Mark as taken"
                    >
                      {busy ? '…' : <Check size={14} />}
                      <span className="hide-mobile">Taken</span>
                    </button>
                    {dose.status === 'skipped' ? (
                      <button
                        type="button"
                        className="icon-action"
                        onClick={() => setStatus(dose, 'pending')}
                        disabled={busy}
                        title="Undo, mark as pending again"
                        aria-label={`Undo skipped status for ${dose.medication_name}`}
                      >
                        <RotateCcw size={14} />
                      </button>
                    ) : null}
                  </>
                )}
              </span>
            </div>
          )
        })}
      </div>

      {showDisclaimer ? (
        <div className="alert alert--neutral" style={{ marginTop: 'var(--sp-2)' }}>
          <Info size={15} aria-hidden="true" />
          <span className="text-xs">{MEDICAL_DISCLAIMER}</span>
        </div>
      ) : null}
    </div>
  )
}