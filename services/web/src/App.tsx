import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/shared/context/AuthContext'
import { Shell } from '@/shell/Shell'
import { Dashboard } from '@/dashboard/Dashboard'
import { LoginPage } from '@/shell/LoginPage'
import { ActivatePage } from '@/shell/ActivatePage'

const Reports            = lazy(() => import('@/modules/reports/Reports').then((m) => ({ default: m.Reports })))
const Crud               = lazy(() => import('@/modules/crud/Crud').then((m) => ({ default: m.Crud })))
const UserManagement     = lazy(() => import('@/modules/crud/users/UserManagement').then((m) => ({ default: m.UserManagement })))
const HospitalManagement = lazy(() => import('@/modules/crud/hospitals/HospitalManagement').then((m) => ({ default: m.HospitalManagement })))
const HospitalDetail     = lazy(() => import('@/modules/crud/hospitals/HospitalDetail').then((m) => ({ default: m.HospitalDetail })))
const SlotManagement         = lazy(() => import('@/modules/crud/slots/SlotManagement').then((m) => ({ default: m.SlotManagement })))
const MedicinereManagement   = lazy(() => import('@/modules/crud/medicineres/MedicinereManagement').then((m) => ({ default: m.MedicinereManagement })))
const Logs               = lazy(() => import('@/modules/logs/Logs').then((m) => ({ default: m.Logs })))

function ModuleFallback() {
  return (
    <div className="flex h-32 items-center justify-center">
      <span className="text-sm text-gray-400">Loading…</span>
    </div>
  )
}

function AppContent() {
  const { user, ready } = useAuth()
  const [params] = useSearchParams()
  const authError = params.get('auth_error')

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <span className="text-sm text-gray-400">Loading…</span>
      </div>
    )
  }

  if (!user) return <LoginPage error={authError} />

  return (
    <Routes>
      <Route path="/" element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="reports/*" element={
          <Suspense fallback={<ModuleFallback />}><Reports /></Suspense>
        } />
        <Route path="users" element={
          <Suspense fallback={<ModuleFallback />}><UserManagement /></Suspense>
        } />
        <Route path="crud/users" element={<Navigate to="/users" replace />} />
        <Route path="hospitals" element={
          <Suspense fallback={<ModuleFallback />}><HospitalManagement /></Suspense>
        } />
        <Route path="hospitals/:uuid" element={
          <Suspense fallback={<ModuleFallback />}><HospitalDetail /></Suspense>
        } />
        <Route path="crud/hospitals" element={<Navigate to="/hospitals" replace />} />
        <Route path="slots" element={
          <Suspense fallback={<ModuleFallback />}><SlotManagement /></Suspense>
        } />
        <Route path="medicineres" element={
          <Suspense fallback={<ModuleFallback />}><MedicinereManagement /></Suspense>
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
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public — no auth required */}
          <Route path="/activate/:uuid" element={<ActivatePage />} />
          {/* Everything else — auth guard inside AppContent */}
          <Route path="/*" element={<AppContent />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
