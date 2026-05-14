import { useEffect, useState, useCallback, useRef } from 'react'
import { Header } from '@/shell/Header'
import { api } from '@/shared/api'
import { CreateSAModal } from './CreateSAModal'

export type UserStatus = 'pending' | 'pending_approval' | 'active' | 'disabled' | 'inactive'
export type UserRole   = 'SA-root' | 'Scheduler' | 'Mediciner'

export interface InviteCycle {
  invitedAt:       string | null
  otpDispatchedAt: string | null
  otpVerifiedAt:   string | null
  activatedAt:     string | null
}

export interface UserRow {
  uuid:             string
  name:             string
  email:            string
  telephone:        string
  role:             UserRole
  status:           UserStatus
  createdAt:        string | null
  otpDispatchedAt:  string | null
  otpVerifiedAt:    string | null
  activatedAt:      string | null
}

const STATUS_BADGE: Record<UserStatus, string> = {
  pending:          'bg-yellow-100 text-yellow-800',
  pending_approval: 'bg-blue-100   text-blue-800',
  active:           'bg-green-100  text-green-800',
  disabled:         'bg-amber-100  text-amber-700',
  inactive:         'bg-gray-100   text-gray-500',
}

const STATUS_LABEL: Record<UserStatus, string> = {
  pending:          'Pending',
  pending_approval: 'Awaiting approval',
  active:           'Active',
  disabled:         'Disabled',
  inactive:         'Inactive',
}

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ── Inline timeline ────────────────────────────────────────────────────────

interface TimelineStep {
  label:     string
  at:        string | null
  done:      boolean
  cancelled?: boolean
}

function buildSteps(u: UserRow): TimelineStep[] {
  const cancelled = u.status === 'inactive' && !u.otpVerifiedAt
  return [
    { label: 'Invited',          at: u.createdAt,       done: !!u.createdAt },
    { label: 'OTP sent',         at: u.otpDispatchedAt, done: !!u.otpDispatchedAt },
    {
      label:     cancelled ? 'Cancelled' : 'Code verified',
      at:        cancelled ? null : u.otpVerifiedAt,
      done:      cancelled ? true : !!u.otpVerifiedAt,
      cancelled: cancelled,
    },
    { label: 'Account activated', at: u.activatedAt, done: !!u.activatedAt },
  ]
}

function MiniTrack({ u }: { u: UserRow }) {
  const steps = buildSteps(u)
  const cancelled = u.status === 'inactive' && !u.otpVerifiedAt
  return (
    <div className="flex items-center gap-1">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center">
          <span
            title={s.label + (s.at ? ': ' + fmt(s.at) : '')}
            className={`h-2.5 w-2.5 rounded-full border ${
              s.cancelled
                ? 'border-red-400 bg-red-400'
                : s.done
                  ? 'border-green-500 bg-green-500'
                  : 'border-gray-300 bg-white'
            }`}
          />
          {i < steps.length - 1 && (
            <span className="mx-0.5 h-px w-3 bg-gray-200" />
          )}
        </div>
      ))}
      {cancelled && (
        <span className="ml-1 text-xs text-red-500">cancelled</span>
      )}
    </div>
  )
}

function CycleSteps({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="relative ml-2 border-l border-gray-200 space-y-0">
      {steps.map((s, i) => (
        <li key={i} className="mb-0 ml-5 pb-4 last:pb-0">
          <span className={`absolute -left-2.5 flex h-5 w-5 items-center justify-center rounded-full ring-4 ring-gray-50 ${
            s.cancelled
              ? 'bg-red-100 text-red-500'
              : s.done
                ? 'bg-green-100 text-green-600'
                : 'bg-gray-100 text-gray-400'
          }`}>
            {s.cancelled ? (
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
                <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
              </svg>
            ) : s.done ? (
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <span className="h-2 w-2 rounded-full bg-gray-300" />
            )}
          </span>
          <div className="flex items-baseline gap-3">
            <span className={`text-sm font-medium ${
              s.cancelled ? 'text-red-600' : s.done ? 'text-gray-900' : 'text-gray-400'
            }`}>{s.label}</span>
            <span className="text-xs text-gray-400">{fmt(s.at)}</span>
          </div>
        </li>
      ))}
    </ol>
  )
}

