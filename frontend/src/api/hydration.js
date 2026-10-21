/** AquaHabit API calls. */

import client from './client'

/** GET /api/hydration/settings */
export function fetchHydrationSettings() {
  return client.get('/api/hydration/settings').then((res) => res.data)
}

/** PATCH /api/hydration/settings */
export function updateHydrationSettings(payload) {
  return client.patch('/api/hydration/settings', payload).then((res) => res.data)
}

/** GET /api/hydration/today */
export function fetchTodayHydration() {
  return client.get('/api/hydration/today').then((res) => res.data)
}

/** GET /api/hydration/weekly */
export function fetchWeeklyHydration(days = 7) {
  return client.get('/api/hydration/weekly', { params: { days } }).then((res) => res.data)
}

/** GET /api/hydration/monthly */
export function fetchMonthlyHydration() {
  return client.get('/api/hydration/monthly').then((res) => res.data)
}

/** GET /api/hydration/history */
export function fetchHydrationHistory(params = {}) {
  return client.get('/api/hydration/history', { params }).then((res) => res.data)
}

/** POST /api/hydration/intake */
export function createIntake(payload) {
  return client.post('/api/hydration/intake', payload).then((res) => res.data)
}

/** PATCH /api/hydration/intake/{id} */
export function updateIntake(id, payload) {
  return client.patch(`/api/hydration/intake/${id}`, payload).then((res) => res.data)
}

/** DELETE /api/hydration/intake/{id} */
export function deleteIntake(id) {
  return client.delete(`/api/hydration/intake/${id}`).then((res) => res.data)
}

/** One-tap serving sizes. */
export const QUICK_ADD_ML = [150, 250, 350, 500]

export const HYDRATION_NOTE =
  'Your goal is a personal preference, not medical advice. Adjust it to whatever suits you.'