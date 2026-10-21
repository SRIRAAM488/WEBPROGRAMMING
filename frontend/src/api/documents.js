/** DateGuard API calls. */

import client from './client'

/** GET /api/documents */
export function fetchDocuments(params = {}) {
  return client.get('/api/documents', { params }).then((res) => res.data)
}

/** GET /api/documents/summary */
export function fetchDocumentSummary() {
  return client.get('/api/documents/summary').then((res) => res.data)
}

/** GET /api/documents/expiring */
export function fetchExpiringDocuments(withinDays = 30) {
  return client
    .get('/api/documents/expiring', { params: { within_days: withinDays } })
    .then((res) => res.data)
}

/** GET /api/documents/{id} - returns the real number + renewal history. */
export function fetchDocument(id) {
  return client.get(`/api/documents/${id}`).then((res) => res.data)
}

/** POST /api/documents */
export function createDocument(payload) {
  return client.post('/api/documents', payload).then((res) => res.data)
}

/** PATCH /api/documents/{id} */
export function updateDocument(id, payload) {
  return client.patch(`/api/documents/${id}`, payload).then((res) => res.data)
}

/** POST /api/documents/{id}/renew */
export function renewDocument(id, payload) {
  return client.post(`/api/documents/${id}/renew`, payload).then((res) => res.data)
}

/** DELETE /api/documents/{id} */
export function deleteDocument(id) {
  return client.delete(`/api/documents/${id}`).then((res) => res.data)
}

export const DOCUMENT_TYPES = [
  { value: 'driving_licence', label: 'Driving Licence' },
  { value: 'passport', label: 'Passport' },
  { value: 'aadhaar', label: 'Aadhaar' },
  { value: 'pan', label: 'PAN' },
  { value: 'vehicle_insurance', label: 'Vehicle Insurance' },
  { value: 'health_insurance', label: 'Health Insurance' },
  { value: 'certificate', label: 'Certificate' },
  { value: 'warranty', label: 'Warranty' },
  { value: 'other', label: 'Other' },
]

export const DOCUMENT_STATUSES = [
  { value: 'all', label: 'All statuses' },
  { value: 'expired', label: 'Expired' },
  { value: 'expiring_soon', label: 'Expiring soon' },
  { value: 'valid', label: 'Valid' },
]

/** Reminder lead-time presets for the "remind me before" field. */
export const REMINDER_OPTIONS = [
  { value: 7, label: '7 days before' },
  { value: 15, label: '15 days before' },
  { value: 30, label: '30 days before' },
  { value: 60, label: '60 days before' },
  { value: 90, label: '90 days before' },
]