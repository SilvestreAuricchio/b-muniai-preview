import { useState, useEffect, FormEvent } from 'react'
import { api } from '@/shared/api'
import { maskCPF, cpfError } from '@/shared/taxId'
import type { HospitalRow } from '@/modules/crud/hospitals/HospitalManagement'

interface Props {
  onClose:   () => void
  onCreated: (email: string) => void
}

const UF_CODES = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO',
  'MA','MG','MS','MT','PA','PB','PE','PI','PR',
  'RJ','RN','RO','RR','RS','SC','SE','SP','TO',
]

function Field({
  label, type = 'text', value, onChange, onBlur, placeholder, error, required = true,
}: {
  label: string; type?: string; value: string
  onChange: (v: string) => void; onBlur?: () => void
  placeholder?: string; error?: string | null; required?: boolean
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">
        {label}{required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      <input
        type={type}
        className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        required={required}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

export function InviteMedicinereModal({ onClose, onCreated }: Props) {
  const [name,      setName]      = useState('')
  const [email,     setEmail]     = useState('')
  const [telephone, setTelephone] = useState('')
  const [cpf,       setCpf]       = useState('')
  const [cpfTouched, setCpfTouched] = useState(false)
  const [specialty, setSpecialty] = useState('')
  const [crmState,  setCrmState]  = useState('')
  const [crmNumber, setCrmNumber] = useState('')
  const [hospitalUuid, setHospitalUuid] = useState('')
  const [hospitals, setHospitals] = useState<HospitalRow[]>([])
  const [crmLoading, setCrmLoading] = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [loading,   setLoading]   = useState(false)

  const cpfValidationError = cpfTouched ? cpfError(cpf) : null
  const canLookupCrm = crmState && crmNumber.replace(/\D/g, '').length > 0

  useEffect(() => {
    api.get<HospitalRow[]>('/hospitals')
      .then(setHospitals)
      .catch(() => setHospitals([]))
  }, [])

  async function lookupCrm() {
    if (!canLookupCrm) return
    setCrmLoading(true)
    try {
      const result = await api.get<{ name?: string; specialty?: string } | null>(
        `/medicineres/crm-lookup?state=${crmState}&number=${crmNumber.replace(/\D/g, '')}`
      )
      if (result) {
        if (result.name)      setName(result.name)
        if (result.specialty) setSpecialty(result.specialty)
      }
    } catch {
      // lookup unavailable — silently ignore
    } finally {
      setCrmLoading(false)
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    const cleanCpf = cpf.replace(/\D/g, '')
    if (cleanCpf.length !== 11 || cpfError(cpf)) {
      setError('Please enter a valid CPF.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await api.post('/medicineres', {
        name,
        email,
        telephone: telephone || undefined,
        cpf: cleanCpf,
        specialty: specialty || undefined,
        crm_state: crmState || undefined,
        crm_number: crmNumber.replace(/\D/g, '') || undefined,
        hospital_uuid: hospitalUuid || undefined,
      })
      onCreated(email)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-lg p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="mb-4 text-base font-semibold text-gray-900">Invite Mediciner</h2>

        <form onSubmit={submit} className="space-y-3">
          <Field label="Full name"  value={name}      onChange={setName}      />
          <Field label="Email"      type="email" value={email} onChange={setEmail} />
          <Field
            label="Phone" value={telephone} onChange={setTelephone}
            placeholder="+5511999999999" required={false}
          />

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              CPF<span className="ml-0.5 text-red-500">*</span>
            </label>
            <input
              type="text"
              inputMode="numeric"
              className="w-full rounded-md border border-gray-200 px-3 py-2 font-mono text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="000.000.000-00"
              value={cpf}
              onChange={(e) => setCpf(maskCPF(e.target.value))}
              onBlur={() => setCpfTouched(true)}
              required
            />
            {cpfValidationError && (
              <p className="mt-1 text-xs text-red-600">{cpfValidationError}</p>
            )}
          </div>

          <Field label="Specialty"  value={specialty} onChange={setSpecialty} required={false} />

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">CRM State</label>
              <select
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={crmState}
                onChange={(e) => setCrmState(e.target.value)}
              >
                <option value="">— UF —</option>
                {UF_CODES.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">CRM Number</label>
              <div className="flex gap-1">
                <input
                  type="text"
                  inputMode="numeric"
                  className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="12345"
                  value={crmNumber}
                  onChange={(e) => setCrmNumber(e.target.value.replace(/\D/g, ''))}
                />
              </div>
            </div>
          </div>

          {canLookupCrm && (
            <button
              type="button"
              className="text-xs font-medium text-brand-600 hover:underline disabled:opacity-40"
              onClick={lookupCrm}
              disabled={crmLoading}
            >
              {crmLoading ? 'Looking up…' : 'Look up CRM →'}
            </button>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Hospital</label>
            <select
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              value={hospitalUuid}
              onChange={(e) => setHospitalUuid(e.target.value)}
            >
              <option value="">— None —</option>
              {hospitals.map((h) => (
                <option key={h.uuid} value={h.uuid}>{h.name}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-brand" disabled={loading}>
              {loading ? 'Sending…' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