function buildCycleSteps(c: InviteCycle): TimelineStep[] {
  return [
    { label: 'Invited',           at: c.invitedAt,       done: !!c.invitedAt },
    { label: 'OTP sent',          at: c.otpDispatchedAt, done: !!c.otpDispatchedAt },
    { label: 'Code verified',     at: c.otpVerifiedAt,   done: !!c.otpVerifiedAt },
    { label: 'Account activated', at: c.activatedAt,     done: !!c.activatedAt },
  ]
}

function TimelinePanel({ u, history }: { u: UserRow; history: InviteCycle[] }) {
  const steps = buildSteps(u)
  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 space-y-4">

      {/* ── Previous cycles (oldest → newest) ── */}
      {history.map((cycle, idx) => (
        <div key={idx}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-300">
            Invite cycle {idx + 1} — previous
          </p>
          <div className="opacity-60">
            <CycleSteps steps={buildCycleSteps(cycle)} />
          </div>
          <div className="mt-2 border-t border-dashed border-gray-200" />
        </div>
      ))}

      {/* ── Current cycle ── */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {history.length > 0 ? `Invite cycle ${history.length + 1} — current` : 'Invitation timeline'}
        </p>
        <CycleSteps steps={steps} />
      </div>
    </div>
  )
}

// ── Action menu (⋯) for active / disabled users ────────────────────────────
// Uses position:fixed so the dropdown escapes overflow-hidden card containers.

interface ActionMenuProps {
  u:        UserRow
  onAction: (uuid: string, action: 'disable' | 'enable' | 'deactivate') => Promise<void>
}

function ActionMenu({ u, onAction }: ActionMenuProps) {
  const [open, setOpen]   = useState(false)
  const [pos,  setPos]    = useState<{ top: number; right: number } | null>(null)
  const btnRef  = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  function toggleMenu(e: React.MouseEvent) {
    e.stopPropagation()
    if (!open && btnRef.current) {
      const r = btnRef.current.getBoundingClientRect()
      setPos({ top: r.bottom + 4, right: window.innerWidth - r.right })
    }
    setOpen(v => !v)
  }

  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node) && !btnRef.current?.contains(e.target as Node))
        setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  return (
    <div className="inline-block">
      <button
        ref={btnRef}
        className="rounded p-1.5 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
        onClick={toggleMenu}
        title="Actions"
      >
        <svg viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
          <circle cx="8" cy="3"  r="1.5"/><circle cx="8" cy="8"  r="1.5"/><circle cx="8" cy="13" r="1.5"/>
        </svg>
      </button>

      {open && pos && (
        <div
          ref={menuRef}
          style={{ position: 'fixed', top: pos.top, right: pos.right, zIndex: 9999 }}
          className="w-40 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        >
          {u.status === 'active' && (
            <MenuItem
              label="Disable"
              colour="text-amber-600"
              onClick={() => { setOpen(false); onAction(u.uuid, 'disable') }}
            />
          )}
          {u.status === 'disabled' && (
            <MenuItem
              label="Re-enable"
              colour="text-green-600"
              onClick={() => { setOpen(false); onAction(u.uuid, 'enable') }}
            />
          )}
          <MenuItem
            label="Deactivate…"
            colour="text-red-600"
            onClick={() => { setOpen(false); onAction(u.uuid, 'deactivate') }}
          />
        </div>
      )}
    </div>
  )
}

function MenuItem({ label, colour, onClick }: { label: string; colour: string; onClick: () => void }) {
  return (
    <button
      className={`w-full px-3 py-1.5 text-left text-xs font-medium hover:bg-gray-50 ${colour}`}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 30_000

export function UserManagement() {
  const [users,        setUsers]        = useState<UserRow[]>([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState<string | null>(null)
  const [creating,     setCreating]     = useState(false)
  const [reinviting,   setReinviting]   = useState<UserRow | null>(null)
  const [expanded,     setExpanded]     = useState<Set<string>>(new Set())
  const [historyMap,   setHistoryMap]   = useState<Record<string, InviteCycle[]>>({})
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setUsers(await api.get<UserRow[]>('/users'))
      setLastRefreshed(new Date())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Auto-refresh every 30 s
  useEffect(() => {
    const id = setInterval(load, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [load])

  function toggleExpand(uuid: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(uuid)) {
        next.delete(uuid)
      } else {
        next.add(uuid)
        // Lazy-load invite history the first time a row is expanded
        if (!(uuid in historyMap)) {
          api.get<InviteCycle[]>(`/users/${uuid}/history`)
            .then(records => setHistoryMap(m => ({ ...m, [uuid]: records })))
            .catch(() => setHistoryMap(m => ({ ...m, [uuid]: [] })))
        }
      }
      return next
    })
  }

  async function handleApprove(uuid: string) {
    if (!confirm('Activate this user?')) return
    try { await api.post(`/users/${uuid}/approve`, {}); await load() }
    catch (e: unknown) { alert(e instanceof Error ? e.message : 'Error approving user') }
  }

  async function handleCancel(uuid: string) {
    if (!confirm('Cancel this invitation?')) return
    try { await api.delete(`/users/${uuid}/invitation`); await load() }
    catch (e: unknown) { alert(e instanceof Error ? e.message : 'Error cancelling invitation') }
  }

  async function handleAction(uuid: string, action: 'disable' | 'enable' | 'deactivate') {
    const messages = {
      disable:    'Disable this user? They will not be able to log in.',
      enable:     'Re-enable this user?',
      deactivate: 'Permanently deactivate this user? This cannot be undone without a new invitation.',
    }
    if (!confirm(messages[action])) return
    try {
      await api.post(`/users/${uuid}/${action}`, {})
      await load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : `Error: ${action} failed`)
    }
  }

  return (
    <div>
      <Header title="Users" subtitle="Manage system users and invitations" />

      <div className="p-6 space-y-4">
        <div className="flex items-center justify-end gap-3">
          {lastRefreshed && (
            <span className="text-xs text-gray-400">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          <button
            className="text-xs text-brand-600 hover:underline disabled:opacity-40"
            onClick={load}
            disabled={loading}
          >
            ↻ Refresh
          </button>
          <button className="btn-brand" onClick={() => setCreating(true)}>+ Invite User</button>
        </div>

        {error && (
          <div className="card border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        <div className="card overflow-hidden p-0">
          {loading ? (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">Loading…</div>
          ) : users.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">No users yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="w-6 px-3 py-3" />
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Progress</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {users.map((u) => (
                  <>
                    <tr
                      key={u.uuid}
                      className="cursor-pointer hover:bg-gray-50/50"
                      onClick={() => toggleExpand(u.uuid)}
                    >
                      <td className="px-3 py-3 text-gray-300">
                        <svg
                          className={`h-3.5 w-3.5 transition-transform ${expanded.has(u.uuid) ? 'rotate-90' : ''}`}
                          viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5"
                        >
                          <path d="M4 2l4 4-4 4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">{u.name}</td>
                      <td className="px-4 py-3 text-gray-500">{u.email}</td>
                      <td className="px-4 py-3 text-gray-500">{u.role}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[u.status]}`}>
                          {STATUS_LABEL[u.status]}
                        </span>
                      </td>
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        <MiniTrack u={u} />
                      </td>
                      <td className="px-4 py-3 space-x-2" onClick={e => e.stopPropagation()}>
                        {/* Pending-approval: approve button */}
                        {u.status === 'pending_approval' && (
                          <button
                            className="text-xs font-medium text-brand-600 hover:underline"
                            onClick={() => handleApprove(u.uuid)}
                          >
                            Approve
                          </button>
                        )}
                        {/* Pending / pending_approval: cancel button */}
                        {(u.status === 'pending' || u.status === 'pending_approval') && (
                          <button
                            className="text-xs text-gray-400 hover:text-red-600 hover:underline"
                            onClick={() => handleCancel(u.uuid)}
                          >
                            Cancel
                          </button>
                        )}
                        {/* Active / disabled: action menu */}
                        {(u.status === 'active' || u.status === 'disabled') && (
                          <ActionMenu u={u} onAction={handleAction} />
                        )}
                        {/* Inactive: reinvite */}
                        {u.status === 'inactive' && (
                          <button
                            className="text-xs font-medium text-brand-600 hover:underline"
                            onClick={() => setReinviting(u)}
                          >
                            Reinvite
                          </button>
                        )}
                      </td>
                    </tr>

                    {expanded.has(u.uuid) && (
                      <tr key={`${u.uuid}-timeline`}>
                        <td colSpan={7} className="p-0">
                          <TimelinePanel u={u} history={historyMap[u.uuid] ?? []} />
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {(creating || reinviting) && (
        <CreateSAModal
          initialData={reinviting ? {
            name:      reinviting.name,
            email:     reinviting.email,
            telephone: reinviting.telephone,
            role:      reinviting.role,
          } : undefined}
          onClose={() => { setCreating(false); setReinviting(null) }}
          onCreated={() => { setCreating(false); setReinviting(null); load() }}
        />
      )}
    </div>
  )
}
