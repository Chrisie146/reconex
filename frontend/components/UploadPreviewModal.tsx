'use client'

import React, { useState } from 'react'
import axios from '@/lib/axiosClient'
import { useClient } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ParsedRow {
  date: string
  description: string
  amount: number
}

interface Props {
  isOpen: boolean
  onClose: () => void
  parsed: ParsedRow[]
  isPdf?: boolean
  file?: File | null
  onSaved?: (sessionId: string, count: number, categories: string[]) => void
}

export default function UploadPreviewModal({ isOpen, onClose, parsed, isPdf = false, file = null, onSaved }: Props) {
  const [rows, setRows] = useState<ParsedRow[]>(parsed || [])
  const [selected, setSelected] = useState<boolean[]>(parsed.map(() => true))
  const [saving, setSaving] = useState(false)

  const { currentClient } = useClient()

  React.useEffect(() => {
    setRows(parsed || [])
    setSelected((parsed || []).map(() => true))
  }, [parsed])

  if (!isOpen) return null

  const toggleSelect = (idx: number) => {
    setSelected(prev => prev.map((v, i) => i === idx ? !v : v))
  }

  const updateField = (idx: number, field: keyof ParsedRow, value: any) => {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r))
  }

  const handleSave = async () => {
    // Build payload of selected rows
    const toSave = rows.filter((r, i) => selected[i])
    if (toSave.length === 0) {
      alert('No rows selected to save')
      return
    }

    setSaving(true)
    try {
      // Build params with client_id
      let params = ''
      if (currentClient?.id) {
        params = `client_id=${currentClient.id}`
      }

      const query = params ? `?${params}` : ''
      const res = await axios.post(`${API_BASE_URL}/save_parsed${query}`, { transactions: toSave })
      onSaved?.(res.data.session_id, res.data.transaction_count, res.data.categories || [])
      onClose()
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded shadow p-4 w-[900px] max-h-[80vh] overflow-auto">
        <h3 className="font-bold mb-2">Preview Parsed Transactions</h3>
        <p className="text-sm text-neutral-600 mb-3">Review parsed rows. Uncheck rows you don't want to save, or edit fields directly.</p>

        <div className="max-h-[60vh] overflow-auto border rounded">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-100 text-left">
                <th className="p-2">Keep</th>
                <th className="p-2">Date</th>
                <th className="p-2">Description</th>
                <th className="p-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b">
                  <td className="p-2">
                    <input type="checkbox" checked={selected[i]} onChange={() => toggleSelect(i)} />
                  </td>
                  <td className="p-2">
                    <input className="px-2 py-1 border rounded w-36" value={r.date} onChange={(e) => updateField(i, 'date', e.target.value)} />
                  </td>
                  <td className="p-2">
                    <input className="px-2 py-1 border rounded w-full" value={r.description} onChange={(e) => updateField(i, 'description', e.target.value)} />
                  </td>
                  <td className="p-2 text-right">
                    <input className="px-2 py-1 border rounded text-right w-32" value={String(r.amount)} onChange={(e) => updateField(i, 'amount', parseFloat(e.target.value || '0'))} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-end gap-2 mt-3">
          <button className="px-3 py-1 border rounded" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="px-3 py-1 bg-neutral-900 text-white rounded" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Selected'}</button>
        </div>
      </div>
    </div>
  )
}
