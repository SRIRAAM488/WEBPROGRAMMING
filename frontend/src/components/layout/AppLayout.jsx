/**
 * AppLayout - the shell every page renders inside.
 *
 * Desktop:  fixed sidebar on the left + scrolling content on the right.
 * Mobile:   a slide-in drawer plus a bottom tab bar.
 */

import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { MobileNavigation, MobileTopbar } from './MobileNavigation'

export default function AppLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()

  // Close the drawer whenever the route changes.
  useEffect(() => {
    setDrawerOpen(false)
  }, [pathname])

  // Lock background scrolling while the drawer covers the screen.
  useEffect(() => {
    if (!drawerOpen) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [drawerOpen])

  // Close on Escape.
  useEffect(() => {
    if (!drawerOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>

      <Sidebar open={drawerOpen} onNavigate={() => setDrawerOpen(false)} />

      {drawerOpen ? (
        <div
          className="scrim"
          onClick={() => setDrawerOpen(false)}
          role="presentation"
          aria-hidden="true"
        />
      ) : null}

      <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <MobileTopbar onOpenDrawer={() => setDrawerOpen(true)} />
        <Topbar />

        <main className="content" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <MobileNavigation />
    </div>
  )
}