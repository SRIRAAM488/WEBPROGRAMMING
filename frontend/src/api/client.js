/**
 * Axios instance shared by every API module.
 *
 * Two things happen here that the rest of the app can rely on:
 *
 *  1. **The base URL comes from an environment variable** (`VITE_API_BASE_URL`),
 *     so the same code works against localhost or a deployed backend without
 *     editing any source file. See `.env.example`.
 *
 *  2. **The browser's UTC offset is attached to every request** as the
 *     `X-Client-Utc-Offset` header. The backend uses it to work out what "today"
 *     means on the user's own clock, instead of assuming the server's timezone.
 */

import axios from 'axios'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
).replace(/\/+$/, '')

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

/** Minutes to add to UTC to get local time (e.g. 330 for India, UTC+5:30). */
export function getUtcOffsetMinutes() {
  // getTimezoneOffset() returns minutes *behind* UTC, so we flip the sign.
  return -new Date().getTimezoneOffset()
}

client.interceptors.request.use((config) => {
  config.headers['X-Client-Utc-Offset'] = String(getUtcOffsetMinutes())
  return config
})

/**
 * Turn any Axios failure into a plain, readable Error.
 * Components can then do `err.message` without digging through Axios internals.
 */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(
        new Error('The request took too long. Please try again.')
      )
    }

    if (!error.response) {
      return Promise.reject(
        new Error(
          `Cannot reach the DailyFlow API at ${API_BASE_URL}. ` +
            'Is the backend running? Start it with: uvicorn app.main:app --reload'
        )
      )
    }

    const { status, data } = error.response

    // Validation errors carry a `fields` map keyed by field name, which the
    // forms render directly under each input.
    if (status === 422 && data && data.fields) {
      const error_ = new Error(data.detail || 'Please correct the highlighted fields.')
      error_.fields = data.fields
      error_.status = status
      return Promise.reject(error_)
    }

    const message =
      (data && (data.detail || data.error)) || `Request failed (${status})`
    const normalised = new Error(
      typeof message === 'string' ? message : 'Request failed.'
    )
    normalised.status = status
    return Promise.reject(normalised)
  }
)

/**
 * Pull a human-readable message out of any error object.
 * Used by every page's error state.
 */
export function getErrorMessage(error, fallback = 'Something went wrong.') {
  if (!error) return fallback
  if (typeof error === 'string') return error
  return error.message || fallback
}

/** Pull the per-field validation map out of an error (may be undefined). */
export function getFieldErrors(error) {
  return (error && error.fields) || {}
}

export default client