/** BillBell API calls. */

import client from './client'

/** GET /api/bills - list with search, filters, sorting and pagination. */
export function fetchBills(params = {}) {
  return client.get('/api/bills', { params }).then((res) => res.data)
}

/** GET /api/bills/summary - totals for the BillBell card. */
export function fetchBillSummary() {
  return client.get('/api/bills/summary').then((res) => res.data)
}

/** GET /api/bills/{id} */
export function fetchBill(id) {
  return client.get(`/api/bills/${id}`).then((res) => res.data)
}

/** POST /api/bills */
export function createBill(payload) {
  return client.post('/api/bills', payload).then((res) => res.data)
}

/** PATCH /api/bills/{id} */
export function updateBill(id, payload) {
  return client.patch(`/api/bills/${id}`, payload).then((res) => res.data)
}

/** POST /api/bills/{id}/pay */
export function payBill(id, payload = {}) {
  return client.post(`/api/bills/${id}/pay`, payload).then((res) => res.data)
}

/** POST /api/bills/{id}/unpay */
export function unpayBill(id) {
  return client.post(`/api/bills/${id}/unpay`, {}).then((res) => res.data)
}

/** DELETE /api/bills/{id} */
export function deleteBill(id) {
  return client.delete(`/api/bills/${id}`).then((res) => res.data)
}

/** Option lists for the BillBell forms. */
export const BILL_CATEGORIES = [
  { value: 'electricity', label: 'Electricity' },
  { value: 'water', label: 'Water' },
  { value: 'internet', label: 'Internet' },
  { value: 'mobile', label: 'Mobile' },
  { value: 'rent', label: 'Rent' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'education', label: 'Education' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'other', label: 'Other' },
]

export const BILL_STATUSES = [
  { value: 'unpaid', label: 'Unpaid' },
  { value: 'paid', label: 'Paid' },
  { value: 'overdue', label: 'Overdue' },
]

export const RECURRENCE_OPTIONS = [
  { value: 'none', label: 'One-time bill' },
  { value: 'weekly', label: 'Every week' },
  { value: 'monthly', label: 'Every month' },
  { value: 'quarterly', label: 'Every 3 months' },
  { value: 'yearly', label: 'Every year' },
  { value: 'yearly_2', label: 'Every 2 years' },
]

export const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'AUD', 'CAD']

export const CURRENCY_SYMBOLS = {
  INR: '₹',
  USD: '$',
  EUR: '€',
  GBP: '£',
  AED: 'AED ',
  SGD: 'S$',
  AUD: 'A$',
  CAD: 'C$',
}