'use client'

import { useEffect, useState } from 'react'
import { Repeat, AlertCircle, ChevronDown, ChevronUp, Calendar } from 'lucide-react'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RecurringTransactionsProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface RecurringItem {
  description_pattern: string
  category: string
  average_amount: number
  occurrences: number
  months_active: string[]
  frequency: string
  total: number
  amount_variance: number
  last_seen: string
  is_debit: boolean
  transactions: { date: string; amount: number; description: string }[]
}

const fmtCurrency = (v: number) => {
  const sign = v < 0 ? '-' : ''
  return `${sign}R ${Math.abs(v).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function RecurringTransactions({ sessionId, currentClient }: RecurringTransactionsProps) {
  const [items, setItems] = useState<RecurringItem[]>([])
  const [totalAmount, setTotalAmount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)
  const [filterType, setFilterType] = useState<'all' | 'debit' | 'credit'>('all')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: any = {}
        if (currentClient?.id) params.client_id = currentClient.id
        else if (sessionId) params.session_id = sessionId
        else { setLoading(false); return }

        const res = await axios.get(`${API_BASE_URL}/analytics/recurring`, { params })
        setItems(res.data.recurring || [])
        setTotalAmount(res.data.total_recurring_amount || 0)
      } catch (e) {
        console.error('Failed to fetch recurring:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [sessionId, currentClient?.id])

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-5 w-48 bg-neutral-200 rounded" />
          <div className="h-32 bg-neutral-100 rounded" />
        </div>
      </div>
    )
  }

  if (items.length === 0) return null

  const filtered = items.filter((item) => {
    if (filterType === 'debit') return item.is_debit
    if (filterType === 'credit') return !item.is_debit
    return true
  })

  const totalDebits = items.filter(i => i.is_debit).reduce((s, i) => s + i.total, 0)
  const totalCredits = items.filter(i => !i.is_debit).reduce((s, i) => s + i.total, 0)

  return (
    <div className="rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-100">
            <Repeat className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Recurring Transactions</h3>
            <p className="text-[11px] text-neutral-500">
              {items.length} recurring items detected  ·  Net {fmtCurrency(totalAmount)}/period
            </p>
          </div>
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1.5">
          {(['all', 'debit', 'credit'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilterType(f)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                filterType === f
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-neutral-50 text-neutral-500 hover:bg-neutral-100'
              }`}
            >
              {f === 'all' ? 'All' : f === 'debit' ? 'Debits' : 'Credits'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary chips */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-neutral-50">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-50 text-xs">
          <span className="text-red-500 font-medium">Recurring debits:</span>
          <span className="font-bold text-red-700">{fmtCurrency(Math.abs(totalDebits))}</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 text-xs">
          <span className="text-emerald-500 font-medium">Recurring credits:</span>
          <span className="font-bold text-emerald-700">{fmtCurrency(totalCredits)}</span>
        </div>
      </div>

      {/* List */}
      <div className="divide-y divide-neutral-50">
        {filtered.map((item, idx) => {
          const isExpanded = expandedIdx === idx
          return (
            <div key={idx} className="group">
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                className="w-full px-5 py-3 flex items-center gap-3 text-left hover:bg-neutral-50 transition-colors"
              >
                {/* Icon */}
                <div className={`flex items-center justify-center w-7 h-7 rounded-full shrink-0 ${
                  item.is_debit ? 'bg-red-50' : 'bg-emerald-50'
                }`}>
                  <Repeat className={`w-3.5 h-3.5 ${item.is_debit ? 'text-red-500' : 'text-emerald-500'}`} />
                </div>

                {/* Description & meta */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-800 truncate">
                    {item.description_pattern}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-500">
                      {item.category}
                    </span>
                    <span className="text-[10px] text-neutral-400">
                      {item.frequency}  ·  {item.occurrences} times
                    </span>
                    {item.amount_variance > 2 && (
                      <span className="flex items-center gap-0.5 text-[10px] text-amber-500">
                        <AlertCircle className="w-3 h-3" />
                        {item.amount_variance.toFixed(0)}% variance
                      </span>
                    )}
                  </div>
                </div>

                {/* Amount */}
                <div className="text-right shrink-0">
                  <p className={`text-sm font-bold ${item.is_debit ? 'text-red-600' : 'text-emerald-600'}`}>
                    {fmtCurrency(item.average_amount)}
                  </p>
                  <p className="text-[10px] text-neutral-400">per month avg</p>
                </div>

                {/* Chevron */}
                {isExpanded
                  ? <ChevronUp className="w-4 h-4 text-neutral-400 shrink-0" />
                  : <ChevronDown className="w-4 h-4 text-neutral-400 shrink-0" />}
              </button>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="px-5 pb-4 pt-1">
                  <div className="ml-10 bg-neutral-50 rounded-lg border border-neutral-100 p-3">
                    <div className="grid grid-cols-3 gap-4 mb-3">
                      <div>
                        <p className="text-[10px] text-neutral-400 uppercase">Total</p>
                        <p className="text-sm font-bold text-neutral-700">{fmtCurrency(item.total)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-neutral-400 uppercase">Last Seen</p>
                        <p className="text-sm font-semibold text-neutral-700">{item.last_seen}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-neutral-400 uppercase">Months Active</p>
                        <p className="text-sm font-semibold text-neutral-700">{item.months_active.length}</p>
                      </div>
                    </div>

                    {/* Active months pills */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      {item.months_active.map((m) => (
                        <span key={m} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-medium">
                          {m}
                        </span>
                      ))}
                    </div>

                    {/* Recent transactions */}
                    <p className="text-[10px] text-neutral-400 uppercase mb-1">Recent Occurrences</p>
                    <div className="space-y-1">
                      {item.transactions.slice(0, 6).map((t, ti) => (
                        <div key={ti} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <Calendar className="w-3 h-3 text-neutral-300" />
                            <span className="text-neutral-500">{t.date}</span>
                            <span className="text-neutral-700 truncate max-w-[180px]">{t.description}</span>
                          </div>
                          <span className={`font-medium ${t.amount < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                            {fmtCurrency(t.amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
