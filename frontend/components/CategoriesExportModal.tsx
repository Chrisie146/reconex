'use client'

import { useEffect, useState } from 'react'
import { X, FileSpreadsheet, AlertCircle, Calendar, Loader2, FolderOpen, BarChart3, CheckSquare, Square } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CategoriesExportModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
  clientId?: number | null
}
interface Category { name: string; transaction_count: number }

export default function CategoriesExportModal({ isOpen, onClose, sessionId, clientId }: CategoriesExportModalProps) {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [useFullPeriod, setUseFullPeriod] = useState(true)
  const [includeVAT, setIncludeVAT] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)

  const [sessionDateFrom, setSessionDateFrom] = useState<string | null>(null)
  const [sessionDateTo, setSessionDateTo] = useState<string | null>(null)

  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [loadingCategories, setLoadingCategories] = useState(false)

  /* ── fetch data ────────────────────────────────────────────────── */
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

    ;(async () => {
      setLoadingCategories(true)
      try {
        const catParams: any = clientId ? { client_id: clientId } : { session_id: sessionId }
        const res = await axios.get(`${API_BASE_URL}/categories`, { params: catParams })
        const cats: Category[] = Array.isArray(res.data?.categories) ? res.data.categories : []
        setCategories(cats); setSelectedCategories(cats.map(c => c.name))
      } catch { setCategories([]); setSelectedCategories([]) }
      finally { setLoadingCategories(false) }
    })()
  }, [isOpen, sessionId, clientId])

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

  /* ── helpers ───────────────────────────────────────────────────── */
  const handleCategoryToggle = (name: string) =>
    setSelectedCategories(prev => prev.includes(name) ? prev.filter(c => c !== name) : [...prev, name])
  const handleSelectAll = () => setSelectedCategories(categories.map(c => c.name))
  const handleDeselectAll = () => setSelectedCategories([])

  /* ── export ────────────────────────────────────────────────────── */
  const handleExport = async () => {
    if (!sessionId && !clientId) return
    if (selectedCategories.length === 0) { setError('Select at least one category.'); return }
    setExporting(true); setError(null)
    try {
      const params: any = clientId
        ? { client_id: clientId, include_vat: includeVAT }
        : { session_id: sessionId, include_vat: includeVAT }
      if (!useFullPeriod && dateFrom && dateTo) { params.date_from = dateFrom; params.date_to = dateTo }
      if (Array.isArray(categories) && selectedCategories.length < categories.length) {
        params.categories = selectedCategories.join(',')
      }
      const res = await axios.get(`${API_BASE_URL}/export/categories`, { params, responseType: 'blob' })
      const range = dateFrom && dateTo ? `${dateFrom}_to_${dateTo}` : (sessionId?.substring(0, 8) || 'export')
      const fn = `categories${includeVAT ? '_with_vat' : ''}_${range}.xlsx`
      const url = window.URL.createObjectURL(res.data)
      const a = document.createElement('a'); a.href = url; a.download = fn
      document.body.appendChild(a); a.click(); document.body.removeChild(a); window.URL.revokeObjectURL(url)
      onClose()
    } catch (err: any) { setError(err.response?.data?.detail || 'Export failed. Please try again.') }
    finally { setExporting(false) }
  }

  if (!isOpen) return null

  const allSelected = categories.length > 0 && selectedCategories.length === categories.length

  /* ── render ────────────────────────────────────────────────────── */
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl ring-1 ring-neutral-200 max-h-[90vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>

        {/* ── Header ───────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-100">
              <FileSpreadsheet className="w-4 h-4 text-indigo-600" />
            </div>
            <h2 className="text-base font-bold text-neutral-900">Export Categories</h2>
            {includeVAT && (
              <span className="rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">VAT</span>
            )}
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Body (scrollable) ────────────────────────────────── */}
        <div className="px-6 py-5 space-y-6 overflow-y-auto flex-1">

          {/* Date Range */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Date Range</h3>
            </div>
            <label className="flex items-center gap-2.5 cursor-pointer mb-3">
              <input type="checkbox" checked={useFullPeriod} onChange={e => setUseFullPeriod(e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-300" />
              <span className="text-sm text-neutral-700">Use full statement period</span>
            </label>
            {!useFullPeriod && (
              <div className="grid grid-cols-2 gap-3 ml-6">
                {[{ label: 'From', val: dateFrom, set: setDateFrom }, { label: 'To', val: dateTo, set: setDateTo }].map(f => (
                  <div key={f.label}>
                    <label className="block text-[11px] font-semibold text-neutral-500 mb-1">{f.label}</label>
                    <input type="date" value={f.val} onChange={e => f.set(e.target.value)}
                      className="w-full rounded-lg border border-neutral-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300" />
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

          {/* Category Selection */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-neutral-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Categories</h3>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={handleSelectAll} className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800">All</button>
                <span className="text-neutral-300">|</span>
                <button onClick={handleDeselectAll} className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800">None</button>
              </div>
            </div>

            {loadingCategories ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
              </div>
            ) : !Array.isArray(categories) || categories.length === 0 ? (
              <div className="py-6 rounded-xl border border-dashed border-neutral-200 text-center text-sm text-neutral-400">
                No categories found
              </div>
            ) : (
              <div className="rounded-xl border border-neutral-200 overflow-hidden max-h-44 overflow-y-auto divide-y divide-neutral-100">
                {categories.map(cat => {
                  const checked = selectedCategories.includes(cat.name)
                  return (
                    <label key={cat.name}
                      className={`flex items-center gap-3 px-3.5 py-2.5 cursor-pointer transition-colors ${checked ? 'bg-indigo-50/40' : 'hover:bg-neutral-50'}`}>
                      <input type="checkbox" checked={checked} onChange={() => handleCategoryToggle(cat.name)}
                        className="w-4 h-4 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-300" />
                      <span className="text-sm text-neutral-700 flex-1 truncate">{cat.name}</span>
                      <span className="text-[11px] text-neutral-400 tabular-nums">{cat.transaction_count}</span>
                    </label>
                  )
                })}
              </div>
            )}
            <p className="mt-2 text-[11px] text-neutral-400">
              {selectedCategories.length} of {Array.isArray(categories) ? categories.length : 0} selected
            </p>
          </div>

          {/* VAT Toggle */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-4 h-4 text-neutral-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Display Options</h3>
            </div>
            <label className={`flex items-start gap-3 cursor-pointer rounded-xl border-2 px-4 py-3 transition-colors ${
              includeVAT ? 'border-emerald-400 bg-emerald-50/50' : 'border-neutral-100 hover:border-neutral-200 hover:bg-neutral-50'
            }`}>
              <input type="checkbox" checked={includeVAT} onChange={e => setIncludeVAT(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-neutral-300 text-emerald-600 focus:ring-emerald-300" />
              <div>
                <p className="text-sm font-semibold text-neutral-800">
                  Include VAT columns
                  {includeVAT && <span className="ml-1.5 text-emerald-600 text-[11px]">Enabled</span>}
                </p>
                <p className="text-[11px] text-neutral-500 mt-0.5">Adds VAT Amount, Incl VAT, and Excl VAT columns</p>
              </div>
            </label>
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
        <div className="flex justify-end gap-2.5 px-6 py-4 border-t border-neutral-100 bg-neutral-50/50 shrink-0">
          <button onClick={onClose} disabled={exporting}
            className="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-40">
            Cancel
          </button>
          <button onClick={handleExport} disabled={exporting || !dateFrom || !dateTo || selectedCategories.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
            {exporting
              ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Exporting...</>
              : <><FileSpreadsheet className="w-3.5 h-3.5" /> Export Report</>}
          </button>
        </div>
      </div>
    </div>
  )
}
