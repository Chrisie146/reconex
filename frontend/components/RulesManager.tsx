"use client"

import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import { useClient } from '@/lib/clientContext'
import AccountSelector from './AccountSelector'
import { useAccounts } from '@/lib/hooks/useAccounts'
import {
  Plus, Trash2, Zap, Eye, EyeOff, ChevronDown, ChevronRight, X,
  Check, Loader2, AlertCircle, CheckCircle2, Settings2, Tag,
  ToggleLeft, ToggleRight, Hash, Layers
} from 'lucide-react'

/* ── Types ──────────────────────────────────────────────────────────── */
interface RulesManagerProps { sessionId: string }
interface Rule {
  rule_id: string
  name: string
  category: string | null
  account_id?: number | null
  keywords: string[]
  priority: number
  auto_apply: boolean
  enabled: boolean
  match_compound_words: boolean
}
interface RulePreview {
  matched: Array<{ id: number; date: string; description: string; amount: number; keyword_matched: string }>
  count: number
  percentage: number
  rule_name: string
  category: string | null
  account_id?: number | null
}

/* ══════════════════════════════════════════════════════════════════════
   RULES MANAGER
   ══════════════════════════════════════════════════════════════════════ */
export default function RulesManager({ sessionId }: RulesManagerProps) {
  const { currentClient } = useClient()
  const { accounts } = useAccounts(currentClient?.id ?? null, { postable: true })
  const [rules, setRules] = useState<Rule[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // form
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '', category: '', account_id: null as number | null, keywords: '', priority: 10, auto_apply: true, match_compound_words: false
  })

  // preview
  const [previewingRuleId, setPreviewingRuleId] = useState<string | null>(null)
  const [preview, setPreview] = useState<RulePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [applyingBulk, setApplyingBulk] = useState(false)

  useEffect(() => { loadRulesAndCategories() }, [sessionId, currentClient?.id])

  /* ── data ──────────────────────────────────────────────────────── */
  const loadRulesAndCategories = async () => {
    setLoading(true)
    try {
      const cp = currentClient?.id ? `&client_id=${currentClient.id}` : ''
      const [rulesData, categoriesData] = await Promise.all([
        apiFetch(`/session-rules?session_id=${sessionId}`),
        apiFetch(`/categories?session_id=${sessionId}${cp}`)
      ])
      setRules(rulesData.rules || [])
      const categoryNames = (categoriesData.categories || []).map((cat: any) =>
        typeof cat === 'string' ? cat : cat.name
      )
      setCategories(categoryNames)
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to load data', 'error') }
    finally { setLoading(false) }
  }

  /* ── helpers ───────────────────────────────────────────────────── */
  const flash = (msg: string, type: 'success' | 'error') => {
    if (type === 'success') { setSuccess(msg); setTimeout(() => setSuccess(null), 3500) }
    else { setError(msg); setTimeout(() => setError(null), 5000) }
  }

  /* ── actions ───────────────────────────────────────────────────── */
  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault(); setError(null); setSuccess(null)
    if (!formData.name.trim() || !formData.keywords.trim() || (!formData.category && !formData.account_id)) { flash('Fill in all required fields', 'error'); return }
    if (formData.category && !categories.includes(formData.category)) { flash(`Category "${formData.category}" doesn't exist in this client.`, 'error'); return }
    const keywords = formData.keywords.split('\n').map(k => k.trim()).filter(k => k)
    if (keywords.length === 0) { flash('Enter at least one keyword', 'error'); return }
    setLoading(true)
    try {
      const data = await apiFetch(`/session-rules?session_id=${sessionId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formData.name, category: formData.category || null, account_id: formData.account_id, keywords, priority: formData.priority, auto_apply: formData.auto_apply, match_compound_words: formData.match_compound_words })
      })
      setRules(data.rules || []); setFormData({ name: '', category: '', account_id: null, keywords: '', priority: 10, auto_apply: true, match_compound_words: false }); setShowCreateForm(false)
      flash('Rule created', 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to create rule', 'error') }
    finally { setLoading(false) }
  }

  const handlePreviewRule = async (ruleId: string) => {
    setPreviewLoading(true)
    try {
      const data = await apiFetch(`/session-rules/${ruleId}/preview?session_id=${sessionId}`, { method: 'POST' })
      setPreview(data)
    } catch (err) { flash(err instanceof Error ? err.message : 'Preview failed', 'error') }
    finally { setPreviewLoading(false) }
  }

  const handleBulkApply = async () => {
    if (!confirm('Apply all enabled rules to transactions?')) return
    setApplyingBulk(true)
    try {
      const data = await apiFetch(`/session-rules/apply-bulk?session_id=${sessionId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_apply_only: false })
      })
      flash(`${data.updated_count} transaction(s) categorized using ${data.rules_applied} rule(s)`, 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to apply rules', 'error') }
    finally { setApplyingBulk(false) }
  }

  const handleDeleteRule = async (ruleId: string, ruleName: string) => {
    if (!confirm(`Delete rule "${ruleName}"?`)) return
    try {
      const data = await apiFetch(`/session-rules/${ruleId}?session_id=${sessionId}`, { method: 'DELETE' })
      setRules(data.rules || []); flash('Rule deleted', 'success')
    } catch (err) { flash(err instanceof Error ? err.message : 'Failed to delete rule', 'error') }
  }

  const keywordsParsed = formData.keywords.split('\n').filter(k => k.trim())
  const selectedAccount = accounts.find(a => a.id === formData.account_id) || null

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-5">

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

      {/* ── Action buttons ──────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <button onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors">
          <Plus className="w-3.5 h-3.5" /> Create Rule
        </button>
        <button onClick={handleBulkApply} disabled={applyingBulk || rules.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          {applyingBulk ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
          {applyingBulk ? 'Applying...' : 'Bulk Apply Rules'}
        </button>
        {rules.length > 0 && (
          <span className="text-xs text-neutral-500">{rules.length} rule{rules.length !== 1 ? 's' : ''} defined</span>
        )}
      </div>

      {/* ── Create rule form ────────────────────────────────────── */}
      {showCreateForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-5 space-y-5">
          <h3 className="text-sm font-semibold text-neutral-800 flex items-center gap-2">
            <Plus className="w-4 h-4 text-blue-500" /> New Rule
          </h3>
          <form onSubmit={handleCreateRule} className="space-y-4">
            {/* step 1: keywords */}
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold mr-1.5">1</span>
                Keywords <span className="font-normal text-neutral-400">(one per line)</span>
              </label>
              <textarea
                placeholder={"spar\npick n pay\ncheckers"}
                value={formData.keywords} onChange={e => setFormData({ ...formData, keywords: e.target.value })}
                rows={3} disabled={loading}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300"
              />
              <p className="text-[11px] text-neutral-400 mt-1">Supports English &amp; Afrikaans</p>
            </div>

            {/* step 2: category + name */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold mr-1.5">2</span>
                  Target Category
                </label>
                <select value={formData.category} onChange={e => setFormData({ ...formData, category: e.target.value })} disabled={loading}
                  className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300">
                  <option value="">Select category...</option>
                  {categories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <p className="text-[11px] text-neutral-400 mt-1">Need a new category? Create it in the Categories tab first.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1.5">Rule Name</label>
                <input type="text" placeholder="e.g. Grocery stores"
                  value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} disabled={loading}
                  className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
                Target Account <span className="font-normal text-neutral-400">(optional)</span>
              </label>
              <AccountSelector
                clientId={currentClient?.id ?? null}
                value={formData.account_id}
                onChange={(id) => setFormData({ ...formData, account_id: id })}
                placeholder="Select account..."
                postableOnly
              />
            </div>

            {/* live preview */}
            {keywordsParsed.length > 0 && (formData.category || selectedAccount) && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                <p className="text-xs text-neutral-700">
                  If transaction contains
                  <span className="inline-flex flex-wrap gap-1 mx-1">
                    {keywordsParsed.slice(0, 4).map(k => (
                      <code key={k} className="rounded bg-white border border-emerald-200 px-1.5 py-0.5 text-[11px] font-mono text-emerald-700">{k}</code>
                    ))}
                    {keywordsParsed.length > 4 && <span className="text-[11px] text-neutral-400">+{keywordsParsed.length - 4} more</span>}
                  </span>
                  then map to
                  {formData.category && (
                    <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-blue-100 text-blue-700 border border-blue-200 px-2 py-0.5 text-[11px] font-semibold">
                      <Tag className="w-3 h-3" /> {formData.category}
                    </span>
                  )}
                  {selectedAccount && (
                    <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[11px] font-semibold">
                      <Layers className="w-3 h-3" /> <span className="font-mono">{selectedAccount.code}</span> {selectedAccount.name}
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* step 3: options */}
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-2">
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold mr-1.5">3</span>
                Options
              </label>
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 text-xs text-neutral-700 cursor-pointer">
                  <input type="checkbox" checked={formData.auto_apply} onChange={e => setFormData({ ...formData, auto_apply: e.target.checked })} disabled={loading}
                    className="w-4 h-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-300" />
                  Auto-apply on upload
                </label>
                <label className="flex items-center gap-2 text-xs text-neutral-700 cursor-pointer">
                  <input type="checkbox" checked={formData.match_compound_words} onChange={e => setFormData({ ...formData, match_compound_words: e.target.checked })} disabled={loading}
                    className="w-4 h-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-300" />
                  Match compound words
                </label>
                <div className="flex items-center gap-2 text-xs text-neutral-700">
                  <Hash className="w-3.5 h-3.5 text-neutral-400" />
                  <span>Priority:</span>
                  <input type="number" value={formData.priority} onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                    min={0} max={100} disabled={loading}
                    className="w-16 rounded border border-neutral-200 px-2 py-1 text-xs text-center focus:outline-none focus:ring-2 focus:ring-blue-200" />
                </div>
              </div>
            </div>

            {/* buttons */}
            <div className="flex gap-2 pt-3 border-t border-blue-100">
              <button type="submit" disabled={loading || !formData.keywords.trim() || (!formData.category && !formData.account_id) || !formData.name.trim()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors">
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Create Rule
              </button>
              <button type="button" onClick={() => setShowCreateForm(false)}
                className="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────── */}
      {rules.length === 0 && !showCreateForm && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-neutral-200 bg-neutral-50 py-12">
          <Settings2 className="w-10 h-10 text-neutral-300 mb-3" />
          <p className="text-sm font-medium text-neutral-700">No rules yet</p>
          <p className="text-xs text-neutral-400 mt-1">Create your first rule to start automatic categorization.</p>
        </div>
      )}

      {/* ── Rules list ──────────────────────────────────────────── */}
      {rules.length > 0 && (
        <div className="space-y-3">
          {rules.map(rule => {
            const isPreviewOpen = previewingRuleId === rule.rule_id
            const account = accounts.find(a => a.id === rule.account_id) || null
            return (
              <div key={rule.rule_id} className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden transition-shadow hover:shadow-md">
                <div className="px-5 py-4">
                  {/* rule description */}
                  <div className="mb-3">
                    <p className="text-sm text-neutral-700 leading-relaxed">
                      If transaction contains
                      <span className="inline-flex flex-wrap gap-1 mx-1">
                        {rule.keywords.slice(0, 4).map(kw => (
                          <code key={kw} className="rounded bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 text-[11px] font-mono text-neutral-700">{kw}</code>
                        ))}
                        {rule.keywords.length > 4 && <span className="text-[11px] text-neutral-400">+{rule.keywords.length - 4} more</span>}
                      </span>
                      then map to
                      {rule.category && (
                        <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 text-[11px] font-semibold">
                          <Tag className="w-3 h-3" /> {rule.category}
                        </span>
                      )}
                      {account && (
                        <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[11px] font-semibold">
                          <Layers className="w-3 h-3" /> <span className="font-mono">{account.code}</span> {account.name}
                        </span>
                      )}
                    </p>
                  </div>

                  {/* metadata + actions */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="rounded-full bg-neutral-100 text-neutral-600 px-2 py-0.5 text-[10px] font-medium">
                        Priority {rule.priority}
                      </span>
                      {rule.auto_apply && (
                        <span className="rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-semibold">
                          Auto-apply
                        </span>
                      )}
                      {rule.match_compound_words && (
                        <span className="rounded-full bg-violet-50 text-violet-700 border border-violet-200 px-2 py-0.5 text-[10px] font-semibold">
                          Compound
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => {
                          if (isPreviewOpen) { setPreviewingRuleId(null); setPreview(null) }
                          else { setPreviewingRuleId(rule.rule_id); handlePreviewRule(rule.rule_id) }
                        }}
                        className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          isPreviewOpen ? 'bg-neutral-100 text-neutral-700' : 'text-blue-600 hover:bg-blue-50'
                        }`}>
                        {isPreviewOpen ? <><EyeOff className="w-3.5 h-3.5" /> Hide</> : <><Eye className="w-3.5 h-3.5" /> Preview</>}
                      </button>
                      <button onClick={() => handleDeleteRule(rule.rule_id, rule.name)}
                        className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" /> Delete
                      </button>
                    </div>
                  </div>

                  {/* all keywords chips */}
                  {rule.keywords.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-neutral-100 flex flex-wrap gap-1.5">
                      {rule.keywords.map(kw => (
                        <span key={kw} className="rounded-full bg-neutral-100 text-neutral-600 px-2.5 py-0.5 text-[11px]">
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* preview panel */}
                {isPreviewOpen && (
                  <div className="border-t border-blue-100 bg-blue-50/50 px-5 py-4">
                    {previewLoading ? (
                      <div className="flex items-center gap-2 text-sm text-neutral-500">
                        <Loader2 className="w-4 h-4 animate-spin" /> Loading preview...
                      </div>
                    ) : preview ? (
                      <>
                        <p className="text-xs font-semibold text-blue-800 mb-2">
                          {preview.count} match{preview.count !== 1 ? 'es' : ''} ({preview.percentage}% of transactions)
                        </p>
                        {preview.matched.length > 0 ? (
                          <div className="rounded-lg border border-blue-200 bg-white overflow-hidden max-h-48 overflow-y-auto divide-y divide-blue-50">
                            {preview.matched.slice(0, 5).map(txn => (
                              <div key={txn.id} className="px-3 py-2.5 text-xs">
                                <p className="font-medium text-neutral-800 truncate">{txn.description}</p>
                                <div className="flex items-center gap-3 mt-0.5 text-neutral-500">
                                  <span>{txn.date}</span>
                                  <span className="font-semibold tabular-nums">R {Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                                  <span className="text-emerald-600">Matched: {txn.keyword_matched}</span>
                                </div>
                              </div>
                            ))}
                            {preview.matched.length > 5 && (
                              <div className="px-3 py-2 text-center text-[11px] text-neutral-400 bg-neutral-50">
                                ...and {preview.matched.length - 5} more
                              </div>
                            )}
                          </div>
                        ) : (
                          <p className="text-xs text-neutral-500">No transactions match this rule in the current session.</p>
                        )}
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
