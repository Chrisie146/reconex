'use client'

import React, { useState, useEffect } from 'react'
import { ArrowLeft, CalendarRange, FileText, Archive, BarChart3, Receipt, Download } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { useParams, useRouter } from 'next/navigation'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Tab = 'overview' | 'transactions' | 'sessions' | 'reconciliation' | 'invoices'

interface FinancialYear {
  id: number
  label: string
  year_start: string
  year_end: string
  status: string
  archived_at: string | null
}

interface ArchivedTransaction {
  id: number
  original_id: number
  session_id: string
  date: string
  description: string
  amount: number
  category: string
  vat_amount: number | null
  bank_source: string | null
}

interface ArchivedSession {
  session_id: string
  friendly_name: string
  locked: boolean
  transaction_count: number
  date_from: string | null
  date_to: string | null
}

interface ReconciliationData {
  monthly: Array<{ month: string; session_id: string; opening_balance: number | null; closing_balance: number | null }>
  overall: Array<{ session_id: string; system_opening_balance: number | null; bank_closing_balance: number | null }>
}

interface ArchivedInvoice {
  id: number
  original_id: number
  session_id: string
  supplier_name: string
  invoice_date: string
  invoice_number: string | null
  total_amount: number
  vat_amount: number | null
}

interface Summary {
  total_income: number
  total_expenses: number
  net: number
  by_category: Array<{ category: string; total: number; count: number }>
}

const fmt = (n: number) =>
  new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(n)

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-ZA')

