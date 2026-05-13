"use client"

import React, { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Check, CheckCircle2, Layers, Loader2, Plus, RefreshCw, Search, Tag, Trash2, X, Zap, Edit2, Save } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'
import { useClient } from '@/lib/clientContext'
import AccountSelector from './AccountSelector'
import { useAccounts } from '@/lib/hooks/useAccounts'

interface RulesManagerProps {
  sessionId: string
}

type RuleAction = {
  type: 'set_category' | 'set_account' | 'set_merchant'
  category?: string | null
  account_id?: number | null
  account_code?: string
  merchant?: string
}

type RuleCondition = {
  field: string
  op: string
  value: string
}

interface Rule {
  id: number
  name: string
  enabled: boolean
  priority: number
  conditions: {
    match_type?: 'all' | 'any'
    conditions?: RuleCondition[]
  }
  action: RuleAction
  auto_apply: boolean
}

interface PreviewState {
  ruleId: number
  loading: boolean
  matches: Array<{ id: number; description: string; amount: number; category?: string | null; account_id?: number | null }>
  count: number
}

interface EditingState {
  ruleId: number
  keyword: string
  category: string
  account_id: number | null
}

const defaultForm = {
  keyword: '',
  name: '',
  category: '',
  account_id: null as number | null,
  auto_apply: true,
  priority: 100,
}

function getRuleKeywords(rule: Rule) {
  return (rule.conditions?.conditions || [])
    .filter(c => c.field === 'description' && c.op === 'contains')
    .map(c => c.value)
    .filter(Boolean)
}

