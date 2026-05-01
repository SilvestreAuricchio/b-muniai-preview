import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/shared/context/AuthContext'
import { Shell } from '@/shell/Shell'
import { Dashboard } from '@/dashboard/Dashboard'

const Reports = lazy(() => import('@/modules/reports/Reports').then((m) => ({ default: m.Reports })))
const Crud    = lazy(() => import('@/modules/crud/Crud').then((m) => ({ default: m.Crud })))
const Logs    = lazy(() => import('@/modules/logs/Logs').then((m) => ({ default: m.Logs })))

function ModuleFallback() {
  return (
    <div className="flex h-32 items-center justify-center">
      <span className="text-sm text-gray-400">Loading…</span>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Dashboard />} />
            <Route path="reports/*" element={
              <Suspense fallback={<ModuleFallback />}><Reports /></Suspense>
            } />
            <Route path="crud/:entity?" element={
              <Suspense fallback={<ModuleFallback />}><Crud /></Suspense>
            } />
            <Route path="logs" element={
              <Suspense fallback={<ModuleFallback />}><Logs /></Suspense>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