export default function ArchivedYearPage() {
  const params = useParams()
  const router = useRouter()
  const fyId = Number(params.id)

  const [tab, setTab] = useState<Tab>('overview')
  const [fy, setFy] = useState<FinancialYear | null>(null)

  const [summary, setSummary]             = useState<Summary | null>(null)
  const [transactions, setTransactions]   = useState<ArchivedTransaction[]>([])
  const [txnTotal, setTxnTotal]           = useState(0)
  const [txnPage, setTxnPage]             = useState(1)
  const [txnSearch, setTxnSearch]         = useState('')
  const [txnCategory, setTxnCategory]     = useState('')
  const [sessions, setSessions]           = useState<ArchivedSession[]>([])
  const [reconciliation, setReconciliation] = useState<ReconciliationData | null>(null)
  const [invoices, setInvoices]           = useState<ArchivedInvoice[]>([])

  const [loading, setLoading]             = useState(true)
  const [downloading, setDownloading]     = useState(false)
  const [clientName, setClientName]       = useState<string | null>(null)

  // Load financial year metadata + initial tab
  useEffect(() => {
    if (!fyId) return
    loadSummary()
    loadSessions()
  }, [fyId])

  // Load tab data on demand
  useEffect(() => {
    if (!fyId) return
    if (tab === 'transactions') loadTransactions(1, txnSearch, txnCategory)
    if (tab === 'reconciliation') loadReconciliation()
    if (tab === 'invoices') loadInvoices()
  }, [tab, fyId])

  const loadSummary = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years/${fyId}/summary`)
      setFy(res.data.financial_year)
      setSummary(res.data)
      if (res.data.client_name) setClientName(res.data.client_name)
    } catch {
      toast.error('Failed to load archived year data.')
    } finally {
      setLoading(false)
    }
  }

  const loadTransactions = async (page: number, search: string, category: string) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years/${fyId}/transactions`, {
        params: { page, page_size: 100, search: search || undefined, category: category || undefined }
      })
      setFy(res.data.financial_year)
      setTransactions(res.data.transactions)
      setTxnTotal(res.data.total)
      setTxnPage(page)
    } catch {
      toast.error('Failed to load transactions.')
    }
  }

  const loadSessions = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years/${fyId}/sessions`)
      setSessions(res.data.sessions)
    } catch {
      toast.error('Failed to load sessions.')
    }
  }

  const loadReconciliation = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years/${fyId}/reconciliation`)
      setReconciliation(res.data)
    } catch {
      toast.error('Failed to load reconciliation data.')
    }
  }

  const loadInvoices = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years/${fyId}/invoices`)
      setInvoices(res.data.invoices)
    } catch {
      toast.error('Failed to load invoices.')
    }
  }

  const handleTransactionSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadTransactions(1, txnSearch, txnCategory)
  }

  const handleDownloadCSV = async () => {
    if (!fyId) return
    setDownloading(true)
    try {
      const token = typeof window !== 'undefined'
        ? localStorage.getItem('statement_analyzer_auth_token') : null
      const response = await fetch(
        `${API_BASE_URL}/financial-years/${fyId}/transactions?page=1&page_size=10000`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const data = await response.json()
      const rows = data.transactions as ArchivedTransaction[]

      // Build CSV
      const headers = ['Date', 'Description', 'Amount', 'Category', 'VAT Amount', 'Bank Source', 'Session ID']
      const meta = [
        clientName ? `Client: ${clientName}` : null,
        `Period: ${fy?.label ?? 'archive'}`,
        `Generated: ${new Date().toLocaleDateString('en-ZA')}`,
      ].filter(Boolean)
      const lines = [
        ...meta.map(m => `# ${m}`),
        headers.join(','),
        ...rows.map(t => [
          t.date,
          `"${t.description.replace(/"/g, '""')}"`,
          t.amount,
          t.category,
          t.vat_amount ?? '',
          t.bank_source ?? '',
          t.session_id,
        ].join(','))
      ]
      const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const clientSlug = clientName ? clientName.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 24) + '_' : ''
      a.download = `${clientSlug}${fy?.label ?? 'archive'}_transactions.csv`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
      toast.success('CSV downloaded.')
    } catch {
      toast.error('Export failed.')
    } finally {
      setDownloading(false)
    }
  }

  const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: 'overview',      label: 'Overview',       icon: <BarChart3 size={16} /> },
    { id: 'transactions',  label: 'Transactions',   icon: <FileText size={16} /> },
    { id: 'sessions',      label: 'Sessions',       icon: <Archive size={16} /> },
    { id: 'reconciliation',label: 'Reconciliation', icon: <CalendarRange size={16} /> },
    { id: 'invoices',      label: 'Invoices',       icon: <Receipt size={16} /> },
  ]

  if (loading) {
    return (
      <main className="bg-white min-h-screen">
        <Sidebar sessionId={null} />
        <div className="flex items-center justify-center h-screen" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </main>
    )
  }

  return (
    <main className="bg-white min-h-screen">
      <Sidebar sessionId={null} />

      <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
        <Header />

        <div className="max-w-7xl mx-auto px-6 py-12">
          {/* Back + header */}
          <div className="flex items-center gap-4 mb-6">
            <button
              onClick={() => router.push('/financial-years')}
              className="p-2 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <div className="flex items-center gap-3">
                <CalendarRange className="text-neutral-400" size={24} />
                <h1 className="text-2xl font-bold text-neutral-900">
                  {fy?.label ?? 'Archived Year'} — Read-only
                </h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-500 border border-neutral-200">
                  Archived
                </span>
              </div>
              {fy && (
                <p className="text-neutral-500 mt-1 text-sm ml-9">
                  {fmtDate(fy.year_start)} – {fmtDate(fy.year_end)}
                  {fy.archived_at && ` · Archived ${fmtDate(fy.archived_at)}`}
                </p>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 border-b border-neutral-200 mb-6">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px
                  ${tab === t.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700'
                  }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>

          {/* ── Overview ────────────────────────────────────────────────── */}
          {tab === 'overview' && summary && (
            <div className="space-y-6">
              {/* KPI cards */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide mb-1">Total Income</p>
                  <p className="text-2xl font-bold text-emerald-700">{fmt(summary.total_income)}</p>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-red-600 uppercase tracking-wide mb-1">Total Expenses</p>
                  <p className="text-2xl font-bold text-red-700">{fmt(summary.total_expenses)}</p>
                </div>
                <div className={`border rounded-lg p-4 ${summary.net >= 0 ? 'bg-blue-50 border-blue-200' : 'bg-orange-50 border-orange-200'}`}>
                  <p className={`text-xs font-medium uppercase tracking-wide mb-1 ${summary.net >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>Net</p>
                  <p className={`text-2xl font-bold ${summary.net >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>{fmt(summary.net)}</p>
                </div>
              </div>

              {/* Category breakdown */}
              <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-neutral-100">
                  <h3 className="font-semibold text-neutral-900">By Category</h3>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 border-b border-neutral-100">
                    <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                      <th className="px-6 py-3">Category</th>
                      <th className="px-6 py-3 text-right">Transactions</th>
                      <th className="px-6 py-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {summary.by_category
                      .sort((a, b) => Math.abs(b.total) - Math.abs(a.total))
                      .map(row => (
                        <tr key={row.category} className="hover:bg-neutral-50">
                          <td className="px-6 py-3 font-medium text-neutral-900">{row.category}</td>
                          <td className="px-6 py-3 text-right text-neutral-600">{row.count}</td>
                          <td className={`px-6 py-3 text-right font-medium ${row.total >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {fmt(row.total)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Transactions ─────────────────────────────────────────────── */}
          {tab === 'transactions' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 justify-between">
                <form onSubmit={handleTransactionSearch} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Search description..."
                    value={txnSearch}
                    onChange={e => setTxnSearch(e.target.value)}
                    className="px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
                  />
                  <input
                    type="text"
                    placeholder="Category filter..."
                    value={txnCategory}
                    onChange={e => setTxnCategory(e.target.value)}
                    className="px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-44"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
                  >
                    Search
                  </button>
                </form>
                <button
                  onClick={handleDownloadCSV}
                  disabled={downloading}
                  className="flex items-center gap-2 px-4 py-2 border border-neutral-200 text-neutral-700 rounded-lg text-sm hover:bg-neutral-50 transition-colors disabled:opacity-50"
                >
                  <Download size={16} />
                  {downloading ? 'Downloading...' : 'Export CSV'}
                </button>
              </div>

              <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
                <div className="px-6 py-3 bg-neutral-50 border-b border-neutral-200 text-sm text-neutral-600">
                  {txnTotal.toLocaleString()} transactions
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-100">
                      <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                        <th className="px-6 py-3">Date</th>
                        <th className="px-6 py-3">Description</th>
                        <th className="px-6 py-3">Category</th>
                        <th className="px-6 py-3 text-right">Amount</th>
                        <th className="px-6 py-3 text-right">VAT</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {transactions.map(t => (
                        <tr key={t.id} className="hover:bg-neutral-50">
                          <td className="px-6 py-3 text-neutral-600 whitespace-nowrap">{fmtDate(t.date)}</td>
                          <td className="px-6 py-3 text-neutral-900 max-w-xs truncate">{t.description}</td>
                          <td className="px-6 py-3">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
                              {t.category}
                            </span>
                          </td>
                          <td className={`px-6 py-3 text-right font-medium ${t.amount >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {fmt(t.amount)}
                          </td>
                          <td className="px-6 py-3 text-right text-neutral-500">
                            {t.vat_amount != null ? fmt(t.vat_amount) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {txnTotal > 100 && (
                  <div className="flex items-center justify-between px-6 py-3 border-t border-neutral-100 text-sm text-neutral-600">
                    <span>Page {txnPage} · showing {transactions.length} of {txnTotal}</span>
                    <div className="flex gap-2">
                      <button
                        disabled={txnPage <= 1}
                        onClick={() => loadTransactions(txnPage - 1, txnSearch, txnCategory)}
                        className="px-3 py-1.5 border border-neutral-200 rounded text-sm hover:bg-neutral-50 disabled:opacity-40 transition-colors"
                      >
                        Previous
                      </button>
                      <button
                        disabled={txnPage * 100 >= txnTotal}
                        onClick={() => loadTransactions(txnPage + 1, txnSearch, txnCategory)}
                        className="px-3 py-1.5 border border-neutral-200 rounded text-sm hover:bg-neutral-50 disabled:opacity-40 transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Sessions ─────────────────────────────────────────────────── */}
          {tab === 'sessions' && (
            <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                    <th className="px-6 py-4">Statement Name</th>
                    <th className="px-6 py-4">Date Range</th>
                    <th className="px-6 py-4 text-right">Transactions</th>
                    <th className="px-6 py-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {sessions.map(s => (
                    <tr key={s.session_id} className="hover:bg-neutral-50">
                      <td className="px-6 py-4 font-medium text-neutral-900">{s.friendly_name}</td>
                      <td className="px-6 py-4 text-neutral-600">
                        {s.date_from && s.date_to
                          ? `${fmtDate(s.date_from)} – ${fmtDate(s.date_to)}`
                          : '—'}
                      </td>
                      <td className="px-6 py-4 text-right text-neutral-700">{s.transaction_count.toLocaleString()}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${s.locked ? 'bg-green-100 text-green-700' : 'bg-neutral-100 text-neutral-600'}`}>
                          {s.locked ? 'Locked' : 'Unlocked'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Reconciliation ───────────────────────────────────────────── */}
          {tab === 'reconciliation' && reconciliation && (
            <div className="space-y-6">
              <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-neutral-100">
                  <h3 className="font-semibold text-neutral-900">Monthly Balances</h3>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 border-b border-neutral-100">
                    <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                      <th className="px-6 py-3">Month</th>
                      <th className="px-6 py-3">Session</th>
                      <th className="px-6 py-3 text-right">Opening</th>
                      <th className="px-6 py-3 text-right">Closing</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {reconciliation.monthly.map((r, i) => (
                      <tr key={i} className="hover:bg-neutral-50">
                        <td className="px-6 py-3 font-medium text-neutral-900">{r.month}</td>
                        <td className="px-6 py-3 text-neutral-500 text-xs font-mono">{r.session_id}</td>
                        <td className="px-6 py-3 text-right text-neutral-700">{r.opening_balance != null ? fmt(r.opening_balance) : '—'}</td>
                        <td className="px-6 py-3 text-right text-neutral-700">{r.closing_balance != null ? fmt(r.closing_balance) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {reconciliation.overall.length > 0 && (
                <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
                  <div className="px-6 py-4 border-b border-neutral-100">
                    <h3 className="font-semibold text-neutral-900">Overall Reconciliation</h3>
                  </div>
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-100">
                      <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                        <th className="px-6 py-3">Session</th>
                        <th className="px-6 py-3 text-right">Opening Balance</th>
                        <th className="px-6 py-3 text-right">Bank Closing</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {reconciliation.overall.map((o, i) => (
                        <tr key={i} className="hover:bg-neutral-50">
                          <td className="px-6 py-3 text-neutral-500 text-xs font-mono">{o.session_id}</td>
                          <td className="px-6 py-3 text-right text-neutral-700">{o.system_opening_balance != null ? fmt(o.system_opening_balance) : '—'}</td>
                          <td className="px-6 py-3 text-right text-neutral-700">{o.bank_closing_balance != null ? fmt(o.bank_closing_balance) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Invoices ─────────────────────────────────────────────────── */}
          {tab === 'invoices' && (
            <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                    <th className="px-6 py-4">Supplier</th>
                    <th className="px-6 py-4">Invoice Date</th>
                    <th className="px-6 py-4">Invoice #</th>
                    <th className="px-6 py-4 text-right">Amount</th>
                    <th className="px-6 py-4 text-right">VAT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {invoices.map(inv => (
                    <tr key={inv.id} className="hover:bg-neutral-50">
                      <td className="px-6 py-4 font-medium text-neutral-900">{inv.supplier_name}</td>
                      <td className="px-6 py-4 text-neutral-600">{fmtDate(inv.invoice_date)}</td>
                      <td className="px-6 py-4 text-neutral-500">{inv.invoice_number ?? '—'}</td>
                      <td className="px-6 py-4 text-right font-medium text-neutral-900">{fmt(inv.total_amount)}</td>
                      <td className="px-6 py-4 text-right text-neutral-500">{inv.vat_amount != null ? fmt(inv.vat_amount) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {invoices.length === 0 && (
                <div className="text-center py-12 text-neutral-400">No invoices archived for this year.</div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
