 'use client'

import React, { useEffect, useState } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Props {
  isOpen: boolean
  onClose: () => void
  transaction: any | null
  sessionId: string
  onSaved?: (merchant: string) => void
}

export default function MerchantEditModal({ isOpen, onClose, transaction, sessionId, onSaved }: Props) {
  const [merchant, setMerchant] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [keyword, setKeyword] = useState('')

  useEffect(() => {
    if (transaction) {
      setMerchant(transaction.merchant ?? '')
      setKeyword(transaction.description ?? '')
    }
  }, [transaction])

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/merchants`, { params: { session_id: sessionId } })
        setSuggestions(res.data.merchants || [])
      } catch (e) {
        // ignore
      }
    }
    if (isOpen) fetch()
  }, [isOpen, sessionId])

  if (!isOpen || !transaction) return null

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded shadow p-6 w-96">
        <h3 className="font-bold mb-2">Edit Merchant</h3>
        <div className="text-sm text-neutral-700 mb-3">{transaction.description}</div>

        <label className="text-xs text-neutral-600">Keyword (used to match similar transactions)</label>
        <input
          placeholder="Enter keyword for matching (editable)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="w-full px-2 py-1 border rounded mb-2"
        />

        <label className="text-xs text-neutral-600">Merchant</label>
        <input
          list="merchant-suggestions"
          value={merchant}
          onChange={(e) => setMerchant(e.target.value)}
          className="w-full px-2 py-1 border rounded mb-2"
        />
        <datalist id="merchant-suggestions">
          {suggestions.map((s) => <option key={s} value={s} />)}
        </datalist>

        <div className="flex justify-end gap-2 mt-4">
          <button className="px-3 py-1 border rounded" onClick={onClose}>Cancel</button>
          <button className="px-3 py-1 border rounded" onClick={async () => {
            // Apply merchant to transactions matched by keyword (only unassigned by default)
            const useKeyword = (keyword || '').trim()
            if (!merchant) {
              if (!confirm('Merchant is blank. Do you want to apply blank to similar transactions?')) return
            } else if (!confirm(`Apply merchant "${merchant}" to matching transactions for keyword:\n"${useKeyword || '[all]'}" (only unassigned)?`)) return

            try {
              const payload = { keyword: useKeyword, merchant, only_unassigned: true }
              const res = await axios.post(`${API_BASE_URL}/bulk-merchant`, payload, { params: { session_id: sessionId } })
              const updated = res.data.updated_count || 0
              alert(`Applied to ${updated} transaction(s)`)
              onSaved?.(merchant)
              onClose()
            } catch (e) {
              alert('Failed to apply to similar')
            }
          }}>Apply to similar</button>
          <button className="px-3 py-1 bg-neutral-900 text-white rounded" onClick={async () => {
            try {
              await axios.put(`${API_BASE_URL}/transactions/${transaction.id}/merchant`, { merchant }, { params: { session_id: sessionId } })
              onSaved?.(merchant)
              onClose()
            } catch (e) {
              alert('Failed to save merchant')
            }
          }}>Save</button>
        </div>
      </div>
    </div>
  )
}
