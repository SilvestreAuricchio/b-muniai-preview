import { useEffect, useState, useCallback, useRef } from 'react'
import { Header } from '@/shell/Header'
import { api } from '@/shared/api'
import { maskCPF } from '@/shared/taxId'
import { InviteMedicinereModal } from './InviteMedicinereModal'

type MedicinereStatus = 'pending' | 'pending_approval' | 'active' | 'disabled' | 'inactive'

interface MedicinereRow {
  uuid:       string
  name:       string
  email:      string
  telephone:  string
  status:     MedicinereStatus
  role:       string
  cpf:        string
  specialty:  string | null
  crm_state:  string | null
  crm_number: string | null
  created_at: string | null
}

interface PagedResponse {
  items:    MedicinereRow[]
  total:    number
  page:     number
  per_page: number
}

const STATUS_BADGE: Record<MedicinereStatus, string> = {
  pending:          'bg-yellow-100 text-yellow-800',
  pending_approval: 'bg-blue-100   text-blue-800',
  active:           'bg-green-100  text-green-800',
  disabled:         'bg-amber-100  text-amber-700',
  inactive:         'bg-gray-100   text-gray-500',
}

const STATUS_LABEL: Record<MedicinereStatus, string> = {
  pending:          'Pending',
  pending_approval: 'Awaiting approval',
  active:           'Active',
  disabled:         'Disabled',
  inactive:         'Inactive',
}

// ── Action menu ────────────────────────────────────────────────────────────

interface ActionMenuProps {
  m:        MedicinereRow
  onAction: (uuid: string, action: 'disable' | 'enable') => Promise<void>
}

function ActionMenu({ m, onAction }: ActionMenuProps) {
  const [open, setOpen] = useState(false)
  const [pos,  setPos]  = useState<{ top: number; right: number } | null>(null)
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
          <circle cx="8" cy="3"  r="1.5"/>
          <circle cx="8" cy="8"  r="1.5"/>
          <circle cx="8" cy="13" r="1.5"/>
        </svg>
      </button>

      {open && pos && (
        <div
          ref={menuRef}
          style={{ position: 'fixed', top: pos.top, right: pos.right, zIndex: 9999 }}
          className="w-40 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        >
          {m.status === 'active' && (
            <button
              className="w-full px-3 py-1.5 text-left text-xs font-medium text-amber-600 hover:bg-gray-50"
              onClick={() => { setOpen(false); onAction(m.uuid, 'disable') }}
            >
              Disable
            </button>
          )}
          {m.status === 'disabled' && (
            <button
              className="w-full px-3 py-1.5 text-left text-xs font-medium text-green-600 hover:bg-gray-50"
              onClick={() => { setOpen(false); onAction(m.uuid, 'enable') }}
            >
              Re-enable
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Toast ──────────────────────────────────────────────────────────────────

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-3 shadow-lg">
      <p className="text-sm font-medium text-green-800">{message}</p>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

const PER_PAGE = 20

export function MedicinereManagement() {
  const [items,    setItems]    = useState<MedicinereRow[]>([])
  const [total,    setTotal]    = useState(0)
  const [page,     setPage]     = useState(1)
  const [search,   setSearch]   = useState('')
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)
  const [inviting, setInviting] = useState(false)
  const [toast,    setToast]    = useState<string | null>(null)

  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async (p: number, q: string) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ page: String(p), per_page: String(PER_PAGE) })
      if (q) params.set('search', q)
      const data = await api.get<PagedResponse>(`/medicineres?${params}`)
      setItems(data.items)
      setTotal(data.total)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load medicineres')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(page, search) }, [load, page])

  function handleSearchChange(v: string) {
    setSearch(v)
    setPage(1)
    if (searchRef.current) clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => load(1, v), 300)
  }

  async function handleAction(uuid: string, action: 'disable' | 'enable') {
    const messages = {
      disable: 'Disable this user? They will not be able to log in.',
      enable:  'Re-enable this user?',
    }
    if (!confirm(messages[action])) return
    try {
      await api.post(`/users/${uuid}/${action}`, {})
      await load(page, search)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : `Error: ${action} failed`)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div>
      <Header title="Medicineres" subtitle="Manage mediciner accounts and profiles" />

      <div className="p-6 space-y-4">
        <div className="flex items-center gap-3">
          <input
            type="search"
            className="flex-1 rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            placeholder="Search by name or CPF…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
          <button className="btn-brand" onClick={() => setInviting(true)}>
            + Invite Mediciner
          </button>
        </div>

        {error && (
          <div className="card border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        <div className="card overflow-hidden p-0">
          {loading ? (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">Loading…</div>
          ) : items.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400">No medicineres found</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">CPF</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Specialty</th>
                  <th className="px-4 py-3">CRM</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {items.map((m) => (
                  <tr key={m.uuid} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-mono text-gray-600">{maskCPF(m.cpf)}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                    <td className="px-4 py-3 text-gray-500">{m.specialty ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {m.crm_state && m.crm_number ? `${m.crm_state} ${m.crm_number}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{m.email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[m.status]}`}>
                        {STATUS_LABEL[m.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {(m.status === 'active' || m.status === 'disabled') && (
                        <ActionMenu m={m} onAction={handleAction} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{total} total</span>
            <div className="flex gap-2">
              <button
                className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                ← Prev
              </button>
              <span className="px-2 py-1">
                Page {page} of {totalPages}
              </span>
              <button
                className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-40"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {inviting && (
        <InviteMedicinereModal
          onClose={() => setInviting(false)}
          onCreated={(email) => {
            setInviting(false)
            load(page, search)
            setToast(`Invitation sent to ${email}`)
          }}
        />
      )}

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </div>
  )
}
