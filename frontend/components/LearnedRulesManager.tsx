'use client'

import React, { useState, useEffect, useMemo } from 'react'
import {
  Sparkles, Trash2, Edit2, Power, PowerOff, RefreshCw, Info,
  TrendingUp, Loader2, AlertCircle, X, Check, ChevronDown, ChevronUp,
  Search, Crosshair, Store, ArrowRight, FileSearch, Tag
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'
import { useClient } from '@/lib/clientContext'
import { toast } from 'sonner'

/* ── Types ──────────────────────────────────────────────────────────── */
interface LearnedRule {
  id: number
  category: string
  pattern_type: string
  pattern_value: string
  confidence_score: number
  use_count: number
  enabled: boolean
  created_at: string
  last_used: string | null
}
interface LearnedRulesManagerProps { sessionId: string }

/* ── Pattern helpers ────────────────────────────────────────────────── */
const PATTERN_META: Record<string, { icon: React.ReactNode; label: string; verb: string }> = {
  exact:       { icon: <Crosshair className="w-3.5 h-3.5" />, label: 'Exact',       verb: 'is exactly' },
  merchant:    { icon: <Store className="w-3.5 h-3.5" />,     label: 'Merchant',     verb: 'merchant is' },
  starts_with: { icon: <ArrowRight className="w-3.5 h-3.5" />,label: 'Starts With',  verb: 'starts with' },
  contains:    { icon: <FileSearch className="w-3.5 h-3.5" />,label: 'Contains',     verb: 'contains' },
}
const pm = (type: string) => PATTERN_META[type] ?? { icon: null, label: type, verb: type }

/* ══════════════════════════════════════════════════════════════════════
   LEARNED RULES MANAGER
   ══════════════════════════════════════════════════════════════════════ */
export default function LearnedRulesManager({ sessionId }: LearnedRulesManagerProps) {
  const { currentClient } = useClient()
  const [rules, setRules] = useState<LearnedRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingRule, setEditingRule] = useState<number | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [showInfo, setShowInfo] = useState(false)
  const [applyingRules, setApplyingRules] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'

  useEffect(() => { fetchRules() }, [currentClient?.id])

  /* ── data ──────────────────────────────────────────────────────── */
  const fetchRules = async () => {
    try {
      setLoading(true); setError(null)
      const cpFirst = currentClient?.id ? `?client_id=${currentClient.id}` : ''
      const data = await apiFetch(`${API_BASE}/learned-rules${cpFirst}`)
      setRules(data.rules || [])
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load learned rules') }
    finally { setLoading(false) }
  }

  const updateRule = async (ruleId: number, updates: Partial<LearnedRule>) => {
    try {
      await apiFetch(`${API_BASE}/learned-rules/${ruleId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates)
      })
      await fetchRules(); setEditingRule(null)
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Failed to update rule') }
  }

  const deleteRule = async (ruleId: number) => {
    if (!confirm('Delete this learned pattern?')) return
    try { await apiFetch(`${API_BASE}/learned-rules/${ruleId}`, { method: 'DELETE' }); await fetchRules() }
    catch (err) { toast.error(err instanceof Error ? err.message : 'Failed to delete rule') }
  }

  const toggleEnabled = async (rule: LearnedRule) => { await updateRule(rule.id, { enabled: !rule.enabled }) }
  const startEdit = (rule: LearnedRule) => { setEditingRule(rule.id); setEditCategory(rule.category) }
  const saveEdit = async (ruleId: number) => { await updateRule(ruleId, { category: editCategory }) }

  const applyRules = async () => {
    if (!confirm('Apply all learned rules to ALL transactions for this client?')) return
    try {
      setApplyingRules(true)
      const sessionParam = sessionId ? `session_id=${sessionId}` : ''
      const clientParam = currentClient?.id ? `client_id=${currentClient.id}` : ''
      const params = [sessionParam, clientParam].filter(Boolean).join('&')
      const data = await apiFetch(`${API_BASE}/learned-rules/apply?${params}`, { method: 'POST' })
      toast.success(data.message); window.location.reload()
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Failed to apply rules') }
    finally { setApplyingRules(false) }
  }

  const deleteAllRules = async () => {
    if (!confirm(`Delete ALL ${rules.length} learned patterns${currentClient ? ` for ${currentClient.name}` : ''}? This cannot be undone.`)) return
    try {
      const cp = currentClient?.id ? `?client_id=${currentClient.id}` : ''
      await apiFetch(`${API_BASE}/learned-rules/all${cp}`, { method: 'DELETE' })
      toast.success('All learned rules deleted')
      await fetchRules()
    } catch (err) { toast.error(err instanceof Error ? err.message : 'Failed to delete rules') }
  }

  /* ── derived ───────────────────────────────────────────────────── */
  const totalUseCount = rules.reduce((sum, r) => sum + r.use_count, 0)
  const enabledCount = rules.filter(r => r.enabled).length
  const avgUseCount = rules.length > 0 ? (totalUseCount / rules.length).toFixed(1) : '0'

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return rules
    const q = searchTerm.toLowerCase()
    return rules.filter(r =>
      r.pattern_value.toLowerCase().includes(q) ||
      r.category.toLowerCase().includes(q) ||
      r.pattern_type.toLowerCase().includes(q)
    )
  }, [rules, searchTerm])

  /* ── loading / error ───────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
        <span className="ml-2 text-sm text-neutral-500">Loading learned patterns...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            <button onClick={fetchRules} className="mt-2 text-xs text-red-600 font-medium underline hover:text-red-800">Try again</button>
          </div>
        </div>
      </div>
    )
  }

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-5">

      {/* ── Stats Grid ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Patterns', value: rules.length, color: 'violet' },
          { label: 'Active',         value: enabledCount,  color: 'emerald' },
          { label: 'Total Uses',     value: totalUseCount, color: 'indigo' },
          { label: 'Avg Uses',       value: avgUseCount,   color: 'amber' },
        ].map(s => (
          <div key={s.label}
            className={`rounded-xl border bg-${s.color}-50 border-${s.color}-200 px-4 py-3`}>
            <p className={`text-[11px] uppercase tracking-wider font-semibold text-${s.color}-600`}>{s.label}</p>
            <p className={`text-2xl font-bold text-${s.color}-800 mt-0.5`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* ── Actions ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={applyRules} disabled={applyingRules || rules.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          {applyingRules ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {applyingRules ? 'Applying...' : 'Re-Apply All Rules'}
        </button>
        <button onClick={fetchRules}
          className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
        <button onClick={deleteAllRules} disabled={rules.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <Trash2 className="w-3.5 h-3.5" /> Delete All
        </button>
        <button onClick={() => setShowInfo(!showInfo)}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${showInfo ? 'bg-indigo-100 text-indigo-700' : 'text-neutral-500 hover:bg-neutral-100'}`}>
          <Info className="w-3.5 h-3.5" /> How it works
        </button>
      </div>

      {/* ── Info Panel ──────────────────────────────────────────── */}
      {showInfo && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 px-5 py-4">
          <h3 className="text-sm font-semibold text-indigo-900 mb-2">How Auto-Learning Works</h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-xs text-indigo-800">
            <li className="flex items-start gap-2"><span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" /> When you categorize, the system learns patterns</li>
            <li className="flex items-start gap-2"><span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" /> Future uploads are auto-categorized</li>
            <li className="flex items-start gap-2"><span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" /> You can edit or disable any learned pattern</li>
            <li className="flex items-start gap-2"><span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" /> Typically saves 70-90% categorization time</li>
          </ul>
        </div>
      )}

      {/* ── Search ──────────────────────────────────────────────── */}
      {rules.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text" placeholder="Search patterns, categories..."
            value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 bg-white pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-300"
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="w-4 h-4 text-neutral-400 hover:text-neutral-600" />
            </button>
          )}
        </div>
      )}

      {/* ── Empty State ─────────────────────────────────────────── */}
      {rules.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-neutral-200 bg-neutral-50 py-14">
          <Sparkles className="w-10 h-10 text-neutral-300 mb-3" />
          <p className="text-sm font-medium text-neutral-700">No Learned Patterns Yet</p>
          <p className="text-xs text-neutral-400 mt-1 max-w-sm text-center">
            Start categorizing transactions — the system will automatically learn and help categorize future uploads.
          </p>
          <div className="mt-4 flex items-center gap-1.5 text-xs text-neutral-400">
            <TrendingUp className="w-3.5 h-3.5" />
            Typically saves 70-90% categorization time from the second upload
          </div>
        </div>
      )}

      {/* ── Rules List ──────────────────────────────────────────── */}
      {filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map(rule => {
            const meta = pm(rule.pattern_type)
            return (
              <div key={rule.id}
                className={`rounded-xl border overflow-hidden transition-shadow ${
                  rule.enabled
                    ? 'border-neutral-200 bg-white shadow-sm hover:shadow-md'
                    : 'border-neutral-100 bg-neutral-50 opacity-60'
                }`}>
                <div className="px-5 py-4">
                  <div className="flex items-start justify-between gap-4">
                    {/* left: description */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-neutral-700 leading-relaxed">
                        If transaction {meta.verb}{' '}
                        <code className="rounded bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 text-[11px] font-mono text-neutral-800">{rule.pattern_value}</code>
                        {' '}then categorize as{' '}
                        <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 text-violet-700 border border-violet-200 px-2 py-0.5 text-[11px] font-semibold">
                          <Tag className="w-3 h-3" /> {rule.category}
                        </span>
                      </p>

                      {/* meta row */}
                      <div className="flex items-center gap-3 mt-2 flex-wrap">
                        <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 text-neutral-600 px-2 py-0.5 text-[10px] font-medium">
                          {meta.icon} {meta.label}
                        </span>
                        <span className="flex items-center gap-1 text-[11px] text-neutral-500">
                          <TrendingUp className="w-3 h-3" /> Used {rule.use_count}×
                        </span>
                        {rule.last_used && (
                          <span className="text-[11px] text-neutral-400">
                            Last: {new Date(rule.last_used).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      {/* inline edit */}
                      {editingRule === rule.id && (
                        <div className="flex items-center gap-2 mt-3">
                          <span className="text-xs text-neutral-500">New category:</span>
                          <input type="text" value={editCategory} onChange={e => setEditCategory(e.target.value)} autoFocus
                            className="rounded-lg border border-neutral-200 px-3 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-violet-200" />
                          <button onClick={() => saveEdit(rule.id)}
                            className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700">
                            <Check className="w-3 h-3" /> Save
                          </button>
                          <button onClick={() => setEditingRule(null)}
                            className="rounded-lg border border-neutral-200 px-2.5 py-1 text-xs text-neutral-600 hover:bg-neutral-50">
                            Cancel
                          </button>
                        </div>
                      )}
                    </div>

                    {/* right: action buttons */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button onClick={() => toggleEnabled(rule)}
                        className={`rounded-lg p-1.5 transition-colors ${rule.enabled ? 'text-emerald-600 hover:bg-emerald-50' : 'text-neutral-400 hover:bg-neutral-100'}`}
                        title={rule.enabled ? 'Disable' : 'Enable'}>
                        {rule.enabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                      </button>
                      <button onClick={() => startEdit(rule)}
                        className="rounded-lg p-1.5 text-indigo-600 hover:bg-indigo-50 transition-colors" title="Edit category">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => deleteRule(rule.id)}
                        className="rounded-lg p-1.5 text-red-500 hover:bg-red-50 transition-colors" title="Delete">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── No search results ───────────────────────────────────── */}
      {rules.length > 0 && filtered.length === 0 && (
        <div className="text-center py-10 text-sm text-neutral-400">
          No patterns match &quot;{searchTerm}&quot;
        </div>
      )}
    </div>
  )
}
