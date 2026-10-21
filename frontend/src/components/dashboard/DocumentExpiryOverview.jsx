/**
 * DocumentExpiryOverview - documents that need attention soon.
 */

import { Link } from 'react-router-dom'
import { CalendarClock, FileText } from 'lucide-react'
import { ExpiryChip } from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { formatDate } from '../../utils/format'

export default function DocumentExpiryOverview({ documents = [], loading = false, limit = 5 }) {
  if (loading) {
    return (
      <div className="stack stack--sm" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="skeleton" style={{ height: 48 }} />
        ))}
      </div>
    )
  }

  if (!documents.length) {
    return (
      <EmptyState
        compact
        icon={<CalendarClock size={24} />}
        title="Nothing expiring soon"
        description="Add the documents you need to remember and DailyFlow will warn you before they expire."
        action={
          <Link to="/documents" className="btn btn--soft btn--sm">
            Track a document
          </Link>
        }
      />
    )
  }

  return (
    <div className="item-list">
      {documents.slice(0, limit).map((doc) => (
        <Link
          key={doc.id}
          to={`/documents?document=${doc.id}`}
          className="item-row"
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          <span
            className="item-row__icon"
            style={{
              background: doc.is_expired ? 'var(--danger-soft)' : 'var(--dateguard-soft)',
              color: doc.is_expired ? 'var(--danger)' : 'var(--dateguard)',
            }}
          >
            <FileText size={17} />
          </span>

          <span className="item-row__body">
            <span className="item-row__title">
              {doc.document_name}
              <ExpiryChip daysRemaining={doc.days_remaining} />
            </span>
            <span className="item-row__meta">
              <span>{doc.document_type_label}</span>
              <span className="dot-sep">Expires {formatDate(doc.expiry_date)}</span>
              {doc.masked_document_number ? (
                <span className="dot-sep text-num">{doc.masked_document_number}</span>
              ) : null}
            </span>
          </span>
        </Link>
      ))}
    </div>
  )
}