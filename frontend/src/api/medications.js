/**
 * DoseNote API calls.
 *
 * DoseNote records the schedule you entered. It is not medical advice and does
 * not recommend medications or doses.
 */

import client from './client'

/** GET /api/medications */
export function fetchSchedules(params = {}) {
  return client.get('/api/medications', { params }).then((res) => res.data)
}

/** GET /api/medications/today */
export function fetchTodayDoses() {
  return client.get('/api/medications/today').then((res) => res.data)
}

/** GET /api/medications/history */
export function fetchDoseHistory(params = {}) {
  return client.get('/api/medications/history', { params }).then((res) => res.data)
}

/** GET /api/medications/adherence */
export function fetchAdherence(days = 7) {
  return client
    .get('/api/medications/adherence', { params: { days } })
    .then((res) => res.data)
}

/** GET /api/medications/{id} */
export function fetchSchedule(id) {
  return client.get(`/api/medications/${id}`).then((res) => res.data)
}

/** POST /api/medications */
export function createSchedule(payload) {
  return client.post('/api/medications', payload).then((res) => res.data)
}

/** PATCH /api/medications/{id} */
export function updateSchedule(id, payload) {
  return client.patch(`/api/medications/${id}`, payload).then((res) => res.data)
}

/** DELETE /api/medications/{id} */
export function deleteSchedule(id) {
  return client.delete(`/api/medications/${id}`).then((res) => res.data)
}

/** POST /api/medications/{id}/doses - 409 if that dose is already logged. */
export function createDoseLog(scheduleId, payload) {
  return client
    .post(`/api/medications/${scheduleId}/doses`, payload)
    .then((res) => res.data)
}

/** PATCH /api/doses/{id} - mark taken / skipped / back to pending. */
export function updateDoseLog(doseId, payload) {
  return client.patch(`/api/doses/${doseId}`, payload).then((res) => res.data)
}

/** DELETE /api/doses/{id} */
export function deleteDoseLog(doseId) {
  return client.delete(`/api/doses/${doseId}`).then((res) => res.data)
}

export const DOSE_STATUSES = [
  { value: 'pending', label: 'Pending' },
  { value: 'taken', label: 'Taken' },
  { value: 'skipped', label: 'Skipped' },
]

export const DOSAGE_UNITS = [
  'tablet',
  'tablets',
  'capsule',
  'capsules',
  'mg',
  'g',
  'ml',
  'drop',
  'drops',
  'IU',
  'unit',
]

/** Frequent presets so the common case is one click instead of typing. */
export const FREQUENCY_PRESETS = [
  { value: 'once', label: 'Once daily', times: ['08:00'] },
  { value: 'twice', label: 'Twice daily', times: ['08:00', '20:00'] },
  { value: 'thrice', label: 'Three times daily', times: ['08:00', '14:00', '20:00'] },
  { value: 'custom', label: 'Custom times', times: [] },
]

export const MEDICAL_DISCLAIMER =
  'DoseNote records the schedule you entered. It is not medical advice and does not tell you to change any prescribed medication. Talk to a doctor or pharmacist about your medication.'