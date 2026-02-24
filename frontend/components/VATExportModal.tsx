'use client'

import { useEffect, useState } from 'react'
import { X, FileSpreadsheet, AlertCircle, Calendar, Loader2, BarChart3, ArrowDownUp, ArrowDown, ArrowUp } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface VATExportModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
  clientId?: number | null
}

const EXPORT_TYPES = [
  { value: 'both'        as const, icon: <ArrowDownUp className="w-4 h-4" />, label: 'Both Input & Output', desc: 'Full report with Net VAT calculation' },
  { value: 'input_only'  as const, icon: <ArrowDown className="w-4 h-4" />,   label: 'VAT Input Only',      desc: 'Expenses and claimable VAT' },
  { value: 'output_only' as const, icon: <ArrowUp className="w-4 h-4" />,     label: 'VAT Output Only',     desc: 'Sales/Income and payable VAT' },
] as const

export default function VATExportModal({ isOpen, onClose, sessionId, clientId }: VATExportModalProps) {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [useFullPeriod, setUseFullPeriod] = useState(true)
  const [exportType, setExportType] = useState<'both' | 'input_only' | 'output_only'>('both')
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)

  const [sessionDateFrom, setSessionDateFrom] = useState<string | null>(null)
  const [sessionDateTo, setSessionDateTo] = useState<string | null>(null)

  /* ── fetch session dates ───────────────────────────────────────── */
  useEffect(() => {
    if (!isOpen || !sessionId) return
    ;(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/sessions`)
        const cur = (res.data.sessions || []).find((s: any) => s.session_id === sessionId)
        if (cur) {
          setSessionDateFrom(cur.date_from); setSessionDateTo(cur.date_to)
          setDateFrom(cur.date_from || ''); setDateTo(cur.date_to || '')
        }
      } catch { /* ignore */ }
    })()
  }, [isOpen, sessionId])

  useEffect(() => {
    if (useFullPeriod && sessionDateFrom && sessionDateTo) {
      setDateFrom(sessionDateFrom); setDateTo(sessionDateTo); setWarning(null)
    }
  }, [useFullPeriod, sessionDateFrom, sessionDateTo])

  useEffect(() => {
    if (!dateFrom || !dateTo || !sessionDateFrom || !sessionDateTo) { setWarning(null); return }
    const [f, t, sf, st] = [new Date(dateFrom), new Date(dateTo), new Date(sessionDateFrom), new Date(sessionDateTo)]
    if (f < sf || t > st) {
      setWarning(`Range extends beyond statement dates. Export will cover ${f < sf ? sessionDateFrom : dateFrom} to ${t > st ? sessionDateTo : dateTo}.`)
    } else setWarning(null)
  }, [dateFrom, dateTo, sessionDateFrom, sessionDateTo])

  /* ── export ────────────────────────────────────────────────────── */
  const handleExport = async () => {
    if (!sessionId && !clientId) return
    setExporting(true); setError(null)
    try {
      const params: any = clientId
        ? { client_id: clientId, format: 'excel', export_type: exportType }
        : { session_id: sessionId, format: 'excel', export_type: exportType }
      if (!useFullPeriod && dateFrom && dateTo) { params.date_from = dateFrom; params.date_to = dateTo }
      const res = await axios.get(`${API_BASE_URL}/vat/export`, { params, responseType: 'blob' })
      const range = dateFrom && dateTo ? `${dateFrom}_to_${dateTo}` : (sessionId?.substring(0, 8) || 'export')
      const fn = `vat_${exportType === 'both' ? 'report' : exportType}_${range}.xlsx`
      const url = window.URL.createObjectURL(res.data)
      const a = document.createElement('a'); a.href = url; a.download = fn
      document.body.appendChild(a); a.click(); document.body.removeChild(a); window.URL.revokeObjectURL(url)
      onClose()
    } catch (err: any) { setError(err.response?.data?.detail || 'Export failed. Please try again.') }
    finally { setExporting(false) }
  }

  if (!isOpen) return null

  /* ── render ────────────────────────────────────────────────────── */
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl ring-1 ring-neutral-200 overflow-hidden" onClick={e => e.stopPropagation()}>

        {/* ── Header ───────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100">
              <FileSpreadsheet className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-base font-bold text-neutral-900">Export VAT Report</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Body ─────────────────────────────────────────────── */}
        <div className="px-6 py-5 space-y-6">

          {/* Date Range */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Date Range</h3>
            </div>

            <label className="flex items-center gap-2.5 cursor-pointer mb-3">
              <input type="checkbox" checked={useFullPeriod} onChange={e => setUseFullPeriod(e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-300" />
              <span className="text-sm text-neutral-700">Use full statement period</span>
            </label>

            {!useFullPeriod && (
              <div className="grid grid-cols-2 gap-3 ml-6">
                {[{ label: 'From', val: dateFrom, set: setDateFrom }, { label: 'To', val: dateTo, set: setDateTo }].map(f => (
                  <div key={f.label}>
                    <label className="block text-[11px] font-semibold text-neutral-500 mb-1">{f.label}</label>
                    <input type="date" value={f.val} onChange={e => f.set(e.target.value)}
                      className="w-full rounded-lg border border-neutral-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300" />
                  </div>
                ))}
              </div>
            )}

            {warning && (
              <div className="mt-3 flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                <AlertCircle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                <p className="text-[11px] text-amber-700">{warning}</p>
              </div>
            )}
          </div>

          {/* Export Type */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Export Type</h3>
            </div>
            <div className="space-y-2">
              {EXPORT_TYPES.map(t => (
                <label key={t.value}
                  className={`flex items-start gap-3 cursor-pointer rounded-xl border-2 px-4 py-3 transition-colors ${
                    exportType === t.value
                      ? 'border-blue-500 bg-blue-50/60'
                      : 'border-neutral-100 hover:border-neutral-200 hover:bg-neutral-50'
                  }`}>
                  <input type="radio" name="exportType" value={t.value} checked={exportType === t.value}
                    onChange={() => setExportType(t.value)}
                    className="mt-0.5 w-4 h-4 border-neutral-300 text-blue-600 focus:ring-blue-300" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className={exportType === t.value ? 'text-blue-600' : 'text-neutral-400'}>{t.icon}</span>
                      <span className="text-sm font-semibold text-neutral-800">{t.label}</span>
                    </div>
                    <p className="text-[11px] text-neutral-500 mt-0.5">{t.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
              <p className="text-xs text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* ── Footer ───────────────────────────────────────────── */}
        <div className="flex justify-end gap-2.5 px-6 py-4 border-t border-neutral-100 bg-neutral-50/50">
          <button onClick={onClose} disabled={exporting}
            className="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-40">
            Cancel
          </button>
          <button onClick={handleExport} disabled={exporting || !dateFrom || !dateTo}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
            {exporting
              ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Exporting...</>
              : <><FileSpreadsheet className="w-3.5 h-3.5" /> Export Report</>}
          </button>
        </div>
      </div>
    </div>
  )
}
