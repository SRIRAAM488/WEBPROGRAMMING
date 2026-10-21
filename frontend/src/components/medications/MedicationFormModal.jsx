/** MedicationFormModal - add / edit a medication schedule. */

import { useEffect, useState } from 'react'
import { Pill, Plus, X } from 'lucide-react'
import Modal from '../common/Modal'
import FormField, { FormErrorBanner, fieldProps, selectProps, textareaProps } from '../common/FormField'
import { DOSAGE_UNITS, FREQUENCY_PRESETS, MEDICAL_DISCLAIMER } from '../../api/medications'
import { formatTime, todayISO } from '../../utils/format'

const EMPTY_FORM = {
  medication_name: '',
  dosage: '',
  dosage_unit: 'tablet',
  instructions: '',
  start_date: todayISO(),
  end_date: '',
  active: true,
  notes: '',
  scheduled_times: ['08:00'],
}

const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/

export default function MedicationFormModal({ open, onClose, onSubmit, schedule = null }) {
  const isEdit = Boolean(schedule)

  const [form, setForm] = useState(EMPTY_FORM)
  const [newTime, setNewTime] = useState('08:00')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    if (schedule) {
      setForm({
        medication_name: schedule.medication_name || '',
        dosage: schedule.dosage || '',
        dosage_unit: schedule.dosage_unit || 'tablet',
        instructions: schedule.instructions || '',
        start_date: schedule.start_date || todayISO(),
        end_date: schedule.end_date || '',
        active: schedule.active !== false,
        notes: schedule.notes || '',
        scheduled_times:
          schedule.scheduled_times?.map((time) => String(time).slice(0, 5)) || ['08:00'],
      })
    } else {
      setForm({ ...EMPTY_FORM })
    }
    setNewTime('08:00')
    setErrors({})
    setFormError('')
    setSaving(false)
  }, [open, schedule])

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  function addTime() {
    const value = newTime.trim()
    if (!TIME_PATTERN.test(value)) {
      setErrors((current) => ({ ...current, scheduled_times: 'Use 24-hour HH:MM, e.g. 08:00.' }))
      return
    }
    if (form.scheduled_times.includes(value)) {
      setErrors((current) => ({ ...current, scheduled_times: `${value} is already in the schedule.` }))
      return
    }
    if (form.scheduled_times.length >= 12) {
      setErrors((current) => ({ ...current, scheduled_times: 'A schedule cannot have more than 12 times.' }))
      return
    }
    setForm((current) => ({
      ...current,
      scheduled_times: [...current.scheduled_times, value].sort(),
    }))
    setNewTime('08:00')
    setErrors((current) => {
      const next = { ...current }
      delete next.scheduled_times
      return next
    })
  }

  function removeTime(time) {
    setForm((current) => ({
      ...current,
      scheduled_times: current.scheduled_times.filter((value) => value !== time),
    }))
  }

  function applyPreset(times) {
    setForm((current) => ({ ...current, scheduled_times: [...times] }))
    setErrors((current) => {
      const next = { ...current }
      delete next.scheduled_times
      return next
    })
  }

  function validate() {
    const next = {}
    if (!form.medication_name.trim()) next.medication_name = 'Enter the medication name.'
    if (!form.dosage.trim()) next.dosage = 'Enter the dosage, e.g. 1.'
    if (!form.start_date) next.start_date = 'Pick a start date.'
    if (form.end_date && form.start_date && form.end_date < form.start_date) {
      next.end_date = 'The end date must be after the start date.'
    }
    if (!form.scheduled_times.length) {
      next.scheduled_times = 'Add at least one time of day.'
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
        medication_name: form.medication_name.trim(),
        dosage: form.dosage.trim(),
        dosage_unit: form.dosage_unit,
        instructions: form.instructions.trim() || null,
        start_date: form.start_date,
        end_date: form.end_date || null,
        active: form.active,
        notes: form.notes.trim() || null,
        scheduled_times: [...form.scheduled_times].sort(),
      })
    } catch (error) {
      setFormError(error.message || 'Could not save this schedule.')
      if (error.fields) setErrors((current) => ({ ...current, ...error.fields }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title={isEdit ? 'Edit schedule' : 'Add a medication schedule'}
      description="Record the schedule you already follow."
      icon={<Pill size={20} />}
      accent="dosenote"
      footer={
        <>
          <button type="button" className="btn btn--secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="medication-form" className="btn btn--primary" disabled={saving}>
            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add schedule'}
          </button>
        </>
      }
    >
      <form id="medication-form" onSubmit={handleSubmit} className="stack">
        <FormErrorBanner message={formError} fields={errors} />

        <div className="alert alert--neutral">
          <Pill size={15} aria-hidden="true" />
          <span className="text-xs">{MEDICAL_DISCLAIMER}</span>
        </div>

        <div className="form-grid">
          <FormField
            label="Medication name"
            htmlFor="medication_name"
            error={errors.medication_name}
            required
            full
          >
            <input
              {...fieldProps('medication_name', errors)}
              id="medication_name"
              type="text"
              placeholder="e.g. Vitamin D3"
              value={form.medication_name}
              onChange={(event) => update('medication_name', event.target.value)}
              maxLength={120}
            />
          </FormField>

          <FormField label="Dosage" htmlFor="dosage" error={errors.dosage} required>
            <input
              {...fieldProps('dosage', errors)}
              id="dosage"
              type="text"
              placeholder="e.g. 1"
              value={form.dosage}
              onChange={(event) => update('dosage', event.target.value)}
              maxLength={40}
            />
          </FormField>

          <FormField label="Unit" htmlFor="dosage_unit" error={errors.dosage_unit}>
            <select
              {...selectProps('dosage_unit', errors)}
              id="dosage_unit"
              value={form.dosage_unit}
              onChange={(event) => update('dosage_unit', event.target.value)}
            >
              {DOSAGE_UNITS.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </FormField>

          {/* ---------------- Times ---------------- */}
          <FormField
            label="Times of day"
            htmlFor="scheduled_times"
            error={errors.scheduled_times}
            required
            full
            hint="Dose logs are generated for each of these times on every active day."
          >
            <div className="stack stack--sm">
              <div className="chips">
                {FREQUENCY_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    className="chip"
                    onClick={() => applyPreset(preset.times)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              <div className="time-inputs">
                <input
                  id="scheduled_times"
                  type="time"
                  className="input"
                  style={{ width: 130 }}
                  value={newTime}
                  onChange={(event) => setNewTime(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      addTime()
                    }
                  }}
                  aria-label="Add a new time"
                />
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={addTime}
                >
                  <Plus size={14} />
                  Add time
                </button>
              </div>

              {form.scheduled_times.length ? (
                <div className="time-inputs">
                  {form.scheduled_times.map((time) => (
                    <span key={time} className="time-chip">
                      {formatTime(time)}
                      <button
                        type="button"
                        onClick={() => removeTime(time)}
                        aria-label={`Remove time ${time}`}
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </FormField>

          <FormField label="Start date" htmlFor="start_date" error={errors.start_date} required>
            <input
              {...fieldProps('start_date', errors)}
              id="start_date"
              type="date"
              value={form.start_date}
              onChange={(event) => update('start_date', event.target.value)}
            />
          </FormField>

          <FormField
            label="End date"
            htmlFor="end_date"
            error={errors.end_date}
            hint="Leave empty for an ongoing schedule."
          >
            <input
              {...fieldProps('end_date', errors)}
              id="end_date"
              type="date"
              min={form.start_date || undefined}
              value={form.end_date}
              onChange={(event) => update('end_date', event.target.value)}
            />
          </FormField>

          <FormField
            label="Instructions (your own note)"
            htmlFor="instructions"
            error={errors.instructions}
            full
          >
            <input
              {...fieldProps('instructions', errors)}
              id="instructions"
              type="text"
              placeholder="e.g. After food"
              value={form.instructions}
              onChange={(event) => update('instructions', event.target.value)}
              maxLength={500}
            />
          </FormField>

          <FormField label="Notes" htmlFor="med_notes" error={errors.notes} full>
            <textarea
              {...textareaProps('notes', errors)}
              id="med_notes"
              rows={2}
              value={form.notes}
              onChange={(event) => update('notes', event.target.value)}
              maxLength={1000}
            />
          </FormField>

          {isEdit ? (
            <div className="form-field form-field--full">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(event) => update('active', event.target.checked)}
                />
                <span>
                  <strong>Schedule is active</strong>
                  <div className="text-xs text-muted">
                    Turn this off instead of deleting, so past dose logs are kept.
                  </div>
                </span>
              </label>
            </div>
          ) : null}
        </div>
      </form>
    </Modal>
  )
}