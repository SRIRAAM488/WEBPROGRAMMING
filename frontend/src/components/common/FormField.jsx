/**
 * FormField - one labelled input, with inline validation.
 *
 * Keeping this in one place is what makes error messages appear consistently
 * under every field across all four modules.
 */

import { AlertCircle } from 'lucide-react'

export default function FormField({
  label,
  htmlFor,
  error,
  hint,
  required = false,
  children,
  full = false,
}) {
  return (
    <div className={`form-field${full ? ' form-field--full' : ''}`}>
      {label ? (
        <label className="form-label" htmlFor={htmlFor}>
          {label}
          {required ? (
            <span className="form-label__req" aria-hidden="true">
              *
            </span>
          ) : null}
        </label>
      ) : null}

      {children}

      {error ? (
        <span className="form-error" id={htmlFor ? `${htmlFor}-error` : undefined} role="alert">
          <AlertCircle size={12} aria-hidden="true" />
          {error}
        </span>
      ) : hint ? (
        <span className="form-hint">{hint}</span>
      ) : null}
    </div>
  )
}

/** Build the props an input needs to show its error state correctly. */
export function fieldProps(name, errors = {}) {
  return {
    name,
    'aria-invalid': errors[name] ? 'true' : undefined,
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    className: `input${errors[name] ? ' input--error' : ''}`,
  }
}

/** The same, for <select> and <textarea> elements. */
export function selectProps(name, errors = {}) {
  return {
    name,
    'aria-invalid': errors[name] ? 'true' : undefined,
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    className: `select${errors[name] ? ' select--error' : ''}`,
  }
}

export function textareaProps(name, errors = {}) {
  return {
    name,
    'aria-invalid': errors[name] ? 'true' : undefined,
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    className: `textarea${errors[name] ? ' textarea--error' : ''}`,
  }
}

/** A whole-form validation banner, shown when the server rejects something. */
export function FormErrorBanner({ message, fields }) {
  if (!message) return null
  const count = fields ? Object.keys(fields).length : 0

  return (
    <div className="alert alert--danger" role="alert">
      <AlertCircle size={16} aria-hidden="true" />
      <div>
        <strong>{message}</strong>
        {count > 1 ? (
          <div style={{ marginTop: 2, fontSize: 'var(--fs-xs)' }}>
            {count} fields need attention. Check the highlighted inputs below.
          </div>
        ) : null}
      </div>
    </div>
  )
}