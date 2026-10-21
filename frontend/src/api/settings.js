/** Application settings API calls. */

import client from './client'

/** GET /api/settings */
export function fetchSettings() {
  return client.get('/api/settings').then((res) => res.data)
}

/** PATCH /api/settings */
export function updateSettings(payload) {
  return client.patch('/api/settings', payload).then((res) => res.data)
}

/** GET /api/settings/meta - option lists for the settings form. */
export function fetchSettingsMeta() {
  return client.get('/api/settings/meta').then((res) => res.data)
}

/** GET /api/health */
export function fetchHealth() {
  return client.get('/api/health').then((res) => res.data)
}