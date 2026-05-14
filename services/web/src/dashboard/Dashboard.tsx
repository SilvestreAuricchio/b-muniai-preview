import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Header } from '@/shell/Header'
import { InsightCard } from './InsightCard'
import { useAuth } from '@/shared/context/AuthContext'
import { RedCross } from '@/shared/components/RedCross'
import { api } from '@/shared/api'
import type { UserRow } from '@/modules/crud/users/UserManagement'
import type { HospitalRow } from '@/modules/crud/hospitals/HospitalManagement'

// ── Per-role stat group ──────────────────────────────────────────────────────

interface RoleGroup {
  active:           number
  pending:          number           // awaiting OTP
  pending_approval: number           // awaiting SA approval
  disabled:         number
  inactive:         number
}

interface Stats {
  sa:        RoleGroup
  scheduler: RoleGroup
}

function emptyGroup(): RoleGroup {
  return { active: 0, pending: 0, pending_approval: 0, disabled: 0, inactive: 0 }
}

function useUserStats() {
  const [stats,   setStats]   = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<UserRow[]>('/users')
      .then((users) => {
        const sa        = emptyGroup()
        const scheduler = emptyGroup()

        for (const u of users) {
          const target = u.role === 'SA-root' ? sa : u.role === 'Scheduler' ? scheduler : null
          if (!target) continue
          if      (u.status === 'active')           target.active           += 1
          else if (u.status === 'pending')          target.pending          += 1
          else if (u.status === 'pending_approval') target.pending_approval += 1
          else if (u.status === 'disabled')         target.disabled         += 1
          else if (u.status === 'inactive')         target.inactive         += 1
        }

        setStats({ sa, scheduler })
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [])

  return { stats, loading }
}

// ── Tooltip showing per-status breakdown on hover over "of N total" ──────────

function TotalTooltip({ group, label }: { group: RoleGroup; label: string }) {
  const total = group.active + group.pending + group.pending_approval + group.disabled + group.inactive
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  function show() {
    if (!ref.current) return
    const r = ref.current.getBoundingClientRect()
    setPos({ top: r.top - 8, left: r.left + r.width / 2 })
  }

  return (
    <span
      ref={ref}
      className="inline-flex items-center cursor-default"
      onMouseEnter={show}
      onMouseLeave={() => setPos(null)}
    >
      <span className="text-gray-900 text-2xl font-normal">
        {' '}of{' '}
        <span className="underline decoration-dotted decoration-gray-400">{total}</span>
      </span>

      {pos && (
        <div
          className="pointer-events-none"
          style={{ position: 'fixed', top: pos.top, left: pos.left, transform: 'translate(-50%, -100%)', zIndex: 9999 }}
        >
          <div className="bg-gray-500 text-white text-xs rounded-lg px-3 py-2 shadow-xl mb-1">
            <p className="font-semibold text-white mb-1.5 border-b border-gray-400 pb-1 whitespace-nowrap">{label}</p>
            <div className="space-y-1">
              {([
                ['Active',            group.active],
                ['Awaiting OTP',      group.pending],
                ['Awaiting approval', group.pending_approval],
                ['Disabled',          group.disabled],
                ['Inactive',          group.inactive],
              ] as [string, number][]).map(([lbl, val]) => (
                <div key={lbl} className="flex justify-between gap-6">
                  <span className="text-gray-200 whitespace-nowrap">{lbl}</span>
                  <span className="text-green-300 font-normal">{val}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="w-2 h-2 bg-gray-500 rotate-45 mx-auto -mt-1" />
        </div>
      )}
    </span>
  )
}

// ── Single role column inside the Users card ─────────────────────────────────

function RoleColumn({
  title, group, loading,
}: { title: string; group: RoleGroup | null; loading: boolean }) {
  const waiting = (group?.pending ?? 0) + (group?.pending_approval ?? 0)

  return (
    <div className="flex flex-col gap-1.5 min-w-0 items-center">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide text-center w-full">{title}</p>

      {loading ? (
        <p className="text-sm text-gray-300">…</p>
      ) : !group ? (
        <p className="text-sm text-gray-300">—</p>
      ) : (
        <>
          <p className="text-2xl font-normal text-gray-900 leading-none tabular-nums w-full text-right">
            {group.active}
            <TotalTooltip group={group} label={title} />
          </p>
          <p className="text-xs text-gray-400 mt-0.5 w-full text-right">
            Waiting:{' '}
            <span className={waiting > 0 ? 'text-amber-600 font-semibold' : 'text-gray-400'}>
              {waiting}
            </span>
          </p>
        </>
      )}
    </div>
  )
}

// ── Hospital summary card (SA-root) ──────────────────────────────────────────

function useHospitalStats() {
  const [count,   setCount]   = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    api.get<HospitalRow[]>('/hospitals')
      .then((rows) => setCount(rows.length))
      .catch(() => setCount(null))
      .finally(() => setLoading(false))
  }, [])
  return { count, loading }
}

function HospitalSummaryCard({ count, loading }: { count: number | null; loading: boolean }) {
  return (
    <div className="card flex flex-col gap-4 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-50 text-brand-600">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
                 className="w-5 h-5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
            </svg>
          </span>
          <p className="text-sm font-medium text-gray-600">Hospitals</p>
        </div>
        <Link
          to="/hospitals"
          className="text-xs text-brand-600 hover:text-brand-700 hover:underline font-medium whitespace-nowrap"
        >
          View list →
        </Link>
      </div>

      <div className="h-px bg-gray-100" />

      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Registered</p>
        {loading ? (
          <p className="text-sm text-gray-300">…</p>
        ) : count === null ? (
          <p className="text-sm text-gray-300">—</p>
        ) : (
          <p className="text-2xl font-normal text-gray-900 tabular-nums">{count}</p>
        )}
      </div>
    </div>
  )
}

// ── Hospital scheduler card (Scheduler role) ──────────────────────────────────

function HospitalSchedulerCard() {
  const [hospitals, setHospitals] = useState<HospitalRow[]>([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    api.get<HospitalRow[]>('/hospitals')
      .then(setHospitals)
      .catch(() => setHospitals([]))
      .finally(() => setLoading(false))
  }, [])

  const preview = hospitals.slice(0, 4)

  return (
    <div className="card flex flex-col gap-4 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-50 text-brand-600">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
                 className="w-5 h-5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
            </svg>
          </span>
          <p className="text-sm font-medium text-gray-600">My Hospitals</p>
        </div>
        <Link
          to="/hospitals"
          className="text-xs text-brand-600 hover:text-brand-700 hover:underline font-medium whitespace-nowrap"
        >
          View all →
        </Link>
      </div>

      <div className="h-px bg-gray-100" />

      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Assigned</p>
        {loading ? (
          <p className="text-sm text-gray-300">…</p>
        ) : (
          <>
            <p className="text-2xl font-normal text-gray-900 tabular-nums">{hospitals.length}</p>
            {preview.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {preview.map((h) => (
                  <span
                    key={h.uuid}
                    className="inline-block truncate max-w-[120px] rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
                    title={h.name}
                  >
                    {h.name}
                  </span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Users summary card ────────────────────────────────────────────────────────

function UserSummaryCard({ stats, loading }: { stats: Stats | null; loading: boolean }) {
  return (
    <div className="card flex flex-col gap-4 p-5 hover:shadow-md transition-shadow">

      {/* header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {/* profile icon */}
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-50 text-brand-600">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
                 className="w-5 h-5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
              <path d="M4.5 20.118a7.5 7.5 0 0 1 15 0A17.93 17.93 0 0 1 12 21.75c-2.676 0-5.216-.584-7.5-1.632Z" />
            </svg>
          </span>
          <p className="text-sm font-medium text-gray-600">Users</p>
        </div>

        <Link
          to="/users"
          className="text-xs text-brand-600 hover:text-brand-700 hover:underline font-medium whitespace-nowrap"
        >
          View list →
        </Link>
      </div>

      {/* divider */}
      <div className="h-px bg-gray-100" />

      {/* columns */}
      <div className="grid grid-cols-2 gap-4">
        <RoleColumn title="System Admin" group={stats?.sa        ?? null} loading={loading} />
        <RoleColumn title="Scheduler"    group={stats?.scheduler ?? null} loading={loading} />
      </div>

    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function Dashboard() {
  const { user }                         = useAuth()
  const { stats, loading }               = useUserStats()
  const { count: hospCount, loading: hospLoading } = useHospitalStats()

  const saCards = [
    { label: 'Open Slots',         value: '—', detail: 'Not yet implemented', accent: true,  icon: '▣' },
    { label: 'Audit Events (24h)', value: '—', detail: 'Not yet implemented', accent: false, icon: '≡' },
  ]

  const schedulerCards = [
    { label: 'Medicineres',   value: '—', detail: 'Not yet implemented', accent: true,  icon: '✚' },
    { label: 'Open Slots',    value: '—', detail: 'Not yet implemented', accent: true,  icon: '▣' },
    { label: 'Filled Rate',   value: '—', detail: 'Not yet implemented', accent: false, icon: '◈' },
  ]

  const medicinerCards = [
    { label: 'My Slots',         value: '—', detail: 'Not yet implemented', accent: true,  icon: '▣' },
    { label: 'Hours This Month', value: '—', detail: 'Not yet implemented', accent: false, icon: '◷' },
    { label: 'Next Shift',       value: '—', detail: 'Not yet implemented', accent: true,  icon: '✚' },
  ]

  const cardsByRole: Record<string, typeof saCards> = {
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
          {user?.role === 'SA-root' && (
            <UserSummaryCard stats={stats} loading={loading} />
          )}
          {user?.role === 'SA-root' && (
            <HospitalSummaryCard count={hospCount} loading={hospLoading} />
          )}
          {user?.role === 'Scheduler' && (
            <HospitalSchedulerCard />
          )}
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
                <QuickAction label="Invite User"    to="/users" />
                <QuickAction label="View Audit Log" to="/logs" />
              </>
            )}
            {user?.role === 'Scheduler' && (
              <QuickAction label="Manage Users" to="/users" />
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
