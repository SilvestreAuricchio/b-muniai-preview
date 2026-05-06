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
  otpDispatchedAt:  string | null
}

const STATUS_BADGE: Record<UserStatus, string> = {
  pending:          'bg-yellow-100 text-yellow-800',
  pending_approval: 'bg-blue-100   text-blue-800',
  active:           'bg-green-100  text-green-800',
  inactive:         'bg-gray-100   text-gray-500',
}

const STATUS_LABEL: Record<UserStatus, string> = {
  pending:          'pending',
  pending_approval: 'awaiting approval',
  active:           'active',
  inactive:         'inactive',
}

export function UserManagement() {
  const [users,    setUsers]    = useState<UserRow[]>([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

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
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">OTP Sent</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {users.map((u) => (
                  <tr key={u.uuid} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-900">{u.name}</td>
                    <td className="px-4 py-3 text-gray-500">{u.email}</td>
                    <td className="px-4 py-3 text-gray-500">{u.role}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[u.status]}`}>
                        {STATUS_LABEL[u.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {u.otpDispatchedAt
                        ? <span title={u.otpDispatchedAt} className="text-xs text-gray-500">
                            {new Date(u.otpDispatchedAt).toLocaleString()}
                          </span>
                        : <span className="text-xs text-gray-300">—</span>
                      }
                    </td>
                    <td className="px-4 py-3 space-x-2">
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
