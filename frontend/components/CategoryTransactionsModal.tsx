"use client"

import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, X } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Props {
  isOpen: boolean
  onClose: () => void
  sessionId: string
  category: string
}

interface Transaction {
  id: number
  date: string
  description: string
  amount: number
  merchant?: string
}

interface MonthGroup {
  month: string
  transactions: Transaction[]
  total: number
}

export default function CategoryTransactionsModal({ isOpen, onClose, sessionId, category }: Props) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [series, setSeries] = useState<{ month: string; amount: number }[]>([])
  const [loadingTx, setLoadingTx] = useState(false)
  const [loadingSeries, setLoadingSeries] = useState(false)
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)
  const [expandedMonths, setExpandedMonths] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!isOpen) return

    const fetchTransactions = async () => {
      setLoadingTx(true)
      try {
        const resp = await axios.get(`${API_BASE_URL}/categories/${encodeURIComponent(category)}/transactions`, {
          params: { session_id: sessionId }
        })
        const txns = resp.data.transactions || []
        setTransactions(txns)
        
        // Auto-expand all months initially
        const months = new Set<string>(txns.map((t: Transaction) => t.date.substring(0, 7)))
        setExpandedMonths(months)
      } catch (e) {
        console.error('Failed to load transactions for category', e)
        setTransactions([])
      } finally {
        setLoadingTx(false)
      }
    }

    const fetchSeries = async () => {
      setLoadingSeries(true)
      try {
        const resp = await axios.get(`${API_BASE_URL}/category-monthly`, {
          params: { session_id: sessionId, category }
        })
        setSeries(resp.data.series || [])
      } catch (e) {
        console.error('Failed to load monthly series', e)
        setSeries([])
      } finally {
        setLoadingSeries(false)
      }
    }

    fetchTransactions()
    fetchSeries()
    setSelectedMonth(null) // Reset filter when modal opens
  }, [isOpen, sessionId, category])

  if (!isOpen) return null

  // Group transactions by month
  const groupTransactionsByMonth = (): MonthGroup[] => {
    const groups: Record<string, Transaction[]> = {}
    
    transactions.forEach(txn => {
      const month = txn.date.substring(0, 7) // YYYY-MM
      if (!groups[month]) groups[month] = []
      groups[month].push(txn)
    })

    return Object.entries(groups)
      .map(([month, txns]) => ({
        month,
        transactions: txns.sort((a, b) => b.date.localeCompare(a.date)),
        total: txns.reduce((sum, t) => sum + Math.abs(t.amount), 0)
      }))
      .sort((a, b) => b.month.localeCompare(a.month))
  }

  const monthGroups = groupTransactionsByMonth()
  
  // Filter by selected month if any
  const filteredGroups = selectedMonth
    ? monthGroups.filter(g => g.month === selectedMonth)
    : monthGroups

  const toggleMonth = (month: string) => {
    const newExpanded = new Set(expandedMonths)
    if (newExpanded.has(month)) {
      newExpanded.delete(month)
    } else {
      newExpanded.add(month)
    }
    setExpandedMonths(newExpanded)
  }

  const totalTransactions = transactions.length
  const totalAmount = transactions.reduce((sum, t) => sum + Math.abs(t.amount), 0)

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-40 z-40" onClick={onClose} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg w-full max-w-6xl max-h-[90vh] flex flex-col">
          
          {/* Header */}
          <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold text-xl text-neutral-900">Category: {category}</h2>
                <div className="flex items-center gap-4 mt-2 text-sm text-neutral-600">
                  <span>{totalTransactions} transactions</span>
                  <span>•</span>
                  <span className="font-semibold">Total: R{totalAmount.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                  {selectedMonth && (
                    <>
                      <span>•</span>
                      <span className="text-blue-600">Filtered: {selectedMonth}</span>
                    </>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-neutral-200 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-neutral-600" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden flex">
            
            {/* Left Panel - Month-to-Month */}
            <div className="w-80 border-r border-neutral-200 overflow-y-auto bg-neutral-50">
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-neutral-900">Month-to-Month</h3>
                  {selectedMonth && (
                    <button
                      onClick={() => setSelectedMonth(null)}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Clear filter
                    </button>
                  )}
                </div>
                
                {loadingSeries ? (
                  <div className="text-neutral-600 text-sm">Loading...</div>
                ) : series.length === 0 ? (
                  <div className="text-neutral-600 text-sm">No data</div>
                ) : (
                  <div className="space-y-1">
                    {series.map((s) => (
                      <button
                        key={s.month}
                        onClick={() => setSelectedMonth(selectedMonth === s.month ? null : s.month)}
                        className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                          selectedMonth === s.month
                            ? 'bg-blue-100 border border-blue-300'
                            : 'bg-white hover:bg-neutral-100 border border-neutral-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`text-sm font-medium ${
                            selectedMonth === s.month ? 'text-blue-900' : 'text-neutral-900'
                          }`}>
                            {s.month}
                          </span>
                          <span className={`text-sm font-semibold ${
                            selectedMonth === s.month ? 'text-blue-700' : 'text-neutral-700'
                          }`}>
                            R{s.amount.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Panel - Transactions */}
            <div className="flex-1 overflow-y-auto">
              {loadingTx ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-neutral-600">Loading transactions...</div>
                </div>
              ) : filteredGroups.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-neutral-600">No transactions found for this category</div>
                </div>
              ) : (
                <div className="divide-y divide-neutral-200">
                  {filteredGroups.map((group) => {
                    const isExpanded = expandedMonths.has(group.month)
                    
                    return (
                      <div key={group.month} className="bg-white">
                        {/* Month Header */}
                        <button
                          onClick={() => toggleMonth(group.month)}
                          className="w-full px-6 py-3 flex items-center justify-between hover:bg-neutral-50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-neutral-600" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-neutral-600" />
                            )}
                            <span className="font-semibold text-neutral-900">{group.month}</span>
                            <span className="text-sm text-neutral-600">
                              ({group.transactions.length} {group.transactions.length === 1 ? 'transaction' : 'transactions'})
                            </span>
                          </div>
                          <span className="font-semibold text-neutral-900">
                            R{group.total.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                          </span>
                        </button>

                        {/* Transactions for this month */}
                        {isExpanded && (
                          <div className="border-t border-neutral-100">
                            <table className="w-full text-sm">
                              <thead className="bg-neutral-50">
                                <tr>
                                  <th className="text-left px-6 py-2 font-medium text-neutral-700">Date</th>
                                  <th className="text-left px-6 py-2 font-medium text-neutral-700">Description</th>
                                  <th className="text-right px-6 py-2 font-medium text-neutral-700">Amount</th>
                                </tr>
                              </thead>
                              <tbody>
                                {group.transactions.map((txn) => (
                                  <tr key={txn.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                                    <td className="px-6 py-3 text-neutral-900 whitespace-nowrap">
                                      {new Date(txn.date).toLocaleDateString('en-ZA', {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric'
                                      })}
                                    </td>
                                    <td className="px-6 py-3">
                                      <div className="text-neutral-900">{txn.description}</div>
                                      {txn.merchant && (
                                        <div className="text-xs text-neutral-500 mt-0.5">{txn.merchant}</div>
                                      )}
                                    </td>
                                    <td className="px-6 py-3 text-right font-medium text-neutral-900">
                                      R{Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
