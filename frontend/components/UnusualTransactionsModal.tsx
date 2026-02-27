'use client'

import { useState, useCallback } from 'react'
import {
  AlertTriangle, X, Search, ChevronDown, ChevronUp,
  Download, Loader2, CalendarX, Copy, RefreshCw,
  TrendingUp, TrendingDown, Circle
} from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { API_BASE_URL } from '@/lib/apiBase'

/* ── Types ────────────────────────────────────────────────────────── */
interface UnusualTransactionsModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
  clientId?: number | null
}

interface FlaggedTransaction {
  id: number
  date: string
  description: string
  amount: number
  category: string | null
  merchant: string
  flags: string[]
}

interface ReportResult {
  total: number
  transactions: FlaggedTransaction[]
}

/* ── Flag label helpers ───────────────────────────────────────────── */
const FLAG_META: Record<string, { label: string; colour: string }> = {
  above_threshold: { label: 'Above threshold',  colour: 'bg-red-500/20 text-red-300 border-red-500/30' },
  below_threshold: { label: 'Below threshold',  colour: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
  round_amount:    { label: 'Round amount',      colour: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  recurring:       { label: 'Recurring',         colour: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
  duplicate:       { label: 'Possible duplicate',colour: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
  weekend:         { label: 'Weekend',           colour: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
}

function FlagBadge({ flag }: { flag: string }) {
  const meta = FLAG_META[flag] ?? { label: flag, colour: 'bg-slate-500/20 text-slate-300 border-slate-500/30' }
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${meta.colour}`}>
      {meta.label}
    </span>
  )
}

/* ── Number input helper ──────────────────────────────────────────── */
function NumInput({ value, onChange, placeholder, min }: {
  value: string; onChange: (v: string) => void; placeholder: string; min?: number
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      placeholder={placeholder}
      onChange={e => onChange(e.target.value)}
      className="w-28 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:border-blue-500"
    />
  )
}

/* ── Checkbox row ─────────────────────────────────────────────────── */
function CriteriaRow({
  enabled, setEnabled, label, icon, children,
}: {
  enabled: boolean
  setEnabled: (v: boolean) => void
  label: string
  icon: React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <div className={`flex flex-col gap-2 p-3 rounded-lg border transition-colors ${
      enabled ? 'border-blue-500/40 bg-blue-500/5' : 'border-slate-700 bg-slate-800/40'
    }`}>
      <label className="flex items-center gap-2.5 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={e => setEnabled(e.target.checked)}
          className="w-4 h-4 accent-blue-500 cursor-pointer"
        />
        <span className="text-neutral-400">{icon}</span>
        <span className="text-sm font-medium text-neutral-200">{label}</span>
      </label>
      {enabled && children && (
        <div className="flex items-center gap-2 pl-6 flex-wrap">
          {children}
        </div>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════
   MODAL
   ══════════════════════════════════════════════════════════════════════ */
export default function UnusualTransactionsModal({
  isOpen, onClose, sessionId, clientId,
}: UnusualTransactionsModalProps) {
  /* ── Criteria state ───────────────────────────────────────────── */
  const [aboveEnabled, setAboveEnabled]   = useState(false)
  const [aboveAmount, setAboveAmount]     = useState('10000')
  const [belowEnabled, setBelowEnabled]   = useState(false)
  const [belowAmount, setBelowAmount]     = useState('10')
  const [roundEnabled, setRoundEnabled]   = useState(false)
  const [roundMultiple, setRoundMultiple] = useState('100')
  const [recurEnabled, setRecurEnabled]   = useState(false)
  const [recurCount, setRecurCount]       = useState('2')
  const [dupeEnabled, setDupeEnabled]     = useState(false)
  const [dupeDays, setDupeDays]           = useState('3')
  const [weekendEnabled, setWeekendEnabled] = useState(false)

  /* ── Results state ────────────────────────────────────────────── */
  const [loading, setLoading]             = useState(false)
  const [result, setResult]               = useState<ReportResult | null>(null)
  const [step, setStep]                   = useState<'criteria' | 'results'>('criteria')
  const [sortCol, setSortCol]             = useState<'date' | 'amount' | 'flags'>('date')
  const [sortDir, setSortDir]             = useState<'asc' | 'desc'>('asc')
  const [exporting, setExporting]         = useState(false)

  const anyEnabled = aboveEnabled || belowEnabled || roundEnabled || recurEnabled || dupeEnabled || weekendEnabled

  /* ── Run report ───────────────────────────────────────────────── */
  const handleRun = useCallback(async () => {
    if (!anyEnabled) { toast.error('Please enable at least one criterion.'); return }
    setLoading(true)
    try {
      const params: Record<string, unknown> = {}
      if (sessionId)  params.session_id = sessionId
      if (clientId)   params.client_id  = clientId
      if (aboveEnabled && aboveAmount) params.above_amount = parseFloat(aboveAmount)
      if (belowEnabled && belowAmount) params.below_amount = parseFloat(belowAmount)
      if (roundEnabled) {
        params.round_amount   = true
        params.round_multiple = parseInt(roundMultiple) || 100
      }
      if (recurEnabled) {
        params.recurring           = true
        params.recurring_min_count = parseInt(recurCount) || 3
      }
      if (dupeEnabled) {
        params.duplicates             = true
        params.duplicate_window_days  = parseInt(dupeDays) || 3
      }
      if (weekendEnabled) params.weekend = true

      const res = await axios.get(`${API_BASE_URL}/unusual`, { params })
      setResult(res.data)
      setStep('results')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Report failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [anyEnabled, sessionId, clientId, aboveEnabled, aboveAmount, belowEnabled, belowAmount,
      roundEnabled, roundMultiple, recurEnabled, recurCount, dupeEnabled, dupeDays, weekendEnabled])

  /* ── Sort ─────────────────────────────────────────────────────── */
  const sorted = result ? [...result.transactions].sort((a, b) => {
    let cmp = 0
    if (sortCol === 'date')   cmp = a.date.localeCompare(b.date)
    if (sortCol === 'amount') cmp = Math.abs(a.amount) - Math.abs(b.amount)
    if (sortCol === 'flags')  cmp = a.flags.length - b.flags.length
    return sortDir === 'asc' ? cmp : -cmp
  }) : []

  const toggleSort = (col: typeof sortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const SortIcon = ({ col }: { col: typeof sortCol }) => {
    if (sortCol !== col) return null
    return sortDir === 'asc'
      ? <ChevronUp className="w-3 h-3 inline ml-0.5" />
      : <ChevronDown className="w-3 h-3 inline ml-0.5" />
  }

  /* ── Export Excel ─────────────────────────────────────────────── */
  const handleExportExcel = useCallback(async () => {
    if (!result?.transactions?.length) return
    setExporting(true)
    try {
      const params: Record<string, unknown> = {}
      if (sessionId)  params.session_id = sessionId
      if (clientId)   params.client_id  = clientId
      if (aboveEnabled && aboveAmount) params.above_amount = parseFloat(aboveAmount)
      if (belowEnabled && belowAmount) params.below_amount = parseFloat(belowAmount)
      if (roundEnabled) {
        params.round_amount   = true
        params.round_multiple = parseInt(roundMultiple) || 100
      }
      if (recurEnabled) {
        params.recurring           = true
        params.recurring_min_count = parseInt(recurCount) || 2
      }
      if (dupeEnabled) {
        params.duplicates            = true
        params.duplicate_window_days = parseInt(dupeDays) || 3
      }
      if (weekendEnabled) params.weekend = true

      const res = await axios.get(`${API_BASE_URL}/unusual/export`, {
        params,
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([res.data]))
      const a   = document.createElement('a')
      a.href = url
      a.download = `unusual_transactions_${new Date().toISOString().slice(0, 10)}.xlsx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
      toast.success('Excel exported')
    } catch { toast.error('Excel export failed') }
    finally { setExporting(false) }
  }, [result, sessionId, clientId, aboveEnabled, aboveAmount, belowEnabled, belowAmount,
      roundEnabled, roundMultiple, recurEnabled, recurCount, dupeEnabled, dupeDays, weekendEnabled])

  /* ── Export CSV ───────────────────────────────────────────────── */
  const handleExportCSV = useCallback(() => {
    if (!result?.transactions?.length) return
    setExporting(true)
    try {
      const headers = ['Date','Description','Merchant','Amount','Category','Flags']
      const rows = sorted.map(t => [
        t.date,
        `"${t.description.replace(/"/g, '""')}"`,
        `"${(t.merchant || '').replace(/"/g, '""')}"`,
        t.amount.toFixed(2),
        `"${(t.category || '').replace(/"/g, '""')}"`,
        `"${t.flags.map(f => FLAG_META[f]?.label ?? f).join('; ')}"`,
      ])
      const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      a.download = `unusual_transactions_${new Date().toISOString().slice(0,10)}.csv`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
      toast.success('CSV exported')
    } catch { toast.error('Export failed') }
    finally { setExporting(false) }
  }, [result, sorted])

  /* ── Reset ────────────────────────────────────────────────────── */
  const handleBack = () => { setStep('criteria'); setResult(null) }

  const handleClose = () => {
    setStep('criteria')
    setResult(null)
    onClose()
  }

  if (!isOpen) return null

  /* ── Format currency ──────────────────────────────────────────── */
  const fmt = (n: number) =>
    new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(n)

  /* ── Render ───────────────────────────────────────────────────── */
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-3xl mx-4 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-neutral-100">Unusual Transactions</h2>
              <p className="text-xs text-neutral-500">
                {step === 'criteria' ? 'Select criteria to flag irregular transactions' : `${result?.total ?? 0} transaction${result?.total === 1 ? '' : 's'} flagged`}
              </p>
            </div>
          </div>
          <button onClick={handleClose}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-slate-800 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Step: Criteria ──────────────────────────────────────── */}
        {step === 'criteria' && (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-3">

              <CriteriaRow
                enabled={aboveEnabled} setEnabled={setAboveEnabled}
                label="Amounts above a threshold"
                icon={<TrendingUp className="w-4 h-4 text-red-400" />}>
                <span className="text-xs text-neutral-400">Amount &gt;</span>
                <NumInput value={aboveAmount} onChange={setAboveAmount} placeholder="10000" min={0} />
              </CriteriaRow>

              <CriteriaRow
                enabled={belowEnabled} setEnabled={setBelowEnabled}
                label="Amounts below a threshold"
                icon={<TrendingDown className="w-4 h-4 text-yellow-400" />}>
                <span className="text-xs text-neutral-400">Amount &lt;</span>
                <NumInput value={belowAmount} onChange={setBelowAmount} placeholder="10" min={0} />
              </CriteriaRow>

              <CriteriaRow
                enabled={roundEnabled} setEnabled={setRoundEnabled}
                label="Round amounts"
                icon={<Circle className="w-4 h-4 text-blue-400" />}>
                <span className="text-xs text-neutral-400">Divisible by</span>
                <NumInput value={roundMultiple} onChange={setRoundMultiple} placeholder="100" min={1} />
              </CriteriaRow>

              <CriteriaRow
                enabled={recurEnabled} setEnabled={setRecurEnabled}
                label="Recurring transactions"
                icon={<RefreshCw className="w-4 h-4 text-purple-400" />}>
                <span className="text-xs text-neutral-400">Same description + amount appearing at least</span>
                <NumInput value={recurCount} onChange={setRecurCount} placeholder="2" min={2} />
                <span className="text-xs text-neutral-400">times</span>
              </CriteriaRow>

              <CriteriaRow
                enabled={dupeEnabled} setEnabled={setDupeEnabled}
                label="Possible duplicates"
                icon={<Copy className="w-4 h-4 text-orange-400" />}>
                <span className="text-xs text-neutral-400">Same description + amount within</span>
                <NumInput value={dupeDays} onChange={setDupeDays} placeholder="3" min={1} />
                <span className="text-xs text-neutral-400">days</span>
              </CriteriaRow>

              <CriteriaRow
                enabled={weekendEnabled} setEnabled={setWeekendEnabled}
                label="Weekend transactions (Saturday / Sunday)"
                icon={<CalendarX className="w-4 h-4 text-teal-400" />}
              />
            </div>

            <div className="px-6 py-4 border-t border-slate-800 flex justify-end gap-3 shrink-0">
              <button onClick={handleClose}
                className="px-4 py-2 rounded-lg text-sm text-neutral-400 hover:text-neutral-200 hover:bg-slate-800 transition-colors">
                Cancel
              </button>
              <button
                onClick={handleRun}
                disabled={!anyEnabled || loading}
                className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                {loading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
                  : <><Search className="w-4 h-4" /> Run Report</>
                }
              </button>
            </div>
          </>
        )}

        {/* ── Step: Results ────────────────────────────────────────── */}
        {step === 'results' && result && (
          <>
            {/* Summary bar */}
            <div className="px-6 py-3 border-b border-slate-800 bg-slate-800/40 shrink-0 flex flex-wrap items-center gap-4">
              <div className="text-sm text-neutral-300">
                <span className="font-semibold text-white">{result.total}</span> flagged transaction{result.total !== 1 ? 's' : ''}
              </div>
              {/* Flag breakdown */}
              {Object.entries(
                sorted.reduce<Record<string, number>>((acc, t) => {
                  t.flags.forEach(f => { acc[f] = (acc[f] ?? 0) + 1 })
                  return acc
                }, {})
              ).map(([flag, cnt]) => (
                <span key={flag}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${FLAG_META[flag]?.colour ?? 'bg-slate-600 text-slate-200 border-slate-500'}`}>
                  {FLAG_META[flag]?.label ?? flag}: {cnt}
                </span>
              ))}
            </div>

            {/* Table */}
            {result.total === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-16 text-neutral-500 gap-3">
                <AlertTriangle className="w-10 h-10 text-neutral-700" />
                <p className="text-sm">No transactions matched the selected criteria.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                    <tr>
                      <th
                        className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400 cursor-pointer hover:text-neutral-200 select-none"
                        onClick={() => toggleSort('date')}>
                        Date <SortIcon col="date" />
                      </th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Description</th>
                      <th
                        className="px-4 py-2.5 text-right text-xs font-semibold text-neutral-400 cursor-pointer hover:text-neutral-200 select-none"
                        onClick={() => toggleSort('amount')}>
                        Amount <SortIcon col="amount" />
                      </th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Category</th>
                      <th
                        className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400 cursor-pointer hover:text-neutral-200 select-none"
                        onClick={() => toggleSort('flags')}>
                        Flags <SortIcon col="flags" />
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {sorted.map(t => (
                      <tr key={t.id} className="hover:bg-slate-800/50 transition-colors">
                        <td className="px-4 py-2.5 text-neutral-300 whitespace-nowrap text-xs">{t.date}</td>
                        <td className="px-4 py-2.5 text-neutral-200 max-w-[220px]">
                          <div className="truncate" title={t.description}>{t.description}</div>
                          {t.merchant && t.merchant !== t.description && (
                            <div className="text-[10px] text-neutral-500 truncate">{t.merchant}</div>
                          )}
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono text-xs font-medium whitespace-nowrap ${
                          t.amount < 0 ? 'text-red-400' : 'text-green-400'
                        }`}>
                          {fmt(t.amount)}
                        </td>
                        <td className="px-4 py-2.5 text-neutral-400 text-xs">
                          {t.category ?? <span className="text-neutral-600 italic">—</span>}
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex flex-wrap gap-1">
                            {t.flags.map(f => <FlagBadge key={f} flag={f} />)}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between shrink-0">
              <button onClick={handleBack}
                className="text-sm text-neutral-400 hover:text-neutral-200 transition-colors">
                ← Modify criteria
              </button>
              <div className="flex gap-3">
                <button onClick={handleClose}
                  className="px-4 py-2 rounded-lg text-sm text-neutral-400 hover:text-neutral-200 hover:bg-slate-800 transition-colors">
                  Close
                </button>
                {result.total > 0 && (
                  <>
                    <button
                      onClick={handleExportCSV}
                      disabled={exporting}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-slate-700 hover:bg-slate-600 text-neutral-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                      {exporting
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Download className="w-4 h-4" />
                      }
                      Export CSV
                    </button>
                    <button
                      onClick={handleExportExcel}
                      disabled={exporting}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                      {exporting
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Download className="w-4 h-4" />
                      }
                      Export Excel
                    </button>
                  </>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
