 'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import Link from 'next/link'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'
import MonthlyTransactionsModal from './MonthlyTransactionsModal'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface MonthlySummaryProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface MonthData {
  month: string
  total_income: number
  total_expenses: number
  net_balance: number
}

export default function MonthlySummary({ sessionId, currentClient }: MonthlySummaryProps) {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [reconciliations, setReconciliations] = useState<Record<string, { opening_balance?: number | null; closing_balance?: number | null }>>({})
  const [editingMonth, setEditingMonth] = useState<string | null>(null)
  const [openInput, setOpenInput] = useState<string | null>(null)
  const [closeInput, setCloseInput] = useState<string | null>(null)
  const [overallRecon, setOverallRecon] = useState<{ system_opening_balance?: number | null; bank_closing_balance?: number | null; transactions_total?: number; system_closing_balance?: number; difference?: number } | null>(null)
  const [openOverallInput, setOpenOverallInput] = useState<string | null>('')
  const [bankCloseInput, setBankCloseInput] = useState<string | null>('')
  const [isMonthModalOpen, setIsMonthModalOpen] = useState(false)
  const [selectedMonth, setSelectedMonth] = useState<{ month: string; data: MonthData } | null>(null)

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        // Priority: if currentClient selected, use client_id; otherwise use sessionId
        const params: any = {}
        if (currentClient?.id) {
          params.client_id = currentClient.id
        } else if (sessionId) {
          params.session_id = sessionId
        } else {
          setLoading(false)
          return
        }

        const response = await axios.get(`${API_BASE_URL}/summary`, { params })
        setSummary(response.data)
        // fetch reconciliations
        try {
          const recResp = await axios.get(`${API_BASE_URL}/reconciliation`, { params })
          const recs = recResp.data.reconciliations || []
          const map: Record<string, any> = {}
          recs.forEach((r: any) => { map[r.month] = { opening_balance: r.opening_balance, closing_balance: r.closing_balance } })
          setReconciliations(map)
        } catch (e) {
          console.error('Failed to fetch reconciliations', e)
        }

        // fetch overall reconciliation overview
        try {
          const overviewResp = await axios.get(`${API_BASE_URL}/reconciliation/overview`, { params })
          setOverallRecon(overviewResp.data)
          setOpenOverallInput(overviewResp.data.system_opening_balance != null ? String(overviewResp.data.system_opening_balance) : '')
          setBankCloseInput(overviewResp.data.bank_closing_balance != null ? String(overviewResp.data.bank_closing_balance) : '')
        } catch (e) {
          const errMsg = (e as any)?.response?.data?.detail || (e as any)?.message || 'Unknown error'
          console.error('[MonthlySummary] Failed to fetch overall reconciliation:', errMsg, e)
        }
      } catch (error) {
        console.error('Failed to fetch summary:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchSummary()
  }, [sessionId, currentClient?.id])

  if (loading) {
    return <div className="text-center py-8 text-neutral-600">Loading summary...</div>
  }

  const overall = summary?.overall || {}
  const months = summary?.months || []

  return (
    <div className="space-y-6">
      {/* Overall Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <div>
            <p className="text-xs font-medium text-neutral-600">Reconciliation Overview</p>
            <p className="text-xs text-neutral-500 mt-1">System closing = opening + txns</p>
            <div className="mt-2 space-y-2">
              <div>
                <label className="text-xs text-neutral-500">System Opening</label>
                <input value={openOverallInput ?? ''} onChange={(e) => setOpenOverallInput(e.target.value)} className="mt-0.5 w-full px-2 py-1 text-sm border rounded" />
              </div>
              <div>
                <label className="text-xs text-neutral-500">Bank Closing</label>
                <input value={bankCloseInput ?? ''} onChange={(e) => setBankCloseInput(e.target.value)} className="mt-0.5 w-full px-2 py-1 text-sm border rounded" />
              </div>
              <button className="w-full px-2 py-1 text-xs bg-neutral-900 text-white rounded" onClick={async () => {
                try {
                  const o = openOverallInput ? parseFloat(openOverallInput) : null
                  const b = bankCloseInput ? parseFloat(bankCloseInput) : null
                  await axios.post(`${API_BASE_URL}/reconciliation/overview`, { system_opening_balance: o, bank_closing_balance: b }, { params: { session_id: sessionId } })
                  const overviewResp = await axios.get(`${API_BASE_URL}/reconciliation/overview`, { params: { session_id: sessionId } })
                  setOverallRecon(overviewResp.data)
                  alert('Saved')
                } catch (e) {
                  console.error('Failed to save overall reconciliation', e)
                  alert('Failed to save')
                }
              }}>Save</button>
              <div className="text-xs text-neutral-600 space-y-1 pt-1 border-t">
                <div>System closing: <span className="font-medium">R{overallRecon?.system_closing_balance?.toLocaleString('en-ZA', { minimumFractionDigits: 2 }) ?? '0'}</span></div>
                {overallRecon?.difference != null && (
                  <div className={Math.abs(Number(overallRecon.difference)) < 0.005 ? 'text-green-600' : 'text-red-600'}>
                    Diff: R{overallRecon.difference.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <Link href={currentClient?.id ? `/transactions?client_id=${currentClient.id}&txn_filter=income` : `/transactions?session_id=${sessionId}&txn_filter=income`} className="flex-1">
              <div className="cursor-pointer">
                <p className="text-sm font-medium text-neutral-600">Total Income</p>
                <p className="text-2xl font-bold text-green-600 mt-1">
                  R{overall.total_income?.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </Link>
            <div className="p-3 bg-green-50 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <Link href={currentClient?.id ? `/transactions?client_id=${currentClient.id}&txn_filter=expenses` : `/transactions?session_id=${sessionId}&txn_filter=expenses`} className="flex-1">
              <div className="cursor-pointer">
                <p className="text-sm font-medium text-neutral-600">Total Expenses</p>
                <p className="text-2xl font-bold text-red-600 mt-1">
                  R{overall.total_expenses?.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </Link>
            <div className="p-3 bg-red-50 rounded-lg">
              <TrendingDown className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <Link href={currentClient?.id ? `/transactions?client_id=${currentClient.id}` : `/transactions?session_id=${sessionId}`} className="flex-1">
              <div className="cursor-pointer">
                <p className="text-sm font-medium text-neutral-600">Net Balance</p>
                <p className={`text-2xl font-bold mt-1 ${
                  overall.net_balance >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  R{overall.net_balance?.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </Link>
            
          </div>
        </div>
      </div>

      {/* Monthly Breakdown */}
      {months.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50">
            <h3 className="font-bold text-neutral-900">Monthly Breakdown</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50">
                  <th className="text-left px-4 py-3 font-medium text-neutral-700">Month</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Opening</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Income</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Expenses</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Net</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Expected Closing</th>
                  <th className="text-right px-4 py-3 font-medium text-neutral-700">Actual Closing</th>
                  <th className="text-center px-4 py-3 font-medium text-neutral-700">Status</th>
                  <th className="text-center px-4 py-3 font-medium text-neutral-700">Action</th>
                </tr>
              </thead>
              <tbody>
                {months.map((month: MonthData) => {
                  const rec = reconciliations[month.month] || {}
                  const openingBalance = rec.opening_balance ?? 0
                  const actualClosing = rec.closing_balance
                  const expectedClosing = openingBalance + month.net_balance
                  
                  // Determine reconciliation status
                  let status: 'reconciled' | 'mismatch' | 'pending' = 'pending'
                  let statusIcon = '⚠️'
                  let statusText = 'Pending'
                  let statusColor = 'text-yellow-600'
                  
                  if (actualClosing != null && openingBalance != null) {
                    const difference = Math.abs(actualClosing - expectedClosing)
                    if (difference < 0.01) {
                      status = 'reconciled'
                      statusIcon = '✓'
                      statusText = 'Reconciled'
                      statusColor = 'text-green-600'
                    } else {
                      status = 'mismatch'
                      statusIcon = '✗'
                      statusText = 'Mismatch'
                      statusColor = 'text-red-600'
                    }
                  }
                  
                  // Calculate date range for month (YYYY-MM format)
                  const [year, monthNum] = month.month.split('-')
                  const firstDay = `${month.month}-01`
                  const lastDay = new Date(parseInt(year), parseInt(monthNum), 0).getDate()
                  const lastDayFormatted = `${month.month}-${String(lastDay).padStart(2, '0')}`
                  
                  const handleOpenMonthModal = () => {
                    setSelectedMonth({ month: month.month, data: month })
                    setIsMonthModalOpen(true)
                  }
                  
                  return (
                    <tr key={month.month} className="border-b border-neutral-100 hover:bg-neutral-50">
                      <td className="px-4 py-3 text-neutral-900 font-medium">
                        <button
                          onClick={handleOpenMonthModal}
                          className="hover:text-blue-600 hover:underline cursor-pointer text-left"
                        >
                          {month.month}
                        </button>
                      </td>

                      <td className="text-right px-4 py-3 text-neutral-700">
                        {editingMonth === month.month ? (
                          <input 
                            className="px-2 py-1 border rounded w-full text-right" 
                            value={openInput ?? ''} 
                            onChange={(e) => setOpenInput(e.target.value)} 
                            placeholder="0.00" 
                          />
                        ) : (
                          <span>R{openingBalance.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                        )}
                      </td>

                      <td className="text-right px-4 py-3 text-green-600 font-medium">
                        <button
                          onClick={handleOpenMonthModal}
                          className="hover:underline"
                        >
                          R{month.total_income.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                        </button>
                      </td>
                      
                      <td className="text-right px-4 py-3 text-red-600 font-medium">
                        <button
                          onClick={handleOpenMonthModal}
                          className="hover:underline"
                        >
                          R{month.total_expenses.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                        </button>
                      </td>
                      
                      <td className={`text-right px-4 py-3 font-medium ${
                        month.net_balance >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        <button
                          onClick={handleOpenMonthModal}
                          className="hover:underline"
                        >
                          R{month.net_balance.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                        </button>
                      </td>

                      <td className="text-right px-4 py-3 text-neutral-700 font-medium bg-blue-50">
                        R{expectedClosing.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                      </td>

                      <td className="text-right px-4 py-3 text-neutral-900">
                        {editingMonth === month.month ? (
                          <input 
                            className="px-2 py-1 border rounded w-full text-right" 
                            value={closeInput ?? ''} 
                            onChange={(e) => setCloseInput(e.target.value)} 
                            placeholder="0.00" 
                          />
                        ) : (
                          <span className={actualClosing != null ? 'font-medium' : 'text-neutral-400'}>
                            {actualClosing != null 
                              ? `R${actualClosing.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}` 
                              : 'Not set'}
                          </span>
                        )}
                      </td>

                      <td className={`text-center px-4 py-3 font-medium ${statusColor}`}>
                        <div className="flex items-center justify-center gap-1">
                          <span className="text-base">{statusIcon}</span>
                          <span className="text-xs">{statusText}</span>
                        </div>
                        {status === 'mismatch' && actualClosing != null && (
                          <div className="text-xs text-red-500 mt-1">
                            Diff: R{(actualClosing - expectedClosing).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                          </div>
                        )}
                      </td>

                      <td className="text-center px-4 py-3">
                        {editingMonth === month.month ? (
                          <div className="flex items-center justify-center gap-2">
                            <button 
                              className="px-3 py-1 bg-neutral-900 text-white rounded text-xs font-medium hover:bg-neutral-800" 
                              onClick={async () => {
                                try {
                                  const o = openInput ? parseFloat(openInput) : null
                                  const c = closeInput ? parseFloat(closeInput) : null
                                  const params: any = {}
                                  if (currentClient?.id) {
                                    params.client_id = currentClient.id
                                  } else if (sessionId) {
                                    params.session_id = sessionId
                                  }
                                  await axios.post(`${API_BASE_URL}/reconciliation`, 
                                    { month: month.month, opening_balance: o, closing_balance: c }, 
                                    { params }
                                  )
                                  setReconciliations(prev => ({...prev, [month.month]: { opening_balance: o, closing_balance: c }}))
                                  setEditingMonth(null)
                                } catch (e) {
                                  alert('Failed to save reconciliation')
                                }
                              }}
                            >
                              Save
                            </button>
                            <button 
                              className="px-3 py-1 border border-neutral-300 rounded text-xs hover:bg-neutral-100" 
                              onClick={() => setEditingMonth(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button 
                            className="px-3 py-1 border border-neutral-300 rounded text-xs hover:bg-neutral-100 font-medium" 
                            onClick={() => {
                              setEditingMonth(month.month)
                              setOpenInput(rec.opening_balance != null ? String(rec.opening_balance) : '')
                              setCloseInput(rec.closing_balance != null ? String(rec.closing_balance) : '')
                            }}
                          >
                            Reconcile
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Monthly Transactions Modal */}
      {selectedMonth && (
        <MonthlyTransactionsModal
          isOpen={isMonthModalOpen}
          onClose={() => setIsMonthModalOpen(false)}
          sessionId={sessionId}
          currentClient={currentClient}
          month={selectedMonth.month}
          monthData={selectedMonth.data}
        />
      )}
    </div>
  )
}
