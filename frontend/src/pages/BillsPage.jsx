/** BillsPage - the BillBell module. */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlarmClock,
  ArrowDownUp,
  CheckCircle2,
  Clock3,
  Pencil,
  Plus,
  Receipt,
  RotateCcw,
  Trash2,
  Wallet,
} from 'lucide-react'

import Toolbar, { FilterSelect } from '../components/common/Toolbar'
import StatusBadge from '../components/common/StatusBadge'
import EmptyState, { ErrorState } from '../components/common/EmptyState'
import { TableSkeleton } from '../components/common/LoadingSkeleton'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { StatTile } from '../components/common/Progress'
import BillFormModal from '../components/bills/BillFormModal'
import PayBillModal from '../components/bills/PayBillModal'

import {
  BILL_CATEGORIES,
  BILL_STATUSES,
  createBill,
  deleteBill,
  fetchBillSummary,
  fetchBills,
  payBill,
  unpayBill,
  updateBill,
} from '../api/bills'
import { getErrorMessage } from '../api/client'
import useDebounced from '../hooks/useDebounced'
import { useSettings } from '../context/SettingsContext'
import { useToast } from '../context/ToastContext'
import { formatCurrency, formatDate, formatDaysRemaining } from '../utils/format'

const PAGE_SIZE = 25

