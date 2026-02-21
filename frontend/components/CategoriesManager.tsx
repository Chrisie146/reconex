"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import { useClient } from '@/lib/clientContext'
import {
  Search, Plus, Trash2, Tag, X, Check, Pencil,
  ToggleLeft, ToggleRight, Calculator, Loader2,
  AlertCircle, CheckCircle2, ShieldCheck, Palette, Info
} from 'lucide-react'

/* ── Category colour tokens (shared) ────────────────────────────────── */
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  'Income':          { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200',  dot: 'bg-emerald-500' },
  'Salary':          { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200',  dot: 'bg-emerald-500' },
  'Transfer':        { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',     dot: 'bg-blue-500' },
  'Transfers':       { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',     dot: 'bg-blue-500' },
  'Bank Charges':    { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',    dot: 'bg-amber-500' },
  'Bank Fees':       { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',    dot: 'bg-amber-500' },
  'Insurance':       { bg: 'bg-violet-50',   text: 'text-violet-700',   border: 'border-violet-200',   dot: 'bg-violet-500' },
  'Groceries':       { bg: 'bg-lime-50',     text: 'text-lime-700',     border: 'border-lime-200',     dot: 'bg-lime-500' },
  'Fuel':            { bg: 'bg-orange-50',   text: 'text-orange-700',   border: 'border-orange-200',   dot: 'bg-orange-500' },
  'Utilities':       { bg: 'bg-cyan-50',     text: 'text-cyan-700',     border: 'border-cyan-200',     dot: 'bg-cyan-500' },
  'Entertainment':   { bg: 'bg-pink-50',     text: 'text-pink-700',     border: 'border-pink-200',     dot: 'bg-pink-500' },
  'Medical':         { bg: 'bg-red-50',      text: 'text-red-700',      border: 'border-red-200',      dot: 'bg-red-500' },
  'Rent':            { bg: 'bg-indigo-50',   text: 'text-indigo-700',   border: 'border-indigo-200',   dot: 'bg-indigo-500' },
  'Subscriptions':   { bg: 'bg-fuchsia-50',  text: 'text-fuchsia-700',  border: 'border-fuchsia-200',  dot: 'bg-fuchsia-500' },
  'Loan':            { bg: 'bg-rose-50',     text: 'text-rose-700',     border: 'border-rose-200',     dot: 'bg-rose-500' },
  'Loan Repayment':  { bg: 'bg-rose-50',     text: 'text-rose-700',     border: 'border-rose-200',     dot: 'bg-rose-500' },
}
const DEFAULT_STYLE = { bg: 'bg-neutral-50', text: 'text-neutral-700', border: 'border-neutral-200', dot: 'bg-neutral-400' }
function getCatStyle(name: string) {
  return CATEGORY_COLORS[name] ??
    Object.entries(CATEGORY_COLORS).find(([k]) => k.toLowerCase() === name.toLowerCase())?.[1] ??
    DEFAULT_STYLE
}

/* ── Types ──────────────────────────────────────────────────────────── */
interface CategoriesManagerProps { sessionId: string }
interface Category {
  name: string
  is_built_in: boolean
  vat_applicable: boolean
  vat_rate: number
}

/* ══════════════════════════════════════════════════════════════════════
   CATEGORIES MANAGER
   ══════════════════════════════════════════════════════════════════════ */
export default function CategoriesManager({ sessionId }: CategoriesManagerProps) {
  const { currentClient } = useClient()
  const [categories, setCategories] = useState<Category[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryVAT, setNewCategoryVAT] = useState(true)
  const [newCategoryRate, setNewCategoryRate] = useState(15.0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [vatEnabled, setVatEnabled] = useState(false)
  const [editingRate, setEditingRate] = useState<string | null>(null)
  const [tempRate, setTempRate] = useState<number>(0)
  const [showAddForm, setShowAddForm] = useState(false)

  /* ── derived ───────────────────────────────────────────────────── */
  const filteredCategories = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    const list = q ? categories.filter(c => c.name.toLowerCase().includes(q)) : categories
    return [...list].sort((a, b) => {
      if (a.is_built_in && !b.is_built_in) return -1
      if (!a.is_built_in && b.is_built_in) return 1
      return a.name.localeCompare(b.name)
    })
  }, [categories, searchQuery])

  const builtInCount = categories.filter(c => c.is_built_in).length
  const customCount = categories.length - builtInCount

  /* ── data loading ──────────────────────────────────────────────── */
  useEffect(() => { loadCategories(); loadVATConfig() }, [sessionId, currentClient?.id])

  const loadCategories = async () => {
    const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
    try {
      const data = await apiFetch(`/categories/with-vat?session_id=${sessionId}${cp}`)
      setCategories(data.categories || [])
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load categories') }
  }
  const loadVATConfig = async () => {
    try { const d = await apiFetch(`/vat/config?session_id=${sessionId}`); setVatEnabled(d.vat_enabled || false) }
    catch { /* ignore */ }
  }

  /* ── actions ───────────────────────────────────────────────────── */
  const flash = (msg: string, type: 'success' | 'error') => {
    if (type === 'success') { setSuccess(msg); setTimeout(() => setSuccess(null), 3500) }
    else { setError(msg); setTimeout(() => setError(null), 5000) }
  }

  const handleToggleVAT = async () => {
    setLoading(true); setError(null)
    try {
      const data = await apiFetch(`/vat/config?session_id=${sessionId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vat_enabled: !vatEnabled, default_vat_rate: 15.0 })
      })
      setVatEnabled(!vatEnabled)
      flash(data.message, 'success')
      await loadCategories()
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to toggle VAT', 'error') }
    finally { setLoading(false) }
  }

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault(); setError(null); setSuccess(null)
    if (!newCategoryName.trim()) { flash('Enter a category name', 'error'); return }
    setLoading(true)
    try {
      const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
      await apiFetch(`/categories?session_id=${sessionId}${cp}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_name: newCategoryName })
      })
      try {
        const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
        await apiFetch(`/categories/${encodeURIComponent(newCategoryName)}/vat?session_id=${sessionId}${cp}`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vat_applicable: newCategoryVAT, vat_rate: newCategoryRate })
        })
      } catch { /* ok */ }
      await loadCategories()
      setNewCategoryName(''); setNewCategoryVAT(false); setNewCategoryRate(15.0); setShowAddForm(false)
      flash('Category created', 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to create category', 'error') }
    finally { setLoading(false) }
  }

  const handleUpdateCategoryVAT = async (name: string, vatApplicable: boolean, vatRate: number) => {
    setLoading(true); setError(null)
    try {
      const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
      await apiFetch(`/categories/${encodeURIComponent(name)}/vat?session_id=${sessionId}${cp}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vat_applicable: vatApplicable, vat_rate: vatRate })
      })
      if (vatEnabled) {
        await apiFetch(`/vat/recalculate?session_id=${sessionId}`, { method: 'POST' })
      }
      await loadCategories(); setEditingRate(null)
      flash(`VAT updated for ${name}`, 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to update VAT', 'error') }
    finally { setLoading(false) }
  }

  const handleManualRecalculate = async () => {
    if (!vatEnabled) { flash('Enable VAT first', 'error'); return }
    setLoading(true); setError(null)
    try {
      const data = await apiFetch(`/vat/recalculate?session_id=${sessionId}`, { method: 'POST' })
      flash(`VAT recalculated — ${data.stats?.total_recalculated || 0} transactions updated`, 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Recalculation failed', 'error') }
    finally { setLoading(false) }
  }

  const handleDeleteCategory = async (name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return
    setLoading(true)
    try {
      const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
      const sp = sessionId ? `session_id=${sessionId}` : ''
      await apiFetch(`/categories/${encodeURIComponent(name)}?${sp}${cp}`, { method: 'DELETE' })
      await loadCategories()
      flash(`"${name}" deleted`, 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to delete', 'error') }
    finally { setLoading(false) }
  }

  const handleDeleteAllCustom = async () => {
    if (!confirm(`Delete ALL ${customCount} custom categories${currentClient ? ` for ${currentClient.name}` : ''}? This cannot be undone.`)) return
    setLoading(true)
    try {
      const cp = currentClient?.id ? `?client_id=${currentClient.id}` : ''
      await apiFetch(`/categories/all/custom${cp}`, { method: 'DELETE' })
      await loadCategories()
      flash('All custom categories deleted', 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to delete categories', 'error') }
    finally { setLoading(false) }
  }

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-5">

      {/* ── VAT toggle card ─────────────────────────────────────── */}
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <Calculator className="w-5 h-5 text-indigo-500" />
            <div>
              <p className="text-sm font-semibold text-neutral-800">VAT Calculation</p>
              <p className="text-xs text-neutral-500">South African 15% standard rate</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleVAT} disabled={loading}
              className="relative flex items-center gap-2 group disabled:opacity-50"
            >
              {vatEnabled
                ? <ToggleRight className="w-9 h-9 text-emerald-500 group-hover:text-emerald-600 transition-colors" />
                : <ToggleLeft className="w-9 h-9 text-neutral-300 group-hover:text-neutral-400 transition-colors" />
              }
              <span className={`text-xs font-semibold ${vatEnabled ? 'text-emerald-600' : 'text-neutral-400'}`}>
                {vatEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </button>
            {vatEnabled && (
              <button
                onClick={handleManualRecalculate} disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Calculator className="w-3.5 h-3.5" />}
                Recalculate
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Toasts ──────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm">
          <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
          <span className="flex-1 text-red-700">{error}</span>
          <button onClick={() => setError(null)}><X className="w-4 h-4 text-red-400 hover:text-red-600" /></button>
        </div>
      )}
      {success && (
        <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
          <span className="flex-1 text-emerald-700">{success}</span>
          <button onClick={() => setSuccess(null)}><X className="w-4 h-4 text-emerald-400 hover:text-emerald-600" /></button>
        </div>
      )}

      {/* ── Toolbar row ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search categories..."
            className="w-full rounded-lg border border-neutral-200 bg-white pl-9 pr-3 py-2 text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="w-3.5 h-3.5 text-neutral-400 hover:text-neutral-600" />
            </button>
          )}
        </div>

        {/* counts */}
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 font-semibold">{builtInCount} built-in</span>
          <span className="rounded-full bg-violet-100 text-violet-700 px-2 py-0.5 font-semibold">{customCount} custom</span>
          {searchQuery && <span className="text-neutral-400">{filteredCategories.length} match</span>}
        </div>

        {/* add + delete all buttons */}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleDeleteAllCustom} disabled={loading || customCount === 0}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete All Custom
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Add Category
          </button>
        </div>
      </div>

      {/* ── Add category form (expandable) ──────────────────────── */}
      {showAddForm && (
        <form onSubmit={handleAddCategory} className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-neutral-800 flex items-center gap-2">
            <Plus className="w-4 h-4 text-indigo-500" /> New Category
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-neutral-600 mb-1">Name</label>
              <input
                type="text" value={newCategoryName} onChange={e => setNewCategoryName(e.target.value)}
                placeholder="e.g. Pet Care, Subscriptions"
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">VAT Rate (%)</label>
              <input
                type="number" value={newCategoryRate} onChange={e => setNewCategoryRate(parseFloat(e.target.value))}
                min="0" max="100" step="0.1"
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300"
                disabled={loading || !newCategoryVAT}
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-xs font-medium text-neutral-600 cursor-pointer">
                <input type="checkbox" checked={newCategoryVAT} onChange={e => setNewCategoryVAT(e.target.checked)}
                  className="w-4 h-4 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-300" />
                VAT applicable
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={loading || !newCategoryName.trim()}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors">
                  {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Create
                </button>
                <button type="button" onClick={() => setShowAddForm(false)}
                  className="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </form>
      )}

      {/* ── Categories table ────────────────────────────────────── */}
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-100 bg-neutral-50/80">
                <th className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Category</th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Type</th>
                <th className="px-5 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-neutral-500">VAT</th>
                <th className="px-5 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Rate</th>
                <th className="px-5 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filteredCategories.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-sm text-neutral-400">
                    {searchQuery ? 'No categories match your search' : 'No categories found'}
                  </td>
                </tr>
              ) : (
                filteredCategories.map((cat, i) => {
                  const cs = getCatStyle(cat.name)
                  return (
                    <tr key={cat.name}
                      className={`group transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-neutral-50/40'} hover:bg-neutral-50`}>
                      {/* name */}
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className={`w-2 h-2 rounded-full ${cs.dot} shrink-0`} />
                          <span className="text-sm font-medium text-neutral-800">{cat.name}</span>
                        </div>
                      </td>
                      {/* type */}
                      <td className="px-5 py-3">
                        {cat.is_built_in ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-0.5 text-[11px] font-semibold">
                            <ShieldCheck className="w-3 h-3" /> Built-in
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 text-violet-700 border border-violet-200 px-2.5 py-0.5 text-[11px] font-semibold">
                            <Palette className="w-3 h-3" /> Custom
                          </span>
                        )}
                      </td>
                      {/* vat checkbox */}
                      <td className="px-5 py-3 text-center">
                        <input type="checkbox" checked={cat.vat_applicable}
                          onChange={e => handleUpdateCategoryVAT(cat.name, e.target.checked, cat.vat_rate)}
                          disabled={loading}
                          className="w-4 h-4 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-300 cursor-pointer disabled:opacity-50" />
                      </td>
                      {/* vat rate */}
                      <td className="px-5 py-3 text-center">
                        {cat.vat_applicable ? (
                          editingRate === cat.name ? (
                            <div className="flex items-center justify-center gap-1.5">
                              <input type="number" value={tempRate} onChange={e => setTempRate(parseFloat(e.target.value))}
                                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleUpdateCategoryVAT(cat.name, cat.vat_applicable, tempRate); }; if (e.key === 'Escape') setEditingRate(null) }}
                                min="0" max="100" step="0.1" autoFocus
                                className="w-16 rounded border border-indigo-300 px-2 py-1 text-xs text-center focus:outline-none focus:ring-2 focus:ring-indigo-200" />
                              <button onClick={() => { handleUpdateCategoryVAT(cat.name, cat.vat_applicable, tempRate) }}
                                className="p-0.5 text-emerald-600 hover:text-emerald-700"><Check className="w-3.5 h-3.5" /></button>
                              <button onClick={() => setEditingRate(null)}
                                className="p-0.5 text-neutral-400 hover:text-neutral-600"><X className="w-3.5 h-3.5" /></button>
                            </div>
                          ) : (
                            <button onClick={() => { setEditingRate(cat.name); setTempRate(cat.vat_rate) }} disabled={loading}
                              className="text-xs font-medium text-neutral-700 hover:text-indigo-600 underline decoration-dotted underline-offset-2 transition-colors">
                              {cat.vat_rate}%
                            </button>
                          )
                        ) : (
                          <span className="text-xs text-neutral-300">—</span>
                        )}
                      </td>
                      {/* actions */}
                      <td className="px-5 py-3 text-center">
                        {cat.is_built_in ? (
                          <span className="text-[11px] text-neutral-400">Protected</span>
                        ) : (
                          <button onClick={() => handleDeleteCategory(cat.name)} disabled={loading}
                            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50">
                            <Trash2 className="w-3.5 h-3.5" /> Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Info cards ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-semibold text-blue-800 mb-0.5">Built-in Categories</p>
            <p className="text-xs text-blue-700 leading-relaxed">Default VAT settings based on SA tax regulations. You can modify VAT but cannot delete them.</p>
          </div>
        </div>
        <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <Info className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-semibold text-emerald-800 mb-0.5">Multilingual Support</p>
            <p className="text-xs text-emerald-700 leading-relaxed">Categories support English and Afrikaans keywords for accurate matching across languages.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
