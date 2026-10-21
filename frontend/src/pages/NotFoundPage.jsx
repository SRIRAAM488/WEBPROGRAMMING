/** NotFoundPage - a friendly 404 for unknown routes. */

import { Link } from 'react-router-dom'
import { ArrowLeft, Compass, Home } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '58vh' }}>
      <div className="stack stack--lg" style={{ alignItems: 'center', textAlign: 'center', maxWidth: 460 }}>
        <div
          className="page-head__icon"
          style={{ background: 'var(--primary-soft)', color: 'var(--primary)', width: 64, height: 64 }}
        >
          <Compass size={30} />
        </div>

        <div>
          <h1 style={{ fontSize: 'var(--fs-3xl)', letterSpacing: '-0.03em' }}>Page not found</h1>
          <p className="page-head__desc" style={{ marginTop: 6 }}>
            That page does not exist in DailyFlow. It may have been moved, or the link might
            have a typo in it.
          </p>
        </div>

        <div className="row" style={{ gap: 'var(--sp-2)', flexWrap: 'wrap', justifyContent: 'center' }}>
          <Link to="/" className="btn btn--primary">
            <Home size={16} />
            Go to dashboard
          </Link>
          <button type="button" className="btn btn--secondary" onClick={() => window.history.back()}>
            <ArrowLeft size={16} />
            Go back
          </button>
        </div>

        <div className="card" style={{ width: '100%', textAlign: 'left' }}>
          <div className="card__body">
            <div className="form-label" style={{ marginBottom: 8 }}>
              Or jump straight to a module
            </div>
            <div className="chips">
              {[
                { to: '/bills', label: 'BillBell' },
                { to: '/documents', label: 'DateGuard' },
                { to: '/medications', label: 'DoseNote' },
                { to: '/hydration', label: 'AquaHabit' },
                { to: '/reminders', label: 'Reminders' },
                { to: '/settings', label: 'Settings' },
              ].map((item) => (
                <Link key={item.to} to={item.to} className="chip">
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}