/** DocumentsPage - the DateGuard module. */

import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlarmClock,
  CalendarClock,
  CheckCircle2,
  Eye,
  FileText,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from 'lucide-react'

import Toolbar, { FilterChips, FilterSelect } from '../components/common/Toolbar'
import StatusBadge, { ExpiryChip } from '../components/common/StatusBadge'
import EmptyState, { ErrorState } from '../components/common/EmptyState'
import { TableSkeleton } from '../components/common/LoadingSkeleton'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { StatTile } from '../components/common/Progress'
import DocumentFormModal from '../components/documents/DocumentFormModal'
import RenewDocumentModal from '../components/documents/RenewDocumentModal'

import {
  DOCUMENT_STATUSES,
  DOCUMENT_TYPES,
  createDocument,
  deleteDocument,
  fetchDocumentSummary,
  fetchDocuments,
  renewDocument,
  updateDocument,
} from '../api/documents'
import { getErrorMessage } from '../api/client'
import useDebounced from '../hooks/useDebounced'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../utils/format'

export default function DocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const [search, setSearch] = useState('')
  const [documentType, setDocumentType] = useState('all')
  const [status, setStatus] = useState('all')
  const [sortOrder, setSortOrder] = useState('asc')

  const [documents, setDocuments] = useState([])
  const [summary, setSummary] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [renewTarget, setRenewTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [detail, setDetail] = useState(null)

  const debouncedSearch = useDebounced(search, 320)
  const highlightId = searchParams.get('document')

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
      const [list, docSummary] = await Promise.all([
        fetchDocuments({
          search: debouncedSearch || undefined,
          document_type: documentType,
          status,
          sort_by: 'expiry_date',
          sort_order: sortOrder,
        }),
        fetchDocumentSummary(),
      ])
      setDocuments(list.items)
      setTotal(list.total)
      setSummary(docSummary)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load your documents.'))
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, documentType, status, sortOrder])

  useEffect(() => {
    load()
  }, [load])

  // ---- actions -------------------------------------------------------------

  async function handleCreate(payload) {
    const created = await createDocument(payload)
    toast.success(`Now tracking "${created.document_name}".`)
    setFormOpen(false)
    await load()
  }

  async function handleUpdate(payload) {
    const updated = await updateDocument(editing.id, payload)
    toast.success(`Updated "${updated.document_name}".`)
    setFormOpen(false)
    setEditing(null)
    await load()
  }

  async function handleRenew(payload) {
    const updated = await renewDocument(renewTarget.id, payload)
    toast.success(`"${updated.document_name}" renewed. Previous expiry kept in history.`)
    setRenewTarget(null)
    await load()
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteDocument(deleteTarget.id)
      toast.success(`Deleted "${deleteTarget.document_name}".`)
      setDeleteTarget(null)
      await load()
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
        <div className="page-head__icon" style={{ background: 'var(--dateguard-soft)', color: 'var(--dateguard)' }}>
          <FileText size={23} />
        </div>
        <div className="page-head__text">
          <h1 className="page-head__title">DateGuard</h1>
          <p className="page-head__desc">
            Track important documents and get warned before they expire.
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
            Track a document
          </button>
        </div>
      </div>

      {summary ? (
        <div className="grid grid--summary">
          <StatTile
            label="Active documents"
            value={summary.total_documents}
            icon={<FileText size={12} />}
          />
          <StatTile
            label="Expiring in 7 days"
            value={summary.expiring_in_7_days}
            tone={summary.expiring_in_7_days > 0 ? 'warning' : 'success'}
            icon={<CalendarClock size={12} />}
          />
          <StatTile
            label="Expiring in 30 days"
            value={summary.expiring_in_30_days}
            tone={summary.expiring_in_30_days > 0 ? 'warning' : undefined}
            icon={<AlarmClock size={12} />}
          />
          <StatTile
            label="Already expired"
            value={summary.expired_count}
            tone={summary.expired_count > 0 ? 'danger' : 'success'}
            icon={<ShieldCheck size={12} />}
          />
        </div>
      ) : null}

      <Toolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search by document name or authority…"
      >
        <FilterSelect
          label="Filter by type"
          value={documentType}
          onChange={setDocumentType}
          options={DOCUMENT_TYPES}
          allLabel="All types"
        />
        <select
          className="select toolbar__select"
          value={sortOrder}
          onChange={(event) => setSortOrder(event.target.value)}
          aria-label="Sort documents"
        >
          <option value="asc">Expiry (soonest first)</option>
          <option value="desc">Expiry (latest first)</option>
        </select>
      </Toolbar>

      <div className="card">
        <div className="card__body">
          <FilterChips
            options={DOCUMENT_STATUSES}
            value={status}
            onChange={setStatus}
            counts={
              summary
                ? {
                    all: summary.total_documents,
                    expired: summary.expired_count,
                    expiring_soon: summary.expiring_in_30_days,
                    valid: Math.max(
                      0,
                      summary.total_documents - summary.expired_count - summary.expiring_in_30_days
                    ),
                  }
                : undefined
            }
          />
        </div>
      </div>

      <section className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">
              {loading ? 'Loading documents…' : `${total} document${total === 1 ? '' : 's'}`}
            </h2>
            {summary?.next_expiry_name ? (
              <p className="card__subtitle">
                Next expiry: {summary.next_expiry_name} on {formatDate(summary.next_expiry_date)}
              </p>
            ) : null}
          </div>
        </div>

        <div className="card__body card__body--tight">
          {loading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : error ? (
            <ErrorState message={error} onRetry={load} />
          ) : documents.length === 0 ? (
            <EmptyState
              icon={<FileText size={26} />}
              title={
                search || documentType !== 'all' || status !== 'all'
                  ? 'No documents match your filters'
                  : 'No documents tracked yet'
              }
              description={
                search || documentType !== 'all' || status !== 'all'
                  ? 'Try a different search or clear the filters.'
                  : 'Add a passport, licence or insurance policy and DailyFlow will remind you before it expires.'
              }
              action={
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => {
                    setEditing(null)
                    setFormOpen(true)
                  }}
                >
                  <Plus size={14} />
                  Track a document
                </button>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Type</th>
                    <th>Expiry</th>
                    <th>Remaining</th>
                    <th>Status</th>
                    <th className="table__actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr
                      key={doc.id}
                      className={
                        String(doc.id) === highlightId
                          ? 'is-selected'
                          : doc.is_expired
                            ? 'is-expired'
                            : ''
                      }
                    >
                      <td data-label="Document">
                        <div className="cell-primary">{doc.document_name}</div>
                        {doc.masked_document_number ? (
                          <div className="cell-sub text-num">{doc.masked_document_number}</div>
                        ) : null}
                      </td>

                      <td data-label="Type">
                        <span className="cell-muted">{doc.document_type_label}</span>
                        {doc.issuing_authority ? (
                          <div className="cell-sub">{doc.issuing_authority}</div>
                        ) : null}
                      </td>

                      <td data-label="Expiry">{formatDate(doc.expiry_date)}</td>

                      <td data-label="Remaining">
                        <ExpiryChip daysRemaining={doc.days_remaining} />
                      </td>

                      <td data-label="Status">
                        <StatusBadge
                          status={doc.status}
                          label={doc.status_label}
                          tone={
                            doc.status === 'expired'
                              ? 'danger'
                              : doc.status === 'expiring_soon'
                                ? 'warning'
                                : 'success'
                          }
                        />
                      </td>

                      <td data-label="Actions" className="table__actions">
                        <span className="row-actions">
                          <button
                            type="button"
                            className="icon-action"
                            onClick={() => setDetail(doc)}
                            title="View details"
                            aria-label={`View details of ${doc.document_name}`}
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            type="button"
                            className="icon-action icon-action--success"
                            onClick={() => setRenewTarget(doc)}
                            title="Record a renewal"
                            aria-label={`Record renewal for ${doc.document_name}`}
                          >
                            <RefreshCw size={15} />
                          </button>
                          <button
                            type="button"
                            className="icon-action icon-action--primary"
                            onClick={() => {
                              setEditing(doc)
                              setFormOpen(true)
                            }}
                            title="Edit document"
                            aria-label={`Edit ${doc.document_name}`}
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            type="button"
                            className="icon-action icon-action--danger"
                            onClick={() => setDeleteTarget(doc)}
                            title="Delete document"
                            aria-label={`Delete ${doc.document_name}`}
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
          )}
        </div>
      </section>

      <div className="alert alert--neutral">
        <ShieldCheck size={16} aria-hidden="true" />
        <span className="text-xs">
          Document numbers are stored so you can tell documents apart, but they are masked
          everywhere except the detail view. DailyFlow is a local single-user app - do not put
          real identity documents on a shared machine.
        </span>
      </div>

      <DocumentFormModal
        open={formOpen}
        document={editing}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={editing ? handleUpdate : handleCreate}
      />

      <RenewDocumentModal
        open={Boolean(renewTarget)}
        document={renewTarget}
        onClose={() => setRenewTarget(null)}
        onSubmit={handleRenew}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        busy={deleting}
        title="Delete this document?"
        description={`"${deleteTarget?.document_name}" and its renewal history will be permanently removed.`}
        confirmLabel="Delete document"
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />

      <DocumentDetailDialog document={detail} onClose={() => setDetail(null)} />
    </>
  )
}

