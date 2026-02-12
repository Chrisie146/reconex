"use client"

import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import LoadingButton from './LoadingButton'

interface RulesManagerProps {
  sessionId: string
}

interface Rule {
  rule_id: string
  name: string
  category: string
  keywords: string[]
  priority: number
  auto_apply: boolean
  enabled: boolean
  match_compound_words: boolean
}

interface RulePreview {
  matched: Array<{
    id: number
    date: string
    description: string
    amount: number
    keyword_matched: string
  }>
  count: number
  percentage: number
  rule_name: string
  category: string
}

export default function RulesManager({ sessionId }: RulesManagerProps) {
  const [rules, setRules] = useState<Rule[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  // Form state
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    keywords: '',
    priority: 10,
    auto_apply: true,
    match_compound_words: false
  })
  
  // Preview state
  const [previewingRuleId, setPreviewingRuleId] = useState<string | null>(null)
  const [preview, setPreview] = useState<RulePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [applyingBulk, setApplyingBulk] = useState(false)

  useEffect(() => {
    loadRulesAndCategories()
  }, [sessionId])

  const loadRulesAndCategories = async () => {
    setLoading(true)
    try {
      const [rulesRes, categoriesRes] = await Promise.all([
        apiFetch(`/rules?session_id=${sessionId}`),
        apiFetch(`/categories?session_id=${sessionId}`)
      ])

      if (!rulesRes.ok || !categoriesRes.ok) throw new Error('Failed to load data')

      const rulesData = await rulesRes.json()
      const categoriesData = await categoriesRes.json()

      setRules(rulesData.rules || [])
      setCategories(categoriesData.categories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!formData.name.trim() || !formData.category || !formData.keywords.trim()) {
      setError('Please fill in all fields')
      return
    }

    // Verify category exists
    if (!categories.includes(formData.category)) {
      setError(`Category "${formData.category}" does not exist. Create it in the Categories tab first, then create the rule.`)
      return
    }

    const keywords = formData.keywords.split('\n').map(k => k.trim()).filter(k => k)
    if (keywords.length === 0) {
      setError('Please enter at least one keyword')
      return
    }

    setLoading(true)
    try {
      const response = await apiFetch(`/rules?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          category: formData.category,
          keywords: keywords,
          priority: formData.priority,
          auto_apply: formData.auto_apply,
          match_compound_words: formData.match_compound_words
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to create rule')
      }

      const data = await response.json()
      setRules(data.rules || [])
      setFormData({ name: '', category: '', keywords: '', priority: 10, auto_apply: true, match_compound_words: false })
      setShowCreateForm(false)
      setSuccess('Rule created successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule')
    } finally {
      setLoading(false)
    }
  }

  const handlePreviewRule = async (ruleId: string) => {
    setPreviewLoading(true)
    try {
      const response = await apiFetch(`/rules/${ruleId}/preview?session_id=${sessionId}`, {
        method: 'POST'
      })

      if (!response.ok) throw new Error('Failed to load preview')
      const data = await response.json()
      setPreview(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleBulkApply = async () => {
    if (!confirm(`Apply all enabled rules to transactions?`)) return

    setApplyingBulk(true)
    try {
      const response = await apiFetch(`/rules/apply-bulk?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_apply_only: false })
      })

      if (!response.ok) throw new Error('Failed to apply rules')
      const data = await response.json()
      setSuccess(`${data.updated_count} transaction(s) categorized using ${data.rules_applied} rule(s)`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply rules')
    } finally {
      setApplyingBulk(false)
    }
  }

  const handleDeleteRule = async (ruleId: string, ruleName: string) => {
    if (!confirm(`Delete rule "${ruleName}"?`)) return

    try {
      const response = await apiFetch(`/rules/${ruleId}?session_id=${sessionId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete rule')
      const data = await response.json()
      setRules(data.rules || [])
      setSuccess('Rule deleted')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule')
    }
  }

  return (
    <div className="space-y-6">
      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
        >
          + Create Rule
        </button>
        <button
          onClick={handleBulkApply}
          disabled={applyingBulk || rules.length === 0}
          className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 font-medium"
        >
          {applyingBulk ? 'Applying...' : '⚡ Bulk Apply Rules'}
        </button>
      </div>

      {/* Create Rule Form */}
      {showCreateForm && (
        <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Create New Rule</h2>
          <form onSubmit={handleCreateRule} className="space-y-6">
            
            {/* Keywords Input */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Step 1: Enter Keywords (one per line)
              </label>
              <textarea
                placeholder="spar&#10;pick n pay&#10;checkers&#10;kruideniersware"
                value={formData.keywords}
                onChange={e => setFormData({ ...formData, keywords: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm"
                disabled={loading}
              />
              <p className="text-xs text-gray-600 mt-1">💡 Supports English & Afrikaans keywords</p>
            </div>

            {/* Category Select */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Step 2: Select Category
              </label>
              <select
                value={formData.category}
                onChange={e => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                disabled={loading}
              >
                <option value="">Select category...</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <p className="text-xs text-gray-600 mt-1">💡 Don't see your category? Create it in the <strong>Categories</strong> tab first</p>
            </div>

            {/* Live Preview */}
            {formData.keywords.trim() && formData.category && (
              <div className="bg-white border-2 border-green-200 rounded-lg p-4">
                <p className="text-xs font-semibold text-green-800 mb-2">✓ Preview</p>
                <p className="text-sm text-gray-800">
                  If transaction contains any of: 
                  <span className="font-mono font-semibold text-gray-900 ml-1">
                    {formData.keywords.split('\n').slice(0, 3).filter(k => k.trim()).join(', ')}
                    {formData.keywords.split('\n').filter(k => k.trim()).length > 3 ? `, +${formData.keywords.split('\n').filter(k => k.trim()).length - 3} more` : ''}
                  </span>
                </p>
                <p className="text-sm text-gray-800 mt-1">
                  then categorize as 
                  <span className="font-semibold text-blue-700 mx-1">"{formData.category}"</span>
                </p>
              </div>
            )}

            {/* Options */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-3">
                Step 3: Configure Options
              </label>
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.auto_apply}
                    onChange={e => setFormData({ ...formData, auto_apply: e.target.checked })}
                    className="w-4 h-4"
                    disabled={loading}
                  />
                  <span className="text-sm font-medium text-gray-800">Apply automatically to new uploads</span>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.match_compound_words}
                    onChange={e => setFormData({ ...formData, match_compound_words: e.target.checked })}
                    className="w-4 h-4"
                    disabled={loading}
                  />
                  <span className="text-sm font-medium text-gray-800">Match within compound words</span>
                </label>

                <div className="pt-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Priority (lower = higher priority)
                  </label>
                  <input
                    type="number"
                    value={formData.priority}
                    onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                    min={0}
                    max={100}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    disabled={loading}
                  />
                </div>
              </div>
            </div>

            {/* Error */}
            {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">{error}</div>}

            {/* Buttons */}
            <div className="flex gap-3 pt-4 border-t border-gray-200">
              <button
                type="submit"
                disabled={loading || !formData.keywords.trim() || !formData.category}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium"
              >
                {loading ? 'Creating...' : '✓ Create Rule'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rules List */}
      {rules.length === 0 && !showCreateForm && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <p className="text-gray-600">No rules created yet. Create your first rule to start automatic categorization.</p>
        </div>
      )}
      {rules.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Active Rules ({rules.length})</h2>
          <div className="space-y-3">
            {rules.map(rule => (
              <div key={rule.rule_id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                {/* Simplified natural language rule display */}
                <div className="mb-3">
                  <p className="text-sm text-gray-800 font-medium mb-2">
                    If transaction contains any of: 
                    <span className="font-mono font-semibold text-gray-900 ml-1">
                      {rule.keywords.slice(0, 3).join(', ')}{rule.keywords.length > 3 ? `, +${rule.keywords.length - 3} more` : ''}
                    </span>
                  </p>
                  <p className="text-sm text-gray-800">
                    then categorize as 
                    <span className="font-semibold text-blue-700 mx-1">"{rule.category}"</span>
                  </p>
                </div>

                {/* Rule metadata */}
                <div className="flex items-center space-x-4 text-xs text-gray-600 mb-3">
                  <span>Priority: {rule.priority}</span>
                  {rule.auto_apply && <span className="bg-green-100 text-green-800 px-2 py-1 rounded">Auto-apply</span>}
                  {rule.match_compound_words && <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">Compound words</span>}
                </div>

                {/* All keywords */}
                {rule.keywords.length > 0 && (
                  <div className="mb-3 pb-3 border-b border-gray-100">
                    <div className="flex flex-wrap gap-2">
                      {rule.keywords.map(kw => (
                        <span key={kw} className="inline-block bg-gray-100 px-3 py-1 rounded-full text-xs text-gray-700">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <button
                    onClick={() => {
                      if (previewingRuleId === rule.rule_id) {
                        setPreviewingRuleId(null)
                        setPreview(null)
                      } else {
                        setPreviewingRuleId(rule.rule_id)
                        handlePreviewRule(rule.rule_id)
                      }
                    }}
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    {previewingRuleId === rule.rule_id ? '✕ Hide Preview' : '👁️ Preview Matches'}
                  </button>
                  <button
                    onClick={() => handleDeleteRule(rule.rule_id, rule.name)}
                    className="text-red-600 hover:text-red-700 font-medium text-sm"
                  >
                    Delete
                  </button>
                </div>

                {/* Preview */}
                {previewingRuleId === rule.rule_id && preview && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
                    <p className="text-sm font-medium text-blue-900 mb-3">
                      {preview.count} transaction(s) would match this rule ({preview.percentage}%)
                    </p>
                    {preview.matched.length > 0 && (
                      <div className="bg-white rounded border border-blue-200 overflow-hidden max-h-48 overflow-y-auto">
                        {preview.matched.slice(0, 5).map(txn => (
                          <div key={txn.id} className="p-3 border-b border-blue-100 last:border-b-0 text-sm">
                            <div className="font-medium text-gray-900">{txn.description}</div>
                            <div className="text-xs text-gray-600 mt-1">{txn.date} • R{txn.amount}</div>
                            <div className="text-xs text-green-600 mt-1">Matched by: {txn.keyword_matched}</div>
                          </div>
                        ))}
                        {preview.matched.length > 5 && (
                          <div className="p-3 bg-gray-50 text-sm text-gray-600 text-center">
                            ...and {preview.matched.length - 5} more
                          </div>
                        )}
                      </div>
                    )}
                    {preview.matched.length === 0 && (
                      <p className="text-sm text-gray-600">No transactions match this rule in the current session.</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {success && <div className="p-4 bg-green-50 border border-green-200 rounded text-green-700 text-sm">{success}</div>}
    </div>
  )
}
