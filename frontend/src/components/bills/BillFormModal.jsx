/**
 * BillFormModal - add / edit a bill.
 *
 * The same component handles both cases so the fields, validation and layout
 * can never drift apart. Client-side validation runs first (fast feedback), but
 * the backend validates everything again - it is the real guard.
 */

import { useEffect, useState } from 'react'
import { Receipt } from 'lucide-react'
import Modal from '../common/Modal'
import FormField, { FormErrorBanner, fieldProps, selectProps, textareaProps } from '../common/FormField'
import { BILL_CATEGORIES, CURRENCIES, RECURRENCE_OPTIONS } from '../../api/bills'
import { useSettings } from '../../context/SettingsContext'
import { todayISO } from '../../utils/format'

const EMPTY_FORM = {
  bill_name: '',
  category: 'other',
  provider: '',
  amount: '',
  currency: 'INR',
  due_date: todayISO(),
  recurring: false,
  recurrence_interval: 'monthly',
  notes: '',
}

export default function BillFormModal({ open, onClose, onSubmit, bill = null }) {
  const isEdit = Boolean(bill)
  const { currency: defaultCurrency } = useSettings()

  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  // Reset the form each time the modal opens.
  useEffect(() => {
    if (!open) return
    if (bill) {
      setForm({
        bill_name: bill.bill_name || '',
        category: bill.category || 'other',
        provider: bill.provider || '',
        amount: String(bill.amount ?? ''),
        currency: bill.currency || 'INR',
        due_date: bill.due_date || todayISO(),
        recurring: Boolean(bill.recurring),
        recurrence_interval: bill.recurring
          ? bill.recurrence_interval || 'monthly'
          : 'monthly',
        notes: bill.notes || '',
      })
    } else {
      setForm({ ...EMPTY_FORM, currency: defaultCurrency })
    }
    setErrors({})
    setFormError('')
    setSaving(false)
  }, [open, bill, defaultCurrency])

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    // Clear the error for a field as soon as the user edits it.
    setErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  /** Quick client-side checks. The server repeats all of these. */
  function validate() {
    const next = {}

    if (!form.bill_name.trim()) next.bill_name = 'Give the bill a name.'

    const amount = Number(form.amount)
    if (form.amount === '') next.amount = 'Enter the amount.'
    else if (!Number.isFinite(amount)) next.amount = 'Amount must be a number.'
    else if (amount <= 0) next.amount = 'Amount must be greater than 0.'
    else if (amount > 10_000_000) next.amount = 'That amount is too large.'

    if (!form.due_date) next.due_date = 'Pick a due date.'

    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    if (!validate()) return

    setSaving(true)
    try {
      const payload = {
        bill_name: form.bill_name.trim(),
        category: form.category,
        provider: form.provider.trim() || null,
        // Send as a string so the backend's Decimal handles it exactly.
        amount: String(Number(form.amount)).slice(0, 12),
        currency: form.currency,
        due_date: form.due_date,
        recurring: form.recurring,
        recurrence_interval: form.recurring ? form.recurrence_interval : 'none',
        notes: form.notes.trim() || null,
      }

      // When editing, we never touch status - use the dedicated /pay endpoint.
      if (isEdit) {
        delete payload.recurring
        payload.recurring = form.recurring
        payload.recurrence_interval = form.recurring ? form.recurrence_interval : 'none'
      }

      await onSubmit(payload)
    } catch (error) {
      setFormError(error.message || 'Could not save this bill.')
      if (error.fields) setErrors((current) => ({ ...current, ...error.fields }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title={isEdit ? 'Edit bill' : 'Add a bill'}
      description={
        isEdit
          ? 'Update the details of this bill.'
          : 'Track a one-time or recurring payment.'
      }
      icon={<Receipt size={20} />}
      accent="billbell"
      footer={
        <>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            form="bill-form"
            className="btn btn--primary"
            disabled={saving}
          >
            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add bill'}
          </button>
        </>
      }
    >
      <form id="bill-form" onSubmit={handleSubmit} className="stack">
        <FormErrorBanner message={formError} fields={errors} />

        <div className="form-grid">
          <FormField label="Bill name" htmlFor="bill_name" error={errors.bill_name} required full>
            <input
              {...fieldProps('bill_name', errors)}
              id="bill_name"
              type="text"
              placeholder="e.g. Electricity Bill"
              value={form.bill_name}
              onChange={(event) => update('bill_name', event.target.value)}
              maxLength={120}
            />
          </FormField>

          <FormField label="Amount" htmlFor="amount" error={errors.amount} required>
            <div className="input-group">
              <input
                {...fieldProps('amount', errors)}
                id="amount"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                value={form.amount}
                onChange={(event) => update('amount', event.target.value)}
              />
              <span className="input-group__suffix">{form.currency}</span>
            </div>
          </FormField>

          <FormField label="Due date" htmlFor="due_date" error={errors.due_date} required>
            <input
              {...fieldProps('due_date', errors)}
              id="due_date"
              type="date"
              value={form.due_date}
              onChange={(event) => update('due_date', event.target.value)}
            />
          </FormField>

          <FormField label="Category" htmlFor="category" error={errors.category}>
            <select
              {...selectProps('category', errors)}
              id="category"
              value={form.category}
              onChange={(event) => update('category', event.target.value)}
            >
              {BILL_CATEGORIES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Provider" htmlFor="provider" error={errors.provider}>
            <input
              {...fieldProps('provider', errors)}
              id="provider"
              type="text"
              placeholder="e.g. DemoPower"
              value={form.provider}
              onChange={(event) => update('provider', event.target.value)}
              maxLength={120}
            />
          </FormField>

          <FormField
            label="Currency"
            htmlFor="currency"
            error={errors.currency}
            hint="No conversion is performed; amounts are stored as entered."
          >
            <select
              {...selectProps('currency', errors)}
              id="currency"
              value={form.currency}
              onChange={(event) => update('currency', event.target.value)}
            >
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </FormField>

          <div className="form-field">
            <span className="form-label">Recurring</span>
            <label className="switch" style={{ height: 38 }}>
              <input
                type="checkbox"
                checked={form.recurring}
                onChange={(event) => update('recurring', event.target.checked)}
              />
              <span className="switch__track">
                <span className="switch__thumb" />
              </span>
              <span className="text-sm text-muted">
                {form.recurring ? 'Repeats automatically' : 'One-time bill'}
              </span>
            </label>
          </div>

          {form.recurring ? (
            <FormField
              label="Repeats"
              htmlFor="recurrence_interval"
              error={errors.recurrence_interval}
              hint="After you mark this bill paid you can create the next cycle."
              full
            >
              <select
                {...selectProps('recurrence_interval', errors)}
                id="recurrence_interval"
                value={form.recurrence_interval}
                onChange={(event) => update('recurrence_interval', event.target.value)}
              >
                {RECURRENCE_OPTIONS.filter((option) => option.value !== 'none').map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}

          <FormField label="Notes" htmlFor="notes" error={errors.notes} full>
            <textarea
              {...textareaProps('notes', errors)}
              id="notes"
              rows={3}
              placeholder="Anything worth remembering about this bill"
              value={form.notes}
              onChange={(event) => update('notes', event.target.value)}
              maxLength={1000}
            />
          </FormField>
        </div>
      </form>
    </Modal>
  )
}