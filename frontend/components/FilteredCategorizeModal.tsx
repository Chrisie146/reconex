'use client'

import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Transaction {
  id: number
  date: string
  description: string
  amount: number
  category: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  transactions: Transaction[]
  categories: string[]
  sessionId: string
  onApplied?: (message: string, updatedCount: number) => void
  initialSelectAll?: boolean
}

export default function FilteredCategorizeModal({ isOpen, onClose, transactions, categories, sessionId, onApplied, initialSelectAll }: Props) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [selectAll, setSelectAll] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setSelectedIds([])
      setSelectAll(false)
      setSelectedCategory('')
      setLoading(false)
    }
    else {
      // if the caller requests initial select-all, enable it on open
      if (initialSelectAll) setSelectAll(true)
    }
  }, [isOpen])

  useEffect(() => {
    if (selectAll) {
      setSelectedIds(transactions.map((t) => t.id))
    } else {
      setSelectedIds([])
    }
  }, [selectAll, transactions])

  const toggleId = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      return [...prev, id]
    })
  }

  const handleApply = async () => {
    if (!selectedCategory) {
      alert('Please choose a category')
      return
    }
    if (selectedIds.length === 0) {
      alert('Select at least one transaction')
      return
    }

    setLoading(true)
    try {
      const response = await axios.post(
        `${API_BASE_URL}/bulk-categorise/ids`,
        { ids: selectedIds, category: selectedCategory },
        { params: { session_id: sessionId } }
      )

      if (response.data) {
        onApplied?.(response.data.message || 'Applied category', response.data.updated_count || 0)
      }
      onClose()
    } catch (err) {
      console.error('Apply filtered categorize failed', err)
      alert('Apply failed')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg max-w-3xl w-full max-h-[80vh] overflow-y-auto">
          <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50 sticky top-0">
            <h2 className="font-bold text-neutral-900">Categorize Filtered Transactions</h2>
          </div>

          <div className="px-6 py-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <input id="fc-select-all" type="checkbox" checked={selectAll} onChange={(e) => setSelectAll(e.target.checked)} className="mt-1" />
                <label htmlFor="fc-select-all" className="text-sm font-medium">Select all ({transactions.length})</label>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-sm">Category</label>
                <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="px-2 py-1 border rounded">
                  <option value="">Choose category...</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              {transactions.map((t) => (
                <div key={t.id} className="flex items-center justify-between border border-neutral-100 rounded p-2">
                  <div className="flex items-center gap-3">
                    <input type="checkbox" checked={selectedIds.includes(t.id)} onChange={() => toggleId(t.id)} />
                    <div className="text-sm">
                      <div className="font-medium">{t.description}</div>
                      <div className="text-xs text-neutral-500">{new Date(t.date).toLocaleDateString('en-ZA')} — R{Math.abs(t.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</div>
                    </div>
                  </div>
                  <div className="text-xs text-neutral-600">Current: {t.category || 'Uncategorized'}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="px-6 py-4 border-t border-neutral-200 bg-neutral-50 flex gap-3">
            <button onClick={onClose} disabled={loading} className="flex-1 px-4 py-2 text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 disabled:opacity-50">Cancel</button>
            <button onClick={handleApply} disabled={loading || !selectedCategory || selectedIds.length===0} className="flex-1 px-4 py-2 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 disabled:opacity-50">{loading ? 'Applying...' : `Apply to ${selectedIds.length} txn(s)`}</button>
          </div>
        </div>
      </div>
    </>
  )
}
