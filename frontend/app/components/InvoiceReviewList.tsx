"use client"

import React, { useEffect, useState, useCallback } from "react"
import { apiFetch } from "@/lib/apiFetch"
import { toast } from 'sonner'
import {
  FileText, RefreshCw, Zap, Package, CheckCircle2, Clock, XCircle,
  AlertTriangle, Loader2, BarChart3
} from 'lucide-react'
import InvoiceMatchCard from "./InvoiceMatchCard"
import UploadInvoiceForm from "./UploadInvoiceForm"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/* ── Types ─────────────────────────────────────────────────────── */

type Invoice = {
  id: number
  supplier_name: string
  invoice_date: string
  invoice_number?: string
  total_amount: number
  vat_amount?: number | null
  file_reference?: string | null
}

type MatchInfo = {
  match_status?: string | null
  suggested_transaction_id?: number | null
  transaction?: { id: number; date: string; description: string; amount: number } | null
  confidence?: number | null
  explanation?: string | null
}

type InvoiceWithMatch = Invoice & MatchInfo

type FilterTab = 'all' | 'review' | 'confirmed' | 'rejected' | 'unmatched'

/* ── Tabs config ───────────────────────────────────────────────── */

const TABS: { key: FilterTab; label: string; icon: React.ElementType }[] = [
  { key: 'all',       label: 'All',        icon: Package },
  { key: 'review',    label: 'To Review',  icon: Clock },
  { key: 'confirmed', label: 'Confirmed',  icon: CheckCircle2 },
  { key: 'rejected',  label: 'Rejected',   icon: XCircle },
  { key: 'unmatched', label: 'Unmatched',  icon: AlertTriangle },
]

/* ── Component ─────────────────────────────────────────────────── */

