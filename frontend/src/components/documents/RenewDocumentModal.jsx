/** RenewDocumentModal - record a renewal without losing the old expiry date. */

import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import Modal from '../common/Modal'
import FormField, { FormErrorBanner, fieldProps } from '../common/FormField'
import { formatDate } from '../../utils/format'

export default function RenewDocumentModal({ open, onClose, document: doc, onSubmit }) {
  const [newExpiry, setNewExpiry] = useState('')
  const [issueDate, setIssueDate] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open || !doc) return
    // Default to one year after the current expiry - the most common renewal.
    const current = new Date(`${doc.expiry_date}T00:00:00`)
    const suggested = new Date(current)
    suggested.setFullYear(suggested.getFullYear() + 1)

    setNewExpiry(suggested.toISOString().slice(0, 10))
    setIssueDate(todayStr())
    setNotes('')
    setError('')
    setFieldError('')
    setSaving(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, doc])

  if (!doc) return null

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFieldError('')

    if (!newExpiry) {
      setFieldError('Pick the new expiry date.')
      return
    }
    if (newExpiry <= doc.expiry_date) {
      setFieldError('The new expiry date must be later than the current one.')
      return
    }

    setSaving(true)
    try {
      await onSubmit({
        new_expiry_date: newExpiry,
        issue_date: issueDate || null,
        notes: notes.trim() || null,
      })
    } catch (err) {
      setError(err.message || 'Could not record the renewal.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title="Record a renewal"
      description={doc.document_name}
      icon={<RefreshCw size={20} />}
      accent="dateguard"
      size="sm"
      footer={
        <>
          <button type="button" className="btn btn--secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="renew-form" className="btn btn--primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save renewal'}
          </button>
        </>
      }
    >
      <form id="renew-form" onSubmit={handleSubmit} className="stack">
        <FormErrorBanner message={error} />

        <div className="alert alert--info">
          <RefreshCw size={15} aria-hidden="true" />
          <span className="text-xs">
            The current expiry date (<strong>{formatDate(doc.expiry_date)}</strong>) is kept in
            the renewal history, so nothing is lost.
          </span>
        </div>

        <FormField
          label="New expiry date"
          htmlFor="new_expiry_date"
          error={fieldError}
          required
        >
          <input
            {...fieldProps('new_expiry_date', fieldError ? { new_expiry_date: true } : {})}
            id="new_expiry_date"
            type="date"
            min={doc.expiry_date}
            value={newExpiry}
            onChange={(event) => {
              setNewExpiry(event.target.value)
              setFieldError('')
            }}
            className={fieldError ? 'input input--error' : 'input'}
          />
        </FormField>

        <FormField label="New issue date" htmlFor="renew_issue_date">
          <input
            {...fieldProps('renew_issue_date')}
            id="renew_issue_date"
            type="date"
            value={issueDate}
            onChange={(event) => setIssueDate(event.target.value)}
          />
        </FormField>

        <FormField label="Note (optional)" htmlFor="renew_note">
          <input
            {...fieldProps('renew_note')}
            id="renew_note"
            type="text"
            placeholder="e.g. Renewed at the regional office"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            maxLength={1000}
          />
        </FormField>
      </form>
    </Modal>
  )
}

function todayStr() {
  const offset = new Date().getTimezoneOffset()
  return new Date(Date.now() - offset * 60000).toISOString().slice(0, 10)
}