import { useState, FormEvent } from 'react'
import { api } from '@/shared/api'

interface Props {
  onClose:   () => void
  onCreated: () => void
}

const ROLES = ['SA-root', 'Scheduler', 'Mediciner'] as const

export function CreateSAModal({ onClose, onCreated }: Props) {
  const [form, setForm] = useState({ name: '', telephone: '', email: '', role: 'SA-root' })
  const [error, setError]     = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.post('/users', form)
      onCreated()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-md p-6 shadow-xl">
        <h2 className="mb-4 text-base font-semibold text-gray-900">Invite New User</h2>

        <form onSubmit={submit} className="space-y-3">
          <Field label="Full name" type="text"     value={form.name}      onChange={(v) => set('name', v)} />
          <Field label="Email"     type="email"    value={form.email}     onChange={(v) => set('email', v)} />
          <Field label="Telephone" type="tel"      value={form.telephone} onChange={(v) => set('telephone', v)} placeholder="+5511999999999" />

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Role</label>
            <select
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              value={form.role}
              onChange={(e) => set('role', e.target.value)}
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn-brand" disabled={loading}>
              {loading ? 'Sending…' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, type, value, onChange, placeholder }: {
  label: string; type: string; value: string
  onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type={type}
        className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
      />
    </div>
  )
}
