 'use client'

import React, { useEffect, useState } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Props {
  isOpen: boolean
  onClose: () => void
  transactions: any[]
  sessionId: string
  onApplied?: (message: string, count: number) => void
}

export default function BulkMerchantModal({ isOpen, onClose, transactions, sessionId, onApplied }: Props) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [merchant, setMerchant] = useState('')
  const [keyword, setKeyword] = useState('')
  const [onlyUnassigned, setOnlyUnassigned] = useState(true)
  const [suggestions, setSuggestions] = useState<string[]>([])

  useEffect(() => { if (isOpen) setSelectedIds(transactions.map(t => t.id)) }, [isOpen, transactions])

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/merchants`, { params: { session_id: sessionId } })
        setSuggestions(res.data.merchants || [])
      } catch (e) {}
    }
    if (isOpen) fetch()
  }, [isOpen, sessionId])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded shadow p-6 w-[700px] max-h-[80vh] overflow-auto">
        <h3 className="font-bold mb-2">Assign Merchant to Filtered Transactions</h3>

        <div className="mb-3 text-sm text-neutral-600">Select transactions to assign a merchant:</div>
        <div className="max-h-56 overflow-auto border rounded p-2 mb-3">
          {transactions.map((t) => (
            <div key={t.id} className="flex items-center gap-3 py-1">
              <input type="checkbox" checked={selectedIds.includes(t.id)} onChange={(e) => {
                if (e.target.checked) setSelectedIds(prev => [...prev, t.id])
                else setSelectedIds(prev => prev.filter(id => id !== t.id))
              }} />
              <div className="text-sm">{t.date} • {t.description} • R{Math.abs(t.amount).toFixed(2)}</div>
            </div>
          ))}
        </div>

        <div className="mb-3">
          <label className="text-xs text-neutral-500">Keyword (optional) - used to match similar transactions</label>
          <input placeholder="Enter keyword to match descriptions" value={keyword} onChange={(e) => setKeyword(e.target.value)} className="mt-1 w-full px-2 py-1 border rounded" />
        </div>

        <div className="mb-3">
          <label className="text-xs text-neutral-500">Merchant</label>
          <input list="bulk-merchant-suggestions" value={merchant} onChange={(e) => setMerchant(e.target.value)} className="mt-1 w-full px-2 py-1 border rounded" />
          <datalist id="bulk-merchant-suggestions">{suggestions.map(s => <option key={s} value={s} />)}</datalist>
        </div>

        <div className="flex items-center gap-2 mb-3">
          <input type="checkbox" id="only-unassigned" checked={onlyUnassigned} onChange={(e) => setOnlyUnassigned(e.target.checked)} />
          <label htmlFor="only-unassigned" className="text-sm text-neutral-600">Only update unassigned merchants</label>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button className="px-3 py-1 border rounded" onClick={onClose}>Cancel</button>
          <button className="px-3 py-1 bg-neutral-900 text-white rounded" onClick={async () => {
            try {
              const res = await axios.post(`${API_BASE_URL}/bulk-merchant/ids`, { ids: selectedIds, merchant }, { params: { session_id: sessionId } })
              onApplied?.(res.data.message || 'Applied', res.data.updated_count || 0)
            } catch (e) {
              alert('Failed to apply merchant')
            }
          }}>Apply to selected</button>

          <button className="px-3 py-1 border rounded" onClick={async () => {
            // Apply by keyword across session (uses POST /bulk-merchant)
            try {
              const payload = { keyword: (keyword || '').trim(), merchant, only_unassigned: !!onlyUnassigned }
              const res = await axios.post(`${API_BASE_URL}/bulk-merchant`, payload, { params: { session_id: sessionId } })
              onApplied?.(res.data.message || 'Applied', res.data.updated_count || 0)
            } catch (e) {
              alert('Failed to apply by keyword')
            }
          }}>Apply by keyword</button>
        </div>
      </div>
    </div>
  )
}