export default function RulesManager({ sessionId }: RulesManagerProps) {
  const { currentClient } = useClient()
  const { accounts } = useAccounts(currentClient?.id ?? null, { postable: true })
  const [rules, setRules] = useState<Rule[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [form, setForm] = useState(defaultForm)
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const [editing, setEditing] = useState<EditingState | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [applying, setApplying] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const selectedAccount = accounts.find(a => a.id === form.account_id) || null

  useEffect(() => {
    loadData()
  }, [currentClient?.id, sessionId])

  function flash(type: 'success' | 'error', text: string) {
    setMessage({ type, text })
    window.setTimeout(() => setMessage(null), type === 'success' ? 3500 : 6000)
  }

  async function loadData() {
    if (!currentClient?.id) return
    setLoading(true)
    try {
      const [rulesData, categoriesData] = await Promise.all([
        apiFetch(`/rules?client_id=${currentClient.id}`),
        apiFetch(`/categories?session_id=${sessionId}&client_id=${currentClient.id}`),
      ])
      setRules(rulesData.rules || [])
      setCategories((categoriesData.categories || []).map((cat: any) => typeof cat === 'string' ? cat : cat.name))
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to load rules')
    } finally {
      setLoading(false)
    }
  }

  async function createRule(e: React.FormEvent) {
    e.preventDefault()
    if (!currentClient?.id) {
      flash('error', 'Select a client first')
      return
    }

    const keyword = form.keyword.trim()
    const category = form.category.trim()
    if (keyword.length < 3) {
      flash('error', 'Enter a keyword with at least 3 characters')
      return
    }
    if (!category && form.account_id == null) {
      flash('error', 'Choose a category, an account, or both')
      return
    }

    setSaving(true)
    try {
      const account = accounts.find(a => a.id === form.account_id) || null
      const ruleName = form.name.trim() || `${keyword} -> ${category || account?.name || 'Account'}`
      await apiFetch(`/rules?client_id=${currentClient.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: ruleName,
          enabled: true,
          priority: form.priority,
          conditions: {
            match_type: 'any',
            conditions: [{ field: 'description', op: 'contains', value: keyword }],
          },
          action: {
            type: 'set_category',
            category: category || null,
            account_id: form.account_id,
          },
          auto_apply: form.auto_apply,
        }),
      })
      setForm(defaultForm)
      setShowCreate(false)
      await loadData()
      flash('success', 'Rule saved')
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to save rule')
    } finally {
      setSaving(false)
    }
  }

  async function deleteRule(rule: Rule) {
    if (!confirm(`Delete rule "${rule.name}"?`)) return
    try {
      await apiFetch(`/rules/${rule.id}`, { method: 'DELETE' })
      setRules(rules.filter(r => r.id !== rule.id))
      flash('success', 'Rule deleted')
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to delete rule')
    }
  }

  async function updateRule(rule: Rule, updates: Partial<Rule>) {
    try {
      await apiFetch(`/rules/${rule.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      setRules(rules.map(r => r.id === rule.id ? { ...r, ...updates } : r))
      setEditing(null)
      flash('success', 'Rule updated')
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to update rule')
    }
  }

  async function updateRuleQuick(rule: Rule, updates: Partial<Rule>) {
    try {
      await apiFetch(`/rules/${rule.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      setRules(rules.map(r => r.id === rule.id ? { ...r, ...updates } : r))
      flash('success', 'Rule updated')
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to update rule')
    }
  }

  async function saveEditing(rule: Rule) {
    if (!editing || editing.ruleId !== rule.id) return
    const keyword = editing.keyword.trim()
    if (keyword.length < 3) {
      flash('error', 'Keyword must be at least 3 characters')
      return
    }
    setSaving(true)
    try {
      const updates: Partial<Rule> = {
        conditions: {
          match_type: 'any',
          conditions: [{ field: 'description', op: 'contains', value: keyword }],
        },
        action: {
          ...rule.action,
          category: editing.category || null,
          account_id: editing.account_id ?? null,
        },
      }
      await updateRule(rule, updates)
    } finally {
      setSaving(false)
    }
  }

  async function previewRule(rule: Rule) {
    setPreview({ ruleId: rule.id, loading: true, matches: [], count: 0 })
    try {
      const data = await apiFetch(`/rules/${rule.id}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      setPreview({ ruleId: rule.id, loading: false, matches: data.matches || [], count: data.count || 0 })
    } catch (err) {
      setPreview(null)
      flash('error', err instanceof Error ? err.message : 'Preview failed')
    }
  }

  async function applyRule(rule: Rule) {
    if (!confirm(`Apply "${rule.name}" to matching transactions in this statement?`)) return
    setApplying(true)
    try {
      const data = await apiFetch(`/rules/${rule.id}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      flash('success', data.message || `Updated ${data.updated_count || 0} transaction(s)`)
      setPreview(null)
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to apply rule')
    } finally {
      setApplying(false)
    }
  }

  async function applyAllRules() {
    const enabled = rules.filter(r => r.enabled)
    if (enabled.length === 0) return
    if (!confirm(`Apply ${enabled.length} enabled rule(s) to this statement?`)) return
    setApplying(true)
    try {
      let total = 0
      for (const rule of enabled) {
        const data = await apiFetch(`/rules/${rule.id}/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        })
        total += Number(data.updated_count || 0)
      }
      flash('success', `Updated ${total} transaction(s)`)
      setPreview(null)
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Failed to apply rules')
    } finally {
      setApplying(false)
    }
  }

  const filteredRules = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return rules
    return rules.filter(rule => {
      const account = accounts.find(a => a.id === rule.action.account_id)
      return (
        rule.name.toLowerCase().includes(q) ||
        getRuleKeywords(rule).some(k => k.toLowerCase().includes(q)) ||
        (rule.action.category || '').toLowerCase().includes(q) ||
        (account?.name || '').toLowerCase().includes(q) ||
        (account?.code || '').toLowerCase().includes(q)
      )
    })
  }, [rules, search, accounts])

  if (!currentClient?.id) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
        Select a client before creating rules.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {message && (
        <div className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${
          message.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'
        }`}>
          {message.type === 'success' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
          <span className="flex-1">{message.text}</span>
          <button onClick={() => setMessage(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
        Rules are saved to the selected client and run automatically on future uploads when Auto-apply is on. Use Apply to current statement for transactions already uploaded.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700"
        >
          <Plus className="h-3.5 w-3.5" /> New rule
        </button>
        <button
          onClick={applyAllRules}
          disabled={applying || rules.filter(r => r.enabled).length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {applying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
          Apply to current statement
        </button>
        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-40"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {showCreate && (
        <form onSubmit={createRule} className="space-y-5 rounded-lg border border-neutral-200 bg-white p-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_220px]">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-neutral-700">If description contains</label>
              <input
                value={form.keyword}
                onChange={e => setForm({ ...form, keyword: e.target.value })}
                placeholder="e.g. checkers, fnb fee, vodacom"
                className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-neutral-700">Priority</label>
              <input
                type="number"
                value={form.priority}
                onChange={e => setForm({ ...form, priority: Number(e.target.value || 100) })}
                className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-neutral-700">Map to category</label>
              <select
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="">No category change</option>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-neutral-700">Map to Chart of Accounts</label>
              <AccountSelector
                clientId={currentClient.id}
                value={form.account_id}
                onChange={(id) => setForm({ ...form, account_id: id })}
                placeholder="No account mapping"
                postableOnly
              />
            </div>
          </div>

          {(form.keyword.trim() || form.category || selectedAccount) && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-900">
              <span>When description contains </span>
              <code className="rounded bg-white px-1.5 py-0.5 font-mono">{form.keyword.trim() || 'keyword'}</code>
              <span>, map to </span>
              {form.category && <TargetPill icon="category" label={form.category} />}
              {selectedAccount && <TargetPill icon="account" label={`${selectedAccount.code} ${selectedAccount.name}`} />}
              {!form.category && !selectedAccount && <span className="text-emerald-700">choose a category or account</span>}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-neutral-700">Rule name</label>
              <input
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Optional, generated if left blank"
                className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <label className="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={form.auto_apply}
                onChange={e => setForm({ ...form, auto_apply: e.target.checked })}
                className="h-4 w-4 rounded border-neutral-300 text-blue-600"
              />
              Auto-apply on upload
            </label>
          </div>

          <div className="flex gap-2 border-t border-neutral-100 pt-4">
            <button
              type="submit"
              disabled={saving || form.keyword.trim().length < 3 || (!form.category && form.account_id == null)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />} Save rule
            </button>
            <button
              type="button"
              onClick={() => { setShowCreate(false); setForm(defaultForm) }}
              className="rounded-lg border border-neutral-200 px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search rules, categories, accounts..."
          className="w-full rounded-lg border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
      </div>

      {filteredRules.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-neutral-200 bg-neutral-50 py-12 text-center">
          <p className="text-sm font-medium text-neutral-700">{rules.length === 0 ? 'No rules yet' : 'No matching rules'}</p>
          <p className="mt-1 text-xs text-neutral-400">Create a rule to map repeated bank descriptions to categories and accounts.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50">
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Description</th>
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Contains</th>
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Map to Account</th>
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Map to Category</th>
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Auto-apply</th>
                <th className="px-4 py-3 text-left font-semibold text-neutral-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {filteredRules.map(rule => {
                const keywords = getRuleKeywords(rule)
                const account = accounts.find(a => a.id === rule.action.account_id) || null
                const isEditing = editing?.ruleId === rule.id
                const isPreviewOpen = preview?.ruleId === rule.id

                return (
                  <React.Fragment key={rule.id}>
                    <tr className={`${isEditing ? 'bg-blue-50' : 'hover:bg-neutral-50'} ${!rule.enabled ? 'opacity-50' : ''}`}>
                      {/* Description */}
                      <td className="px-4 py-3">
                        <p className="font-medium text-neutral-900">{rule.name}</p>
                        {!rule.enabled && <span className="text-[10px] font-semibold text-neutral-500">Disabled</span>}
                      </td>

                      {/* Contains */}
                      <td className="px-4 py-3">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editing.keyword}
                            onChange={e => setEditing({ ...editing, keyword: e.target.value })}
                            className="w-full rounded border border-blue-300 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="e.g. CHECKERS, FNB FEE"
                          />
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {keywords.length > 0 ? keywords.map(k => (
                              <code key={k} className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-[11px]">{k}</code>
                            )) : <span className="text-neutral-400 text-[11px]">custom conditions</span>}
                          </div>
                        )}
                      </td>

                      {/* Map to Account */}
                      <td className="px-4 py-3">
                        {isEditing ? (
                          <AccountSelector
                            clientId={currentClient.id}
                            value={editing.account_id}
                            onChange={(id) => setEditing({ ...editing, account_id: id })}
                            placeholder="None"
                            postableOnly
                          />
                        ) : (
                          <span className={account ? 'font-medium text-neutral-900' : 'text-neutral-400'}>
                            {account ? `${account.code} ${account.name}` : '—'}
                          </span>
                        )}
                      </td>

                      {/* Map to Category */}
                      <td className="px-4 py-3">
                        {isEditing ? (
                          <select
                            value={editing.category}
                            onChange={e => setEditing({ ...editing, category: e.target.value })}
                            className="w-full rounded border border-blue-300 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            <option value="">None</option>
                            {categories.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                        ) : (
                          <span className={rule.action.category ? 'font-medium text-neutral-900' : 'text-neutral-400'}>
                            {rule.action.category || '—'}
                          </span>
                        )}
                      </td>

                      {/* Auto-apply */}
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={rule.auto_apply}
                          onChange={e => updateRuleQuick(rule, { auto_apply: e.target.checked })}
                          aria-label={`Toggle auto-apply for ${rule.name}`}
                          className="h-4 w-4 rounded border-neutral-300 text-blue-600 cursor-pointer"
                        />
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div className="flex gap-1.5">
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => saveEditing(rule)}
                                disabled={saving}
                                aria-label="Save rule"
                                className="rounded px-2 py-1 text-xs font-medium text-emerald-700 border border-emerald-200 hover:bg-emerald-50 disabled:opacity-40"
                              >
                                <Save className="inline h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => setEditing(null)}
                                aria-label="Cancel editing"
                                className="rounded px-2 py-1 text-xs font-medium text-neutral-600 border border-neutral-200 hover:bg-neutral-50"
                              >
                                <X className="inline h-3.5 w-3.5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => setEditing({
                                  ruleId: rule.id,
                                  keyword: keywords.join(', '),
                                  category: rule.action.category || '',
                                  account_id: rule.action.account_id ?? null,
                                })}
                                aria-label={`Edit ${rule.name}`}
                                className="rounded px-2 py-1 text-xs font-medium text-neutral-600 border border-neutral-200 hover:bg-neutral-50"
                              >
                                <Edit2 className="inline h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => isPreviewOpen ? setPreview(null) : previewRule(rule)}
                                className="rounded px-2 py-1 text-xs font-medium text-neutral-600 border border-neutral-200 hover:bg-neutral-50"
                              >
                                Preview
                              </button>
                              <button
                                onClick={() => applyRule(rule)}
                                disabled={applying}
                                className="rounded px-2 py-1 text-xs font-medium text-blue-700 border border-blue-200 hover:bg-blue-50 disabled:opacity-40"
                              >
                                Apply
                              </button>
                              <button
                                onClick={() => deleteRule(rule)}
                                aria-label={`Delete ${rule.name}`}
                                className="rounded px-2 py-1 text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50"
                              >
                                <Trash2 className="inline h-3.5 w-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>

                    {isPreviewOpen && (
                      <tr className="bg-blue-50">
                        <td colSpan={6} className="px-4 py-3">
                          {preview.loading ? (
                            <div className="flex items-center gap-2 text-sm text-neutral-500">
                              <Loader2 className="h-4 w-4 animate-spin" /> Loading preview...
                            </div>
                          ) : preview.count === 0 ? (
                            <p className="text-sm text-neutral-500">No transactions in this statement match this rule.</p>
                          ) : (
                            <>
                              <p className="mb-2 text-xs font-semibold text-blue-800">{preview.count} matching transaction(s)</p>
                              <div className="max-h-56 divide-y divide-blue-100 overflow-y-auto rounded border border-blue-100 bg-white">
                                {preview.matches.slice(0, 8).map(txn => (
                                  <div key={txn.id} className="px-3 py-2 text-xs">
                                    <p className="truncate font-medium text-neutral-800">{txn.description}</p>
                                    <p className="mt-0.5 text-neutral-500">R {Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</p>
                                  </div>
                                ))}
                              </div>
                            </>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function TargetPill({ icon, label }: { icon: 'category' | 'account'; label: string }) {
  const Icon = icon === 'category' ? Tag : Layers
  const className = icon === 'category'
    ? 'bg-blue-50 text-blue-700 border-blue-200'
    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
  return (
    <span className={`ml-1 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${className}`}>
      <Icon className="h-3 w-3" /> {label}
    </span>
  )
}
