import { useState, useEffect } from 'react'
import { api } from '@/shared/api'
import type { HospitalRow } from '@/modules/crud/hospitals/HospitalManagement'
import type { SlotRow } from './SlotManagement'

interface Props {
  slot: SlotRow
  onClose: () => void
  onSaved: (slot: SlotRow) => void
}

export function EditSlotModal({ slot, onClose, onSaved }: Props) {
  const [hospitals,    setHospitals]    = useState<HospitalRow[]>([])
  const [date,         setDate]         = useState(slot.date)
  const [type,         setType]         = useState(slot.type)
  const [department,   setDepartment]   = useState(slot.department)
  const [medicinerCrm, setMedicinerCrm] = useState(slot.mediciner_crm ?? '')
  const [error,        setError]        = useState<string | null>(null)
  const [saving,       setSaving]       = useState(false)

  useEffect(() => {
    api.get<HospitalRow[]>('/hospitals').then(setHospitals).catch(() => {})
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const updated = await api.put<SlotRow>(`/slots/${slot.uuid}`, {
        date,
        type,
        department,
        mediciner_crm: medicinerCrm || null,
      })
      onSaved(updated)
    } catch (err: unknown) {
      const msg = (err as { data?: { error?: string } })?.data?.error ?? 'Failed to update slot.'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const hospitalName = hospitals.find((h) => h.uuid === slot.hospital_uuid)?.name ?? slot.hospital_uuid

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Edit Slot</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Hospital</label>
            <p className="text-sm text-gray-700 font-medium">{hospitalName}</p>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            >
              <option value="PM">PM – Physician On-Call</option>
              <option value="PE">PE – Nursing Duty</option>
              <option value="CC">CC – Operating Room</option>
              <option value="CM">CM – Outpatient</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Department</label>
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            >
              <option value="UTI">UTI – ICU</option>
              <option value="PA">PA – Urgent Care</option>
              <option value="PS">PS – Emergency Room</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Mediciner CRM <span className="text-gray-400 font-normal">(optional)</span></label>
            <input
              type="text"
              value={medicinerCrm}
              onChange={(e) => setMedicinerCrm(e.target.value)}
              placeholder="CRM/SP 123456"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost text-gray-600 border border-gray-200">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn-brand">
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