/** Detail view - the only place the real document number is shown. */
function DocumentDetailDialog({ document: doc, onClose }) {
  if (!doc) return null

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="modal modal--sm" role="dialog" aria-modal="true" aria-label={doc.document_name}>
        <header className="modal__header">
          <div
            className="modal__icon"
            style={{ background: 'var(--dateguard-soft)', color: 'var(--dateguard)' }}
          >
            <FileText size={20} />
          </div>
          <div style={{ minWidth: 0 }}>
            <h2 className="modal__title">{doc.document_name}</h2>
            <p className="modal__desc">{doc.document_type_label}</p>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="modal__body">
          <dl className="stack stack--sm" style={{ margin: 0 }}>
            <DetailRow label="Expiry date" value={formatDate(doc.expiry_date)} />
            <DetailRow
              label="Remaining"
              value={
                doc.days_remaining < 0
                  ? `Expired ${Math.abs(doc.days_remaining)} days ago`
                  : `${doc.days_remaining} days left`
              }
            />
            <DetailRow
              label="Status"
              value={doc.status_label}
              badge={doc.status}
            />
            {doc.issue_date ? (
              <DetailRow label="Issue date" value={formatDate(doc.issue_date)} />
            ) : null}
            {doc.issuing_authority ? (
              <DetailRow label="Issuing authority" value={doc.issuing_authority} />
            ) : null}
            <DetailRow
              label="Document number"
              value={doc.masked_document_number || 'Not stored'}
            />
            <DetailRow
              label="Remind me"
              value={`${doc.reminder_days_before} days before expiry`}
            />
          </dl>

          {doc.notes ? (
            <div>
              <div className="form-label" style={{ marginBottom: 4 }}>
                Notes
              </div>
              <p className="text-sm text-muted">{doc.notes}</p>
            </div>
          ) : null}
        </div>

        <footer className="modal__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  )
}

function DetailRow({ label, value, badge }) {
  return (
    <div className="row row--between" style={{ gap: 'var(--sp-4)' }}>
      <dt className="text-sm text-muted">{label}</dt>
      <dd style={{ margin: 0, textAlign: 'right' }}>
        {badge ? <StatusBadge status={badge} /> : <span className="text-sm font-semibold">{value}</span>}
      </dd>
    </div>
  )
}