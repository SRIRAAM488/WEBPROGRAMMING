/** Dashboard API calls. */

import client from './client'

/** GET /api/dashboard/summary - powers the four overview cards. */
export function fetchDashboardSummary() {
  return client.get('/api/dashboard/summary').then((res) => res.data)
}

/** GET /api/dashboard/charts - powers every chart on the dashboard. */
export function fetchDashboardCharts() {
  return client.get('/api/dashboard/charts').then((res) => res.data)
}

/** GET /api/dashboard/activity - the recent activity feed. */
export function fetchDashboardActivity(limit = 12) {
  return client
    .get('/api/dashboard/activity', { params: { limit } })
    .then((res) => res.data)
}

/**
 * Fetch all three dashboard payloads in parallel.
 * One call for the page, three requests on the wire.
 */
export function fetchDashboardBundle() {
  return Promise.all([
    fetchDashboardSummary(),
    fetchDashboardCharts(),
    fetchDashboardActivity(),
  ]).then(([summary, charts, activity]) => ({ summary, charts, activity }))
}