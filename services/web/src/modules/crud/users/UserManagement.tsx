import { useEffect, useState, useCallback } from 'react'
import { Header } from '@/shell/Header'
import { api } from '@/shared/api'
import { CreateSAModal } from './CreateSAModal'

export type UserStatus = 'pending' | 'pending_approval' | 'active' | 'inactive'
export type UserRole   = 'SA-root' | 'Scheduler' | 'Mediciner'

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
  inactive:         'bg-gray-100   text-gray-500',
}

const STATUS_LABEL: Record<UserStatus, string> = {
  pending:          'Pending',
  pending_approval: 'Awaiting approval',
  active:           'Active',
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
  const cancelled = u.status === 'inactive'
  return [
    {
      label: 'Invited',
      at:    u.createdAt,
      done:  !!u.createdAt,
    },
    {
      label: 'OTP sent',
      at:    u.otpDispatchedAt,
      done:  !!u.otpDispatchedAt,
    },
    {
      label:     cancelled ? 'Cancelled' : 'Code verified',
      at:        cancelled ? null : u.otpVerifiedAt,
      done:      cancelled ? true : !!u.otpVerifiedAt,
      cancelled: cancelled,
    },
    {
      label: 'Account activated',
      at:    u.activatedAt,
      done:  !!u.activatedAt,
    },
  ]
}

function MiniTrack({ u }: { u: UserRow }) {
  const steps = buildSteps(u)
  const cancelled = u.status === 'inactive'
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

function TimelinePanel({ u }: { u: UserRow }) {
  const steps = buildSteps(u)
  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Invitation timeline
      </p>
      <ol className="relative ml-2 border-l border-gray-200 space-y-0">
        {steps.map((s, i) => (
          <li key={i} className="mb-0 ml-5 pb-4 last:pb-0">
            {/* dot */}
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
              }`}>
                {s.label}
              </span>
              <span className="text-xs text-gray-400">{fmt(s.at)}</span>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export function UserManagement() {
  const [users,     setUsers]     = useState<UserRow[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)
  const [creating,  setCreating]  = useState(false)
  const [expanded,  setExpanded]  = useState<Set<string>>(new Set())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setUsers(await api.get<UserRow[]>('/users'))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function toggleExpand(uuid: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(uuid) ? next.delete(uuid) : next.add(uuid)
      return next
    })
  }

  async function handleApprove(uuid: string) {
    if (!confirm('Activate this user?')) return
    try {
      await api.post(`/users/${uuid}/approve`, {})
      await load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error approving user')
    }
  }

  async function handleCancel(uuid: string) {
    if (!confirm('Cancel this invitation?')) return
    try {
      await api.delete(`/users/${uuid}/invitation`)
      await load()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error cancelling invitation')
    }
  }

  return (
    <div>
      <Header title="Users" subtitle="Manage system users and invitations" />

      <div className="p-6 space-y-4">
        <div className="flex justify-end">
          <button className="btn-brand" onClick={() => setCreating(true)}>
            + Invite User
          </button>
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
                      {/* chevron */}
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
                        {u.status === 'pending_approval' && (
                          <button
                            className="text-xs font-medium text-brand-600 hover:underline"
                            onClick={() => handleApprove(u.uuid)}
                          >
                            Approve
                          </button>
                        )}
                        {(u.status === 'pending' || u.status === 'pending_approval') && (
                          <button
                            className="text-xs text-gray-400 hover:text-red-600 hover:underline"
                            onClick={() => handleCancel(u.uuid)}
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>

                    {expanded.has(u.uuid) && (
                      <tr key={`${u.uuid}-timeline`}>
                        <td colSpan={7} className="p-0">
                          <TimelinePanel u={u} />
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

      {creating && (
        <CreateSAModal
          onClose={() => setCreating(false)}
          onCreated={() => { setCreating(false); load() }}
        />
      )}
    </div>
  )
}
