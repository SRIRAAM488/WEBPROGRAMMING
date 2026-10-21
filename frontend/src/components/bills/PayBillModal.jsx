/**
 * PayBillModal - mark a bill paid, with an option to roll into the next cycle.
 *
 * For recurring bills we do NOT silently create the next occurrence. The user
 * ticks a box saying so, which keeps the data honest and avoids duplicates.
 */

import { useEffect, useState } from 'react'
import { CheckCircle2, Repeat } from 'lucide-react'
import Modal from '../common/Modal'
import FormField, { FormErrorBanner, fieldProps } from '../common/FormField'
import { formatCurrency, todayISO } from '../../utils/format'

export default function PayBillModal({ open, onClose, bill, onConfirm }) {
  const [paymentDate, setPaymentDate] = useState(todayISO())
  const [markNextCycle, setMarkNextCycle] = useState(false)
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setPaymentDate(todayISO())
    setMarkNextCycle(false)
    setNotes('')
    setError('')
    setSaving(false)
  }, [open, bill])

  if (!bill) return null

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await onConfirm({
        payment_date: paymentDate,
        mark_next_cycle: markNextCycle,
        notes: notes.trim() || null,
      })
    } catch (err) {
      setError(err.message || 'Could not record this payment.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title="Mark bill as paid"
      description={`${bill.bill_name} · ${formatCurrency(bill.amount, bill.currency)}`}
      icon={<CheckCircle2 size={20} />}
      accent="success"
      size="sm"
      footer={
        <>
          <button type="button" className="btn btn--secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="pay-bill-form" className="btn btn--success" disabled={saving}>
            {saving ? 'Saving…' : 'Mark as paid'}
          </button>
        </>
      }
    >
      <form id="pay-bill-form" onSubmit={handleSubmit} className="stack">
        <FormErrorBanner message={error} />

        <FormField label="Payment date" htmlFor="payment_date" required>
          <input
            {...fieldProps('payment_date')}
            id="payment_date"
            type="date"
            value={paymentDate}
            onChange={(event) => setPaymentDate(event.target.value)}
          />
        </FormField>

        {bill.recurring ? (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={markNextCycle}
              onChange={(event) => setMarkNextCycle(event.target.checked)}
            />
            <span>
              <strong>Also create the next cycle</strong>
              <div className="text-xs text-muted">
                {bill.next_cycle_due_date
                  ? `The next bill will be due on ${bill.next_cycle_due_date}.`
                  : 'A new unpaid bill will be created for the next due date.'}{' '}
                DailyFlow checks first and will never create a duplicate.
              </div>
            </span>
          </label>
        ) : null}

        <FormField
          label="Note (optional)"
          htmlFor="pay_note"
          hint="Stored on this bill, for example the payment reference."
        >
          <input
            {...fieldProps('pay_note')}
            id="pay_note"
            type="text"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            maxLength={1000}
            placeholder="e.g. Paid by UPI"
          />
        </FormField>

        {bill.recurring ? (
          <div className="alert alert--info">
            <Repeat size={15} aria-hidden="true" />
            <span className="text-xs">
              This bill repeats ({bill.recurrence_label?.toLowerCase()}). DailyFlow never
              creates the next cycle automatically - you choose.
            </span>
          </div>
        ) : null}
      </form>
    </Modal>
  )
}