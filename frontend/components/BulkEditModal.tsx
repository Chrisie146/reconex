'use client'

import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, CheckSquare, Layers, Loader2, Search, Store, Tag, X } from 'lucide-react'
import { toast } from 'sonner'
import axios from '@/lib/axiosClient'
import AccountSelector from './AccountSelector'
import type { Account } from '@/lib/hooks/useAccounts'
import { API_BASE_URL } from '@/lib/apiBase'

interface Transaction {
  id: number
  date: string
  description: string
  amount: number
  category: string
  merchant?: string | null
  account_id?: number | null
  account_code?: string | null
  account_name?: string | null
}

interface BulkEditModalProps {
  isOpen: boolean
  onClose: () => void
  transactions: Transaction[]
  categories: string[]
  sessionId: string
  clientId?: number | null
  onApplied?: (
    message: string,
    updatedCount: number,
    details: {
      ids: number[]
      category?: string
      account?: Account | null
      merchant?: string | null
      taskId?: string | null
      transactions?: Transaction[]
    }
  ) => void
}

export default function BulkEditModal({
  isOpen,
  onClose,
  transactions,
  categories,
  sessionId,
  clientId,
  onApplied,
}: BulkEditModalProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [category, setCategory] = useState('')
  const [accountId, setAccountId] = useState<number | null>(null)
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)
  const [merchant, setMerchant] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [onlyVisible, setOnlyVisible] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    setSelectedIds(transactions.map((t) => t.id))
    setCategory('')
    setAccountId(null)
    setSelectedAccount(null)
    setMerchant('')
    setSearch('')
    setOnlyVisible(false)
  }, [isOpen, transactions])

  const filteredTransactions = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return transactions
    return transactions.filter((t) =>
      [t.description, t.category, t.merchant, t.account_name, String(Math.abs(t.amount))]
        .some((value) => (value || '').toLowerCase().includes(q))
    )
  }, [transactions, search])

  const selectedTotal = useMemo(() => {
    return transactions
      .filter((t) => selectedIds.includes(t.id))
      .reduce((sum, t) => sum + t.amount, 0)
  }, [transactions, selectedIds])

  if (!isOpen) return null

  const params = clientId ? { client_id: clientId } : { session_id: sessionId }
  const targetIds = onlyVisible ? filteredTransactions.map((t) => t.id).filter((id) => selectedIds.includes(id)) : selectedIds
  const hasMappingChange = !!category || accountId !== null
  const hasMerchantChange = merchant.trim().length > 0
  const canApply = targetIds.length > 0 && (hasMappingChange || hasMerchantChange)

  const toggleId = (id: number) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
  }

  const selectVisible = () => {
    const visibleIds = filteredTransactions.map((t) => t.id)
    setSelectedIds((prev) => Array.from(new Set([...prev, ...visibleIds])))
  }

  const clearVisible = () => {
    const visibleIds = new Set(filteredTransactions.map((t) => t.id))
    setSelectedIds((prev) => prev.filter((id) => !visibleIds.has(id)))
  }

  const handleApply = async () => {
    if (!canApply) {
      toast.error('Choose at least one field to update')
      return
    }

    setLoading(true)
    try {
      let updatedCount = 0
      const messages: string[] = []
      let taskId: string | null = null
      let updatedTransactions: Transaction[] | undefined

      if (hasMappingChange) {
        const res = await axios.post(
          `${API_BASE_URL}/bulk-categorise/ids`,
          { ids: targetIds, category: category || undefined, account_id: accountId ?? undefined },
          { params }
        )
        updatedCount = Math.max(updatedCount, res.data?.updated_count || 0)
        taskId = res.data?.task_id || null
        updatedTransactions = res.data?.transactions
        messages.push('mapping')
      }

      if (hasMerchantChange) {
        const res = await axios.post(
          `${API_BASE_URL}/bulk-merchant/ids`,
          { ids: targetIds, merchant: merchant.trim() },
          { params }
        )
        updatedCount = Math.max(updatedCount, res.data?.updated_count || 0)
        messages.push('merchant')
      }

      onApplied?.(`Updated ${messages.join(' and ')} for ${targetIds.length} transaction(s)`, updatedCount || targetIds.length, {
        ids: targetIds,
        category: category || undefined,
        account: selectedAccount,
        merchant: hasMerchantChange ? merchant.trim() : undefined,
        taskId,
        transactions: updatedTransactions,
      })
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Bulk edit failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="flex max-h-[86vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl ring-1 ring-neutral-200">
          <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-5 py-3">
            <div>
              <h2 className="text-base font-semibold text-neutral-900">Bulk edit selected rows</h2>
              <p className="text-xs text-neutral-500">
                {selectedIds.length} selected · Net R{Math.abs(selectedTotal).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </p>
            </div>
            <button onClick={onClose} className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700">
              <X size={18} />
            </button>
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 divide-y divide-neutral-200 lg:grid-cols-[360px_1fr] lg:divide-x lg:divide-y-0">
            <div className="space-y-4 overflow-y-auto p-5">
              <div className="rounded-md border border-neutral-200 bg-white p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
                  <Tag size={15} className="text-neutral-500" />
                  Mapping
                </div>
                <div className="space-y-3">
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  >
                    <option value="">Leave category unchanged</option>
                    {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
                  </select>
                  <AccountSelector
                    clientId={clientId ?? null}
                    value={accountId}
                    onChange={(id, account) => { setAccountId(id); setSelectedAccount(account) }}
                    postableOnly
                    placeholder="Leave CoA account unchanged"
                  />
                </div>
              </div>

              <div className="rounded-md border border-neutral-200 bg-white p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
                  <Store size={15} className="text-neutral-500" />
                  Merchant
                </div>
                <input
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                  placeholder="Leave merchant unchanged"
                  className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
                <div className="mb-1 flex items-center gap-2 font-semibold">
                  <AlertCircle size={14} />
                  Spreadsheet-safe behavior
                </div>
                Blank fields are ignored. Only the checked rows are changed, and your current table filters stay in place after applying.
              </div>
            </div>

            <div className="flex min-h-0 flex-col">
              <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 bg-white px-4 py-3">
                <div className="relative min-w-[240px] flex-1">
                  <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search selected rows..."
                    className="w-full rounded-md border border-neutral-300 py-1.5 pl-8 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </div>
                <button onClick={selectVisible} className="rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">
                  Select visible
                </button>
                <button onClick={clearVisible} className="rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">
                  Clear visible
                </button>
              </div>

              <div className="min-h-0 flex-1 overflow-auto">
                <table className="w-full border-separate border-spacing-0 text-xs">
                  <thead className="sticky top-0 z-10 bg-neutral-100 text-[11px] uppercase tracking-wide text-neutral-500">
                    <tr>
                      <th className="border-b border-r border-neutral-300 px-2 py-2 text-left">Use</th>
                      <th className="border-b border-r border-neutral-300 px-2 py-2 text-left">Date</th>
                      <th className="border-b border-r border-neutral-300 px-2 py-2 text-left">Description</th>
                      <th className="border-b border-r border-neutral-300 px-2 py-2 text-right">Amount</th>
                      <th className="border-b border-neutral-300 px-2 py-2 text-left">Current mapping</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.map((txn) => {
                      const selected = selectedIds.includes(txn.id)
                      return (
                        <tr key={txn.id} className={selected ? 'bg-blue-50' : 'bg-white hover:bg-neutral-50'}>
                          <td className="border-b border-r border-neutral-200 px-2 py-1.5">
                            <button onClick={() => toggleId(txn.id)} className={selected ? 'text-blue-600' : 'text-neutral-300 hover:text-neutral-600'}>
                              <CheckSquare size={15} />
                            </button>
                          </td>
                          <td className="whitespace-nowrap border-b border-r border-neutral-200 px-2 py-1.5 tabular-nums text-neutral-600">
                            {new Date(txn.date).toLocaleDateString('en-ZA')}
                          </td>
                          <td className="max-w-md border-b border-r border-neutral-200 px-2 py-1.5 text-neutral-900">
                            <div className="truncate" title={txn.description}>{txn.description}</div>
                          </td>
                          <td className={`whitespace-nowrap border-b border-r border-neutral-200 px-2 py-1.5 text-right font-medium tabular-nums ${txn.amount >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                            {txn.amount >= 0 ? '+' : '-'}R{Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="border-b border-neutral-200 px-2 py-1.5 text-neutral-600">
                            <div className="flex items-center gap-1.5">
                              <Layers size={12} className="text-neutral-400" />
                              <span className="truncate">{txn.account_name || txn.category || 'Unmapped'}</span>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-neutral-200 bg-neutral-50 px-5 py-3">
            <label className="flex items-center gap-2 text-xs font-medium text-neutral-600">
              <input
                type="checkbox"
                checked={onlyVisible}
                onChange={(e) => setOnlyVisible(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-neutral-300 text-blue-600"
              />
              Apply only to visible filtered rows
            </label>
            <div className="flex gap-2">
              <button onClick={onClose} disabled={loading} className="rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50">
                Cancel
              </button>
              <button
                onClick={handleApply}
                disabled={loading || !canApply}
                className="inline-flex items-center gap-2 rounded-md bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading && <Loader2 size={15} className="animate-spin" />}
                Apply to {targetIds.length} row{targetIds.length === 1 ? '' : 's'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