export default function BillsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { currency: defaultCurrency, refreshReminders } = useSettings()

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')
  const [sortBy, setSortBy] = useState('due_date')
  const [sortOrder, setSortOrder] = useState('asc')
  const [page, setPage] = useState(1)

  const [bills, setBills] = useState([])
  const [summary, setSummary] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [payTarget, setPayTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const debouncedSearch = useDebounced(search, 320)
  const highlightId = searchParams.get('bill')

  // Open the add form when arriving from a dashboard quick action.
  useEffect(() => {
    if (searchParams.get('action') === 'add') {
      setEditing(null)
      setFormOpen(true)
      searchParams.delete('action')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const load = useCallback(async () => {
    try {
      setError(null)
      const [list, billSummary] = await Promise.all([
        fetchBills({
          search: debouncedSearch || undefined,
          category,
          status,
          sort_by: sortBy,
          sort_order: sortOrder,
          page,
          page_size: PAGE_SIZE,
        }),
        fetchBillSummary(),
      ])
      setBills(list.items)
      setTotal(list.total)
      setSummary(billSummary)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load your bills.'))
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, category, status, sortBy, sortOrder, page])

  useEffect(() => {
    load()
  }, [load])

  // Back to page 1 whenever a filter changes.
  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, category, status, sortBy, sortOrder])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const displayCurrency = summary?.currency || defaultCurrency

  const filterCounts = useMemo(() => {
    if (!summary) return undefined
    return {
      unpaid: summary.unpaid_count,
      paid: summary.paid_count,
      overdue: summary.overdue_count,
    }
  }, [summary])

  // ---- actions -------------------------------------------------------------

  async function handleCreate(payload) {
    const created = await createBill(payload)
    toast.success(`Added "${created.bill_name}".`)
    setFormOpen(false)
    await load()
    refreshReminders()
  }

  async function handleUpdate(payload) {
    const updated = await updateBill(editing.id, payload)
    toast.success(`Updated "${updated.bill_name}".`)
    setFormOpen(false)
    setEditing(null)
    await load()
    refreshReminders()
  }

  async function handlePay(payload) {
    const updated = await payBill(payTarget.id, payload)
    toast.success(
      payload.mark_next_cycle
        ? `Paid "${updated.bill_name}" and created the next cycle.`
        : `Marked "${updated.bill_name}" as paid.`
    )
    setPayTarget(null)
    await load()
    refreshReminders()
  }

  async function handleUnpay(bill) {
    try {
      await unpayBill(bill.id)
      toast.success(`"${bill.bill_name}" moved back to unpaid.`)
      await load()
      refreshReminders()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteBill(deleteTarget.id)
      toast.success(`Deleted "${deleteTarget.bill_name}".`)
      setDeleteTarget(null)
      await load()
      refreshReminders()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  // ---- render --------------------------------------------------------------

  return (
    <>
      <div className="page-head">
        <div className="page-head__icon" style={{ background: 'var(--billbell-soft)', color: 'var(--billbell)' }}>
          <Receipt size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">BillBell</h1>
          <p className="page-head__desc">
            Track bills, due dates, amounts and payment status.
          </p>
        </div>
        <div className="page-head__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus size={16} />
            Add bill
          </button>
        </div>
      </div>

      {/* Totals straight from the database */}
      {summary ? (
        <div className="grid grid--summary">
          <StatTile
            label="Outstanding"
            value={formatCurrency(summary.total_unpaid_amount, displayCurrency, { decimals: 0 })}
            tone="billbell"
            icon={<Wallet size={12} />}
          />
          <StatTile
            label="Unpaid bills"
            value={summary.unpaid_count}
            icon={<Clock3 size={12} />}
          />
          <StatTile
            label="Overdue"
            value={summary.overdue_count}
            tone={summary.overdue_count > 0 ? 'danger' : 'success'}
            icon={<AlarmClock size={12} />}
          />
          <StatTile
            label="Paid this month"
            value={formatCurrency(summary.total_paid_this_month, displayCurrency, { decimals: 0 })}
            tone="success"
            icon={<CheckCircle2 size={12} />}
          />
        </div>
      ) : null}

      <Toolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search by bill name or provider…"
      >
        <FilterSelect
          label="Filter by category"
          value={category}
          onChange={setCategory}
          options={BILL_CATEGORIES}
          allLabel="All categories"
        />
        <FilterSelect
          label="Filter by status"
          value={status}
          onChange={setStatus}
          options={BILL_STATUSES}
          allLabel="All statuses"
        />
        <select
          className="select toolbar__select"
          value={`${sortBy}:${sortOrder}`}
          onChange={(event) => {
            const [field, order] = event.target.value.split(':')
            setSortBy(field)
            setSortOrder(order)
          }}
          aria-label="Sort bills"
        >
          <option value="due_date:asc">Due date (soonest)</option>
          <option value="due_date:desc">Due date (latest)</option>
          <option value="amount:desc">Amount (high to low)</option>
          <option value="amount:asc">Amount (low to high)</option>
          <option value="bill_name:asc">Name (A to Z)</option>
          <option value="bill_name:desc">Name (Z to A)</option>
        </select>
      </Toolbar>

      <section className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">
              {loading ? 'Loading bills…' : `${total} bill${total === 1 ? '' : 's'}`}
            </h2>
            {summary?.next_due_bill_name ? (
              <p className="card__subtitle">
                Next due: {summary.next_due_bill_name} on {formatDate(summary.next_due_date)}
              </p>
            ) : null}
          </div>
          {filterCounts ? (
            <div className="card__actions">
              <span className="badge badge--warning">
                {summary.unpaid_count} unpaid
              </span>
              {summary.overdue_count > 0 ? (
                <span className="badge badge--danger">{summary.overdue_count} overdue</span>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="card__body card__body--tight">
          {loading ? (
            <TableSkeleton rows={6} columns={5} />
          ) : error ? (
            <ErrorState message={error} onRetry={load} />
          ) : bills.length === 0 ? (
            <EmptyState
              icon={<Receipt size={26} />}
              title={
                search || category !== 'all' || status !== 'all'
                  ? 'No bills match your filters'
                  : 'No bills yet'
              }
              description={
                search || category !== 'all' || status !== 'all'
                  ? 'Try a different search term or clear the filters.'
                  : 'Add your first bill and DailyFlow will remind you before it is due.'
              }
              action={
                search || category !== 'all' || status !== 'all' ? (
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={() => {
                      setSearch('')
                      setCategory('all')
                      setStatus('all')
                    }}
                  >
                    Clear filters
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => {
                      setEditing(null)
                      setFormOpen(true)
                    }}
                  >
                    <Plus size={14} />
                    Add your first bill
                  </button>
                )
              }
            />
          ) : (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Bill</th>
                      <th>Category</th>
                      <th>Due</th>
                      <th className="table__num">Amount</th>
                      <th>Status</th>
                      <th className="table__actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bills.map((bill) => (
                      <tr
                        key={bill.id}
                        className={
                          String(bill.id) === highlightId
                            ? 'is-selected'
                            : bill.status === 'overdue'
                              ? 'is-overdue'
                              : ''
                        }
                      >
                        <td data-label="Bill">
                          <div className="cell-primary">{bill.bill_name}</div>
                          {bill.provider ? <div className="cell-sub">{bill.provider}</div> : null}
                        </td>

                        <td data-label="Category">
                          <span className="cell-muted">{bill.category_label}</span>
                        </td>

                        <td data-label="Due">
                          <div>{formatDate(bill.due_date)}</div>
                          <div className="cell-sub">{formatDaysRemaining(bill.days_until_due)}</div>
                        </td>

                        <td data-label="Amount" className="table__num">
                          <strong>{formatCurrency(bill.amount, bill.currency)}</strong>
                          {bill.recurring ? (
                            <div className="cell-sub">
                              Repeats {bill.recurrence_label.toLowerCase()}
                            </div>
                          ) : null}
                        </td>

                        <td data-label="Status">
                          <StatusBadge status={bill.status} label={bill.status_label} />
                          {bill.payment_date ? (
                            <div className="cell-sub">Paid {formatDate(bill.payment_date)}</div>
                          ) : null}
                        </td>

                        <td data-label="Actions" className="table__actions">
                          <span className="row-actions">
                            {bill.status === 'paid' ? (
                              <button
                                type="button"
                                className="icon-action"
                                onClick={() => handleUnpay(bill)}
                                title="Undo payment"
                                aria-label={`Undo payment for ${bill.bill_name}`}
                              >
                                <RotateCcw size={15} />
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="icon-action icon-action--success"
                                onClick={() => setPayTarget(bill)}
                                title="Mark as paid"
                                aria-label={`Mark ${bill.bill_name} as paid`}
                              >
                                <CheckCircle2 size={15} />
                              </button>
                            )}
                            <button
                              type="button"
                              className="icon-action icon-action--primary"
                              onClick={() => {
                                setEditing(bill)
                                setFormOpen(true)
                              }}
                              title="Edit bill"
                              aria-label={`Edit ${bill.bill_name}`}
                            >
                              <Pencil size={15} />
                            </button>
                            <button
                              type="button"
                              className="icon-action icon-action--danger"
                              onClick={() => setDeleteTarget(bill)}
                              title="Delete bill"
                              aria-label={`Delete ${bill.bill_name}`}
                            >
                              <Trash2 size={15} />
                            </button>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {totalPages > 1 ? (
                <div className="card__footer" style={{ justifyContent: 'space-between' }}>
                  <span>
                    Page {page} of {totalPages} · {total} bills
                  </span>
                  <div className="row" style={{ gap: 'var(--sp-2)' }}>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      disabled={page <= 1}
                      onClick={() => setPage((current) => current - 1)}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((current) => current + 1)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </section>

      <BillFormModal
        open={formOpen}
        bill={editing}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={editing ? handleUpdate : handleCreate}
      />

      <PayBillModal
        open={Boolean(payTarget)}
        bill={payTarget}
        onClose={() => setPayTarget(null)}
        onConfirm={handlePay}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        busy={deleting}
        title="Delete this bill?"
        description={`"${deleteTarget?.bill_name}" will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete bill"
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </>
  )
}