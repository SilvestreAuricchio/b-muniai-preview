import { useEffect, useState, useCallback } from 'react'
import { Header } from '@/shell/Header'
import { api } from '@/shared/api'
import { useAuth } from '@/shared/context/AuthContext'
import { maskTaxId } from '@/shared/taxId'
import { CreateHospitalOverlay } from './CreateHospitalOverlay'
import { HospitalDetailOverlay } from './HospitalDetailOverlay'

export interface HospitalRow {
  uuid:           string
  cnpj:           string
  name:           string
  address:        string
  slotTypes:      string[]
  schedulerCount: number
  status?:        'active' | 'inactive' | 'disabled'
}

const STATUS_DOT: Record<string, string> = {
  active:   'bg-green-400',
  inactive: 'bg-yellow-400',
  disabled: 'bg-red-400',
}

export function HospitalManagement() {
  const { country }                       = useAuth()
  const [hospitals,    setHospitals]    = useState<HospitalRow[]>([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState<string | null>(null)
  const [showCreate,   setShowCreate]   = useState(false)
  const [detailUuid,   setDetailUuid]   = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setHospitals(await api.get<HospitalRow[]>('/hospitals'))
    } catch {
      setError('Failed to load hospitals')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="flex flex-col h-full">
      <Header title="Hospitals" subtitle="Manage hospital registrations" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">

        <div className="flex justify-end">
          <button className="btn-brand" onClick={() => setShowCreate(true)}>+ New Hospital</button>
        </div>

        {loading && <p className="text-sm text-gray-400">Loading…</p>}
        {error   && <p className="text-sm text-red-500">{error}</p>}

        {!loading && !error && hospitals.length === 0 && (
          <div className="card p-8 text-center text-gray-400">
            <p className="text-sm">No hospitals registered yet.</p>
          </div>
        )}

        {!loading && hospitals.length > 0 && (
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">CNPJ</th>
                  <th className="px-4 py-3">Address</th>
                  <th className="px-4 py-3">Slot Types</th>
                  <th className="px-4 py-3 text-right">Schedulers</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {hospitals.map((h) => (
                  <tr
                    key={h.uuid}
                    className="hover:bg-gray-50/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 flex-shrink-0 rounded-full ${STATUS_DOT[h.status ?? 'active']}`} title={h.status ?? 'active'} />
                        <span className="font-medium text-gray-900">{h.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500">{maskTaxId(country, h.cnpj)}</td>
                    <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{h.address}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {h.slotTypes.map((s) => (
                          <span key={s} className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-brand-50 text-brand-700">
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{h.schedulerCount}</td>
                    <td className="px-4 py-3">
                      <button
                        className="text-xs font-medium text-brand-600 hover:underline"
                        onClick={() => setDetailUuid(h.uuid)}
                      >
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>

      {showCreate && (
        <CreateHospitalOverlay
          onClose={() => setShowCreate(false)}
          onCreated={(h) => { setHospitals((prev) => [h, ...prev]); setShowCreate(false) }}
        />
      )}

      {detailUuid && (
        <HospitalDetailOverlay
          uuid={detailUuid}
          onClose={() => setDetailUuid(null)}
          onSaved={(updated) => {
            setHospitals((prev) => prev.map((h) => h.uuid === updated.uuid ? updated : h))
            setDetailUuid(null)
          }}
        />
      )}
    </div>
  )
}
