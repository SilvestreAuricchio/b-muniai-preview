import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Header } from '@/shell/Header'
import { InsightCard } from './InsightCard'
import { useAuth } from '@/shared/context/AuthContext'
import { RedCross } from '@/shared/components/RedCross'
import { api } from '@/shared/api'
import type { UserRow } from '@/modules/crud/users/UserManagement'

interface Stats {
  total:    number
  pending:  number
  active:   number
  inactive: number
}

function useUserStats() {
  const [stats,   setStats]   = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<UserRow[]>('/users')
      .then((users) => setStats({
        total:    users.length,
        pending:  users.filter((u) => u.status === 'pending').length,
        active:   users.filter((u) => u.status === 'active').length,
        inactive: users.filter((u) => u.status === 'inactive').length,
      }))
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [])

  return { stats, loading }
}

function val(v: number | null | undefined, loading: boolean) {
  if (loading) return '…'
  if (v == null) return '—'
  return v
}

export function Dashboard() {
  const { user }           = useAuth()
  const { stats, loading } = useUserStats()

  const saCards = [
    { label: 'Total Users',        value: val(stats?.total,   loading), detail: 'Registered in the system', accent: false, icon: '⊟' },
    { label: 'Active Users',       value: val(stats?.active,  loading), detail: 'Verified and operational',  accent: true,  icon: '✚' },
    { label: 'Pending Invitations',value: val(stats?.pending, loading), detail: 'Awaiting OTP activation',   accent: false, icon: '⊙' },
    { label: 'Hospitals',          value: '—',                          detail: 'Not yet implemented',       accent: false, icon: '⊞' },
    { label: 'Open Slots',         value: '—',                          detail: 'Not yet implemented',       accent: true,  icon: '▣' },
    { label: 'Audit Events (24h)', value: '—',                          detail: 'Not yet implemented',       accent: false, icon: '≡' },
  ]

  const schedulerCards = [
    { label: 'My Hospitals',  value: '—', detail: 'Not yet implemented', accent: false, icon: '⊞' },
    { label: 'Medicineres',   value: '—', detail: 'Not yet implemented', accent: true,  icon: '✚' },
    { label: 'Open Slots',    value: '—', detail: 'Not yet implemented', accent: true,  icon: '▣' },
    { label: 'Filled Rate',   value: '—', detail: 'Not yet implemented', accent: false, icon: '◈' },
  ]

  const medicinerCards = [
    { label: 'My Slots',         value: '—',       detail: 'Not yet implemented',      accent: true,  icon: '▣' },
    { label: 'Hours This Month', value: '—',        detail: 'Not yet implemented',      accent: false, icon: '◷' },
    { label: 'Next Shift',       value: '—',        detail: 'Not yet implemented',      accent: true,  icon: '✚' },
  ]

  const cardsByRole = {
    'SA-root':   saCards,
    'Scheduler': schedulerCards,
    'Mediciner': medicinerCards,
  }

  const cards = cardsByRole[user?.role ?? 'SA-root']

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dashboard"
        subtitle={`Welcome back, ${user?.name ?? '—'}`}
      />

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map((c) => (
            <InsightCard key={c.label} {...c} />
          ))}
        </div>

        <div className="mt-8">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
            Quick Actions
          </p>
          <div className="flex flex-wrap gap-3">
            {user?.role === 'SA-root' && (
              <>
                <QuickAction label="Invite User"    to="/crud/users" />
                <QuickAction label="View Audit Log" to="/logs" />
              </>
            )}
            {user?.role === 'Scheduler' && (
              <QuickAction label="Manage Users" to="/crud/users" />
            )}
            {user?.role === 'Mediciner' && (
              <QuickAction label="View My Slots" to="/crud/slots" />
            )}
          </div>
        </div>

        <div className="mt-12 flex items-center gap-3 text-gray-200 select-none">
          <RedCross size={36} />
          <span className="text-2xl font-bold tracking-tight">
            Muni<span className="text-gray-300">AI</span>
          </span>
        </div>
      </div>
    </div>
  )
}

function QuickAction({ label, to }: { label: string; to: string }) {
  return (
    <Link
      to={to}
      className="btn-ghost border border-gray-200 text-gray-700 hover:border-brand-200 hover:text-brand-700 hover:bg-brand-50"
    >
      {label}
    </Link>
  )
}