export default function InvoiceReviewList({ sessionId }: { sessionId: string | null }) {
  const [items, setItems] = useState<InvoiceWithMatch[]>([])
  const [loading, setLoading] = useState(false)
  const [matching, setMatching] = useState(false)
  const [filter, setFilter] = useState<FilterTab>('all')

  /* ── Data fetching ───────────────────────────────────────────── */
  const loadAll = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const [invRes, matchRes] = await Promise.all([
        apiFetch(`${API_BASE}/invoices?session_id=${encodeURIComponent(sessionId)}`),
        apiFetch(`${API_BASE}/invoice/matches?session_id=${encodeURIComponent(sessionId)}`),
      ])

      const invoices: Invoice[] = invRes.invoices || []
      const matchArr = Array.isArray(matchRes.matches) ? matchRes.matches : []
      const matchMap: Record<number, MatchInfo> = {}
      matchArr.forEach((m: any) => {
        matchMap[m.invoice_id] = {
          match_status: m.match_status,
          suggested_transaction_id: m.suggested_transaction_id,
          transaction: m.transaction,
          confidence: m.confidence,
          explanation: m.explanation,
        }
      })

      setItems(invoices.map(inv => ({ ...inv, ...(matchMap[inv.id] || {}) })))
    } catch {
      toast.error('Failed to load invoices')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { loadAll() }, [loadAll])

  const runMatch = async () => {
    if (!sessionId) return
    setMatching(true)
    try {
      await apiFetch(`${API_BASE}/invoice/match?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' })
      toast.success('Matching complete')
      await loadAll()
    } catch (e) {
      toast.error('Matching failed: ' + String(e))
    } finally {
      setMatching(false)
    }
  }

  /* ── Stats ───────────────────────────────────────────────────── */
  const total     = items.length
  const confirmed = items.filter(i => i.match_status === 'confirmed').length
  const review    = items.filter(i => i.match_status === 'suggested').length
  const rejected  = items.filter(i => i.match_status === 'rejected').length
  const unmatched = items.filter(i => !i.match_status).length

  const totalValue = items.reduce((s, i) => s + Math.abs(i.total_amount), 0)
  const matchedValue = items.filter(i => i.match_status === 'confirmed').reduce((s, i) => s + Math.abs(i.total_amount), 0)

  /* ── Filtering ───────────────────────────────────────────────── */
  const filtered = items.filter(i => {
    if (filter === 'all')       return true
    if (filter === 'review')    return i.match_status === 'suggested'
    if (filter === 'confirmed') return i.match_status === 'confirmed'
    if (filter === 'rejected')  return i.match_status === 'rejected'
    if (filter === 'unmatched') return !i.match_status
    return true
  })

  const tabCount = (key: FilterTab) => {
    if (key === 'all')       return total
    if (key === 'review')    return review
    if (key === 'confirmed') return confirmed
    if (key === 'rejected')  return rejected
    if (key === 'unmatched') return unmatched
    return 0
  }

  /* ── Stats cards const ───────────────────────────────────────── */
  const STATS = [
    { label: 'Total Invoices', value: total,     sub: `R ${totalValue.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}` },
    { label: 'To Review',      value: review,    sub: 'Awaiting confirmation' },
    { label: 'Confirmed',      value: confirmed, sub: `R ${matchedValue.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}` },
    { label: 'Unmatched',      value: unmatched, sub: 'No transaction match' },
  ]

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-100">
            <FileText className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-neutral-900">Invoice Management</h1>
            <p className="text-sm text-neutral-500">Upload invoices, auto-extract details, and match to bank transactions</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={runMatch}
            disabled={matching || loading || !sessionId || total === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
            {matching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            {matching ? 'Matching...' : 'Run Matching'}
          </button>
          <button onClick={() => loadAll()}
            disabled={loading || !sessionId}
            className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Stats cards ────────────────────────────────────────── */}
      {total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {STATS.map(s => (
            <div key={s.label} className="rounded-xl border border-neutral-200 bg-white px-4 py-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-neutral-400 mb-1">{s.label}</p>
              <p className="text-2xl font-bold text-neutral-900 tabular-nums">{s.value}</p>
              <p className="text-[11px] text-neutral-400 mt-0.5 truncate">{s.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Upload section ─────────────────────────────────────── */}
      <UploadInvoiceForm sessionId={sessionId} onUploaded={loadAll} />

      {/* ── Loading ────────────────────────────────────────────── */}
      {loading && total === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      )}

      {/* ── Filter tabs + list ─────────────────────────────────── */}
      {total > 0 && (
        <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
          {/* Tabs */}
          <div className="flex items-center gap-1 px-4 pt-4 pb-3 border-b border-neutral-100 overflow-x-auto">
            {TABS.map(tab => {
              const Icon = tab.icon
              const count = tabCount(tab.key)
              const active = filter === tab.key
              return (
                <button key={tab.key} onClick={() => setFilter(tab.key)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors ${
                    active ? 'bg-blue-50 text-blue-700' : 'text-neutral-500 hover:text-neutral-700 hover:bg-neutral-50'
                  }`}>
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                  <span className={`ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                    active ? 'bg-blue-100 text-blue-700' : 'bg-neutral-100 text-neutral-500'
                  }`}>{count}</span>
                </button>
              )
            })}
          </div>

          {/* Cards */}
          <div className="divide-y divide-neutral-100">
            {filtered.length === 0 ? (
              <div className="py-14 text-center">
                <Package className="w-8 h-8 text-neutral-300 mx-auto mb-2" />
                <p className="text-sm text-neutral-400">No invoices in this category</p>
              </div>
            ) : (
              filtered.map(item => (
                <InvoiceMatchCard
                  key={item.id}
                  invoice={item}
                  suggested={item.match_status ? {
                    transaction: item.transaction || undefined,
                    confidence: item.confidence ?? undefined,
                    classification: item.match_status === 'confirmed' ? 'High' : ((item.confidence ?? 0) >= 80 ? 'High' : (item.confidence ?? 0) >= 50 ? 'Medium' : 'Low'),
                    explanation: item.explanation ?? undefined,
                    status: item.match_status ?? undefined,
                  } : undefined}
                  sessionId={sessionId}
                  onUpdate={loadAll}
                />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Empty state ────────────────────────────────────────── */}
      {!loading && total === 0 && (
        <div className="rounded-xl border-2 border-dashed border-neutral-200 bg-white py-16 text-center">
          <BarChart3 className="w-10 h-10 text-neutral-300 mx-auto mb-3" />
          <p className="text-sm font-medium text-neutral-600 mb-1">No invoices uploaded yet</p>
          <p className="text-xs text-neutral-400 max-w-sm mx-auto">
            Upload your first invoice above. We'll automatically extract the supplier, amount and date, then match it to your bank transactions.
          </p>
        </div>
      )}

      {/* ── Disclaimer footer ──────────────────────────────────── */}
      <div className="rounded-lg bg-neutral-50 border border-neutral-100 px-4 py-3">
        <p className="text-[11px] text-neutral-500">
          <span className="font-semibold text-neutral-600">Disclaimer:</span> Matches are suggestions only. No accounting entries or VAT claims are made automatically. Confirm each match before taking action.
        </p>
      </div>
    </div>
  )
}
