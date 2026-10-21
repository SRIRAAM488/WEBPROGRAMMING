/**
 * App - routing.
 *
 * Every required route lives here. The catch-all `*` path renders the friendly
 * 404 page, so an unknown URL never shows a blank screen.
 *
 * Refreshing a nested route such as /hydration works because Vite's dev server
 * falls back to index.html for any path.
 */

import { BrowserRouter, Route, Routes } from 'react-router-dom'

import AppLayout from './components/layout/AppLayout'
import { ToastProvider } from './context/ToastContext'
import { SettingsProvider } from './context/SettingsContext'

import DashboardPage from './pages/DashboardPage'
import BillsPage from './pages/BillsPage'
import DocumentsPage from './pages/DocumentsPage'
import MedicationsPage from './pages/MedicationsPage'
import HydrationPage from './pages/HydrationPage'
import RemindersPage from './pages/RemindersPage'
import SettingsPage from './pages/SettingsPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <SettingsProvider>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="bills" element={<BillsPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="medications" element={<MedicationsPage />} />
              <Route path="hydration" element={<HydrationPage />} />
              <Route path="reminders" element={<RemindersPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </SettingsProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}