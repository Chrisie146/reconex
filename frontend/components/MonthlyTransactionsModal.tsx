'use client'

import { useEffect, useState } from 'react'
import { X, TrendingUp, TrendingDown } from 'lucide-react'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface MonthlyTransactionsModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
  currentClient?: Client | null
  month: string // YYYY-MM format
  monthData: {
    total_income: number
    total_expenses: number
    net_balance: number
  }
}

interface Transaction {
  id: number
  date: string
  description: string
  amount: number
  category: string
  merchant?: string
}

export default function MonthlyTransactionsModal({
  isOpen,
  onClose,
  sessionId,
  currentClient,
  month,
  monthData
}: MonthlyTransactionsModalProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'income' | 'expenses'>('all')

  useEffect(() => {
    if (!isOpen) return

    const fetchTransactions = async () => {
      setLoading(true)
      try {
        // Calculate date range for month
        const [year, monthNum] = month.split('-')
        const firstDay = `${month}-01`
        const lastDay = new Date(parseInt(year), parseInt(monthNum), 0).getDate()
        const lastDayFormatted = `${month}-${String(lastDay).padStart(2, '0')}`

        const params: any = {
          date_from: firstDay,
          date_to: lastDayFormatted
        }

        if (currentClient?.id) {
          params.client_id = currentClient.id
        } else if (sessionId) {
          params.session_id = sessionId
        }

        const response = await axios.get(`${API_BASE_URL}/transactions`, { params })
        setTransactions(response.data.transactions || [])
      } catch (error) {
        console.error('Failed to fetch monthly transactions:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchTransactions()
  }, [isOpen, sessionId, currentClient?.id, month])

  if (!isOpen) return null

  const filteredTransactions = transactions.filter(t => {
    if (filter === 'income') return t.amount > 0
    if (filter === 'expenses') return t.amount < 0
    return true
  })

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-neutral-900">
              Transactions for {month}
            </h2>
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="text-green-600 font-medium">
                Income: R{monthData.total_income.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </span>
              <span className="text-red-600 font-medium">
                Expenses: R{Math.abs(monthData.total_expenses).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </span>
              <span className={`font-medium ${monthData.net_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                Net: R{monthData.net_balance.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-neutral-600" />
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="px-6 py-3 border-b border-neutral-200 flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'all'
                ? 'bg-neutral-900 text-white'
                : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
            }`}
          >
            All ({transactions.length})
          </button>
          <button
            onClick={() => setFilter('income')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              filter === 'income'
                ? 'bg-green-600 text-white'
                : 'bg-green-50 text-green-700 hover:bg-green-100'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            Income ({transactions.filter(t => t.amount > 0).length})
          </button>
          <button
            onClick={() => setFilter('expenses')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              filter === 'expenses'
                ? 'bg-red-600 text-white'
                : 'bg-red-50 text-red-700 hover:bg-red-100'
            }`}
          >
            <TrendingDown className="w-4 h-4" />
            Expenses ({transactions.filter(t => t.amount < 0).length})
          </button>
        </div>

        {/* Transactions List */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-neutral-600">Loading transactions...</div>
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-neutral-600">No transactions found</div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th className="text-left px-6 py-3 font-medium text-neutral-700">Date</th>
                  <th className="text-left px-6 py-3 font-medium text-neutral-700">Description</th>
                  <th className="text-left px-6 py-3 font-medium text-neutral-700">Category</th>
                  <th className="text-right px-6 py-3 font-medium text-neutral-700">Amount</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                    <td className="px-6 py-3 text-neutral-900">
                      {new Date(txn.date).toLocaleDateString('en-ZA', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </td>
                    <td className="px-6 py-3">
                      <div>
                        <div className="text-neutral-900">{txn.description}</div>
                        {txn.merchant && (
                          <div className="text-xs text-neutral-500 mt-0.5">{txn.merchant}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700">
                        {txn.category}
                      </span>
                    </td>
                    <td className={`text-right px-6 py-3 font-medium ${
                      txn.amount >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      R{Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between bg-neutral-50">
          <div className="text-sm text-neutral-600">
            Showing {filteredTransactions.length} of {transactions.length} transactions
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
