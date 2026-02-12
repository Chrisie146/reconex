'use client'

import React, { useState, useEffect } from 'react'
import { Sparkles, Trash2, Edit2, Power, PowerOff, RefreshCw, Info, TrendingUp } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

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

interface LearnedRulesManagerProps {
  sessionId: string
}

export default function LearnedRulesManager({ sessionId }: LearnedRulesManagerProps) {
  const [rules, setRules] = useState<LearnedRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingRule, setEditingRule] = useState<number | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [showInfo, setShowInfo] = useState(false)
  const [applyingRules, setApplyingRules] = useState(false)

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'

  useEffect(() => {
    fetchRules()
  }, [])

  const fetchRules = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch(`${API_BASE}/learned-rules`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch learned rules')
      }
      
      const data = await response.json()
      setRules(data.rules || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load learned rules')
    } finally {
      setLoading(false)
    }
  }

  const updateRule = async (ruleId: number, updates: Partial<LearnedRule>) => {
    try {
      const response = await apiFetch(
        `${API_BASE}/learned-rules/${ruleId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        }
      )

      if (!response.ok) {
        throw new Error('Failed to update rule')
      }

      await fetchRules()
      setEditingRule(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update rule')
    }
  }

  const deleteRule = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this learned pattern?')) {
      return
    }

    try {
      const response = await apiFetch(
        `${API_BASE}/learned-rules/${ruleId}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error('Failed to delete rule')
      }

      await fetchRules()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete rule')
    }
  }

  const toggleEnabled = async (rule: LearnedRule) => {
    await updateRule(rule.id, { enabled: !rule.enabled })
  }

  const startEdit = (rule: LearnedRule) => {
    setEditingRule(rule.id)
    setEditCategory(rule.category)
  }

  const saveEdit = async (ruleId: number) => {
    await updateRule(ruleId, { category: editCategory })
  }

  const applyRules = async () => {
    if (!sessionId) {
      alert('Please upload a statement first to apply learned rules')
      return
    }

    if (!confirm('Apply all learned rules to current transactions? This will auto-categorize transactions based on learned patterns.')) {
      return
    }

    try {
      setApplyingRules(true)
      const response = await apiFetch(
        `${API_BASE}/learned-rules/apply?session_id=${sessionId}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error('Failed to apply rules')
      }

      const data = await response.json()
      alert(`✓ ${data.message}`)
      
      // Refresh the page or trigger a transaction refresh
      window.location.reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to apply rules')
    } finally {
      setApplyingRules(false)
    }
  }

  const getPatternTypeLabel = (type: string) => {
    switch (type) {
      case 'exact': return '🎯 Exact'
      case 'merchant': return '🏪 Merchant'
      case 'starts_with': return '▶️ Starts With'
      case 'contains': return '🔍 Contains'
      default: return type
    }
  }

  const getPatternTypeDescription = (type: string) => {
    switch (type) {
      case 'exact': return 'Matches exact transaction description'
      case 'merchant': return 'Matches extracted merchant name'
      case 'starts_with': return 'Matches transactions starting with this pattern'
      case 'contains': return 'Matches if pattern appears anywhere'
      default: return type
    }
  }

  const getSimplePatternDescription = (type: string) => {
    switch (type) {
      case 'exact': return 'is exactly'
      case 'merchant': return 'merchant is'
      case 'starts_with': return 'starts with'
      case 'contains': return 'contains'
      default: return type
    }
  }

  const totalUseCount = rules.reduce((sum, rule) => sum + rule.use_count, 0)
  const enabledCount = rules.filter(r => r.enabled).length
  const avgUseCount = rules.length > 0 ? (totalUseCount / rules.length).toFixed(1) : 0

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading learned patterns...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
          <button
            onClick={fetchRules}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Sparkles className="text-purple-600" size={24} />
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Learned Categorization Patterns</h2>
              <p className="text-sm text-gray-600 mt-1">
                Automatically learned from your categorization decisions
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="How this works"
          >
            <Info size={20} className="text-gray-600" />
          </button>
        </div>

        {/* Info Panel */}
        {showInfo && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">How Auto-Learning Works</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• When you categorize a transaction, the system learns patterns</li>
              <li>• On future uploads, similar transactions are auto-categorized</li>
              <li>• You can edit or disable any learned pattern</li>
              <li>• Rules are applied automatically on each new statement upload</li>
            </ul>
          </div>
        )}

        {/* Stats */}
        <div className="mt-4 grid grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-3">
            <div className="text-sm text-purple-600 font-medium">Total Patterns</div>
            <div className="text-2xl font-bold text-purple-900">{rules.length}</div>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-3">
            <div className="text-sm text-green-600 font-medium">Active</div>
            <div className="text-2xl font-bold text-green-900">{enabledCount}</div>
          </div>
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-3">
            <div className="text-sm text-blue-600 font-medium">Total Uses</div>
            <div className="text-2xl font-bold text-blue-900">{totalUseCount}</div>
          </div>
          <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-3">
            <div className="text-sm text-orange-600 font-medium">Avg Uses</div>
            <div className="text-2xl font-bold text-orange-900">{avgUseCount}</div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex space-x-3">
          <button
            onClick={applyRules}
            disabled={applyingRules || rules.length === 0}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {applyingRules ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Applying...</span>
              </>
            ) : (
              <>
                <RefreshCw size={16} />
                <span>Re-Apply All Rules</span>
              </>
            )}
          </button>
          <button
            onClick={fetchRules}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Rules List */}
      <div className="p-6">
        {rules.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <Sparkles className="mx-auto text-gray-400 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Learned Patterns Yet</h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Start categorizing transactions! The system will automatically learn patterns and help categorize future uploads.
            </p>
            <div className="mt-4 text-sm text-gray-500">
              <TrendingUp className="inline mr-1" size={16} />
              Typically saves 70-90% of categorization time from the second upload onwards
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className={`border rounded-lg p-4 transition-all ${
                  rule.enabled
                    ? 'border-gray-200 bg-white hover:shadow-md'
                    : 'border-gray-100 bg-gray-50 opacity-60'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {/* Simplified natural language rule display */}
                    <div className="mb-3">
                      <p className="text-sm text-gray-800">
                        If transaction {getSimplePatternDescription(rule.pattern_type)} 
                        <span className="font-mono font-semibold text-gray-900 mx-1">"{rule.pattern_value}"</span>
                        then categorize as 
                        <span className="font-semibold text-purple-700 mx-1">"{rule.category}"</span>
                      </p>
                    </div>

                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <TrendingUp size={14} />
                        <span>Used {rule.use_count} times</span>
                      </div>
                      {rule.last_used && (
                        <span>Last used: {new Date(rule.last_used).toLocaleDateString()}</span>
                      )}
                    </div>

                    {editingRule === rule.id ? (
                      <div className="flex items-center space-x-2 mt-3">
                        <span className="text-gray-600">Edit category:</span>
                        <input
                          type="text"
                          value={editCategory}
                          onChange={(e) => setEditCategory(e.target.value)}
                          className="px-3 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                          autoFocus
                        />
                        <button
                          onClick={() => saveEdit(rule.id)}
                          className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingRule(null)}
                          className="px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 text-xs"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : null}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => toggleEnabled(rule)}
                      className={`p-2 rounded hover:bg-gray-100 transition-colors ${
                        rule.enabled ? 'text-green-600' : 'text-gray-400'
                      }`}
                      title={rule.enabled ? 'Disable' : 'Enable'}
                    >
                      {rule.enabled ? <Power size={18} /> : <PowerOff size={18} />}
                    </button>
                    <button
                      onClick={() => startEdit(rule)}
                      className="p-2 rounded hover:bg-gray-100 text-blue-600 transition-colors"
                      title="Edit category"
                    >
                      <Edit2 size={18} />
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      className="p-2 rounded hover:bg-gray-100 text-red-600 transition-colors"
                      title="Delete pattern"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
