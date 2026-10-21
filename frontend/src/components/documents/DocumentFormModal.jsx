/** DocumentFormModal - add / edit a tracked document. */

import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import Modal from '../common/Modal'
import FormField, { FormErrorBanner, fieldProps, selectProps, textareaProps } from '../common/FormField'
import { DOCUMENT_TYPES, REMINDER_OPTIONS } from '../../api/documents'
import { todayISO } from '../../utils/format'

const EMPTY_FORM = {
  document_name: '',
  document_type: 'other',
  document_number: '',
  issue_date: '',
  expiry_date: '',
  issuing_authority: '',
  reminder_days_before: 30,
  notes: '',
}

export default function DocumentFormModal({ open, onClose, onSubmit, document: doc = null }) {
  const isEdit = Boolean(doc)

  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    if (doc) {
      setForm({
        document_name: doc.document_name || '',
        document_type: doc.document_type || 'other',
        document_number: doc.document_number || '',
        issue_date: doc.issue_date || '',
        expiry_date: doc.expiry_date || '',
        issuing_authority: doc.issuing_authority || '',
        reminder_days_before: doc.reminder_days_before ?? 30,
        notes: doc.notes || '',
      })
    } else {
      setForm({ ...EMPTY_FORM, expiry_date: '' })
    }
    setErrors({})
    setFormError('')
    setSaving(false)
  }, [open, doc])

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  function validate() {
    const next = {}
    if (!form.document_name.trim()) next.document_name = 'Give the document a name.'
    if (!form.expiry_date) next.expiry_date = 'An expiry date is required.'
    if (form.issue_date && form.expiry_date && form.issue_date > form.expiry_date) {
      next.expiry_date = 'The expiry date must be after the issue date.'
    }
    if (form.reminder_days_before < 0 || form.reminder_days_before > 365) {
      next.reminder_days_before = 'Choose between 0 and 365 days.'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    if (!validate()) return

    setSaving(true)
    try {
      await onSubmit({
        document_name: form.document_name.trim(),
        document_type: form.document_type,
        document_number: form.document_number.trim() || null,
        issue_date: form.issue_date || null,
        expiry_date: form.expiry_date,
        issuing_authority: form.issuing_authority.trim() || null,
        reminder_days_before: Number(form.reminder_days_before),
        notes: form.notes.trim() || null,
      })
    } catch (error) {
      setFormError(error.message || 'Could not save this document.')
      if (error.fields) setErrors((current) => ({ ...current, ...error.fields }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title={isEdit ? 'Edit document' : 'Track a document'}
      description={
        isEdit ? 'Update the details of this document.' : 'DailyFlow will remind you before it expires.'
      }
      icon={<FileText size={20} />}
      accent="dateguard"
      footer={
        <>
          <button type="button" className="btn btn--secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="document-form" className="btn btn--primary" disabled={saving}>
            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Track document'}
          </button>
        </>
      }
    >
      <form id="document-form" onSubmit={handleSubmit} className="stack">
        <FormErrorBanner message={formError} fields={errors} />

        <div className="form-grid">
          <FormField label="Document name" htmlFor="document_name" error={errors.document_name} required full>
            <input
              {...fieldProps('document_name', errors)}
              id="document_name"
              type="text"
              placeholder="e.g. Driving Licence"
              value={form.document_name}
              onChange={(event) => update('document_name', event.target.value)}
              maxLength={120}
            />
          </FormField>

          <FormField label="Document type" htmlFor="document_type" error={errors.document_type}>
            <select
              {...selectProps('document_type', errors)}
              id="document_type"
              value={form.document_type}
              onChange={(event) => update('document_type', event.target.value)}
            >
              {DOCUMENT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField
            label="Document number"
            htmlFor="document_number"
            error={errors.document_number}
            hint="Optional. Hidden everywhere except the detail view."
          >
            <input
              {...fieldProps('document_number', errors)}
              id="document_number"
              type="text"
              placeholder="e.g. DL-2024-1234"
              value={form.document_number}
              onChange={(event) => update('document_number', event.target.value)}
              maxLength={60}
            />
          </FormField>

          <FormField label="Issue date" htmlFor="issue_date" error={errors.issue_date}>
            <input
              {...fieldProps('issue_date', errors)}
              id="issue_date"
              type="date"
              max={form.expiry_date || undefined}
              value={form.issue_date}
              onChange={(event) => update('issue_date', event.target.value)}
            />
          </FormField>

          <FormField label="Expiry date" htmlFor="expiry_date" error={errors.expiry_date} required>
            <input
              {...fieldProps('expiry_date', errors)}
              id="expiry_date"
              type="date"
              min={form.issue_date || undefined}
              value={form.expiry_date}
              onChange={(event) => update('expiry_date', event.target.value)}
            />
          </FormField>

          <FormField label="Issuing authority" htmlFor="issuing_authority" error={errors.issuing_authority}>
            <input
              {...fieldProps('issuing_authority', errors)}
              id="issuing_authority"
              type="text"
              placeholder="e.g. Regional Office"
              value={form.issuing_authority}
              onChange={(event) => update('issuing_authority', event.target.value)}
              maxLength={120}
            />
          </FormField>

          <FormField
            label="Remind me before"
            htmlFor="reminder_days_before"
            error={errors.reminder_days_before}
            hint="This document's own lead time, independent of the global default."
          >
            <select
              {...selectProps('reminder_days_before', errors)}
              id="reminder_days_before"
              value={form.reminder_days_before}
              onChange={(event) => update('reminder_days_before', event.target.value)}
            >
              {REMINDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
              {!REMINDER_OPTIONS.some((o) => o.value === Number(form.reminder_days_before)) ? (
                <option value={form.reminder_days_before}>
                  {form.reminder_days_before} days before
                </option>
              ) : null}
            </select>
          </FormField>

          <FormField label="Notes" htmlFor="doc_notes" error={errors.notes} full>
            <textarea
              {...textareaProps('notes', errors)}
              id="doc_notes"
              rows={2}
              placeholder="Renewal instructions, office hours, and so on"
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