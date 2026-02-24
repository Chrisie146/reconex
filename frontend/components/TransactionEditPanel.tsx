'use client'

import { X, Loader2, AlertCircle, CheckCircle, AlertTriangle, Plus, Pencil, Tag, Store, Sparkles, Copy, Save } from 'lucide-react'
import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Helper function to clean NaN-like values
const cleanDescription = (desc: string | null | undefined): string => {
  if (!desc) return ''
  const cleaned = desc.trim()
  if (cleaned.toLowerCase() === 'nan' || cleaned.toLowerCase() === 'none' || cleaned === '-') {
    return ''
  }
  return cleaned
}

interface Transaction {
  id: number
  session_id?: string
  date: string
  description: string
  amount: number
  category: string
  merchant?: string | null
  vat_amount?: number | null
  amount_excl_vat?: number | null
  amount_incl_vat?: number | null
  statement_name?: string
}

interface TransactionEditPanelProps {
  isOpen: boolean
  transaction: Transaction | null
  sessionId: string
  clientId?: number | null
  categories: string[]
  onClose: () => void
  onSave?: (updatedTransaction: Transaction) => void
  onCategoryCreated?: (newCategories: string[]) => void
  onRefresh?: () => void
}

export default function TransactionEditPanel({
  isOpen,
  transaction,
  sessionId,
  clientId,
  categories,
  onClose,
  onSave,
  onCategoryCreated,
  onRefresh,
}: TransactionEditPanelProps) {
  const [category, setCategory] = useState('')
  const [merchant, setMerchant] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showCreateCategory, setShowCreateCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [createError, setCreateError] = useState('')
  const [appliedRules, setAppliedRules] = useState<any[]>([])
  const [learnRule, setLearnRule] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [applyMerchantSimilar, setApplyMerchantSimilar] = useState(false)
  const [applyCategorySimilar, setApplyCategorySimilar] = useState(false)
  const [merchantKeyword, setMerchantKeyword] = useState('')
  const [categoryKeyword, setCategoryKeyword] = useState('')
  const [description, setDescription] = useState('')
  const [editingDescription, setEditingDescription] = useState(false)

  // Extract keyword from description
  const extractKeyword = (description: string): string => {
    const words = description.split(/\s+/)
    const commonWords = ['the', 'a', 'an', 'deposit', 'payment', 'transfer', 'pos', 'purchase']
    for (const word of words) {
      const clean = word.toLowerCase().replace(/[^a-z0-9]/g, '')
      if (clean.length >= 3 && !commonWords.includes(clean)) {
        return word.toUpperCase()
      }
    }
    return description.substring(0, 10).toUpperCase()
  }

  // Sync state when transaction changes
  useEffect(() => {
    if (transaction) {
      setCategory(transaction.category || '')
      setMerchant(transaction.merchant || '')
      setDescription(cleanDescription(transaction.description))
      setEditingDescription(false)
      setError(null)
      setSuccess(null)
      setShowCreateCategory(false)
      setNewCategoryName('')
      setLearnRule(false)
      setKeyword(extractKeyword(transaction.description))
      setApplyMerchantSimilar(false)
      setApplyCategorySimilar(false)
      setMerchantKeyword(extractKeyword(transaction.description))
      setCategoryKeyword(extractKeyword(transaction.description))
    }
  }, [transaction, isOpen])

  // Resolve the effective session_id: prefer the transaction's own session_id, fall back to prop
  const effectiveSessionId = transaction?.session_id || sessionId

  const handleApplyMerchantSimilar = async () => {
    if (!transaction) return

    const trimmedMerchant = (merchant || '').trim()
    const trimmedKeyword = (merchantKeyword || '').trim()

    if (!trimmedMerchant) {
      setError('Merchant is required to apply to similar transactions')
      return
    }

    if (trimmedKeyword.length < 3) {
      setError('Keyword must be at least 3 characters')
      return
    }

    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      await axios.put(
        `${API_BASE_URL}/transactions/${transaction.id}/merchant`,
        { merchant: trimmedMerchant || null },
        { params: { session_id: effectiveSessionId } }
      )

      // Use client_id to apply across all statements when available
      const bulkParams: any = clientId
        ? { client_id: clientId }
        : { session_id: effectiveSessionId }

      const response = await axios.post(
        `${API_BASE_URL}/bulk-merchant`,
        { keyword: trimmedKeyword, merchant: trimmedMerchant, only_unassigned: false },
        { params: bulkParams }
      )

      await axios.post(`${API_BASE_URL}/merchant-rules/learn`, {
        keyword: trimmedKeyword,
        merchant: trimmedMerchant,
        auto_apply: true,
        enabled: true,
      })

      const updated = response.data?.updated_count || 0
      setSuccess(`Applied merchant to ${updated} transaction(s)`)
      setTimeout(() => setSuccess(null), 2000)

      onSave?.({
        ...transaction,
        category,
        merchant: trimmedMerchant || null,
      })

      setApplyMerchantSimilar(false)
      onRefresh?.()
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to apply merchant to similar transactions'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleApplyCategorySimilar = async () => {
    if (!transaction) return

    const trimmedCategory = (category || '').trim()
    const trimmedKeyword = (categoryKeyword || '').trim()

    if (!trimmedCategory) {
      setError('Category is required to apply to similar transactions')
      return
    }

    if (trimmedKeyword.length < 3) {
      setError('Keyword must be at least 3 characters')
      return
    }

    setError(null)
    setLoading(true)

    try {
      // Use client_id to apply across all statements when available
      const bulkParams: any = clientId
        ? { client_id: clientId }
        : { session_id: effectiveSessionId }

      const response = await axios.post(
        `${API_BASE_URL}/bulk-categorise`,
        {
          keyword: trimmedKeyword,
          category: trimmedCategory,
          only_uncategorised: false
        },
        { params: bulkParams }
      )

      const updated = response.data?.updated_count || 0
      setSuccess(`Applied category to ${updated} transaction(s)`)
      setTimeout(() => setSuccess(null), 2000)

      onSave?.({
        ...transaction,
        category: trimmedCategory,
        merchant,
      })

      setApplyCategorySimilar(false)
      onRefresh?.()
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to apply category to similar transactions'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateCategory = async () => {
    setCreateError('')

    if (!newCategoryName.trim()) {
      setCreateError('Category name cannot be empty')
      return
    }

    if (newCategoryName.length < 2) {
      setCreateError('Category name must be at least 2 characters')
      return
    }

    if (newCategoryName.length > 50) {
      setCreateError('Category name must be 50 characters or less')
      return
    }

    try {
      setLoading(true)

      const response = await axios.post(
        `${API_BASE_URL}/categories`,
        { category_name: newCategoryName },
        { params: { session_id: effectiveSessionId, ...(clientId ? { client_id: clientId } : {}) } }
      )

      if (response.data.success) {
        onCategoryCreated?.(response.data.categories)
        setCategory(newCategoryName)
        setNewCategoryName('')
        setShowCreateCategory(false)
        setSuccess('Category created')
        setTimeout(() => setSuccess(null), 2000)
      }
    } catch (error: any) {
      console.error('Failed to create category:', error)
      const errorMessage = error.response?.data?.detail || 'Failed to create category'
      setCreateError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!transaction) {
      setError('No transaction selected')
      return
    }

    if (!transaction.id) {
      setError('Invalid transaction ID')
      return
    }

    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      const cleanedOriginalDesc = cleanDescription(transaction.description)

      const categoryChanged = category !== (transaction.category || '')
      const descriptionChanged = editingDescription && description !== cleanedOriginalDesc

      // Track API response data (includes recalculated VAT fields)
      let apiResponseData: any = null

      if (categoryChanged || descriptionChanged) {
        const requestBody: any = {}
        if (categoryChanged) {
          requestBody.category = category
        }
        if (descriptionChanged) {
          requestBody.description = description
        }

        const response = await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}`,
          requestBody,
          {
            params: {
              session_id: effectiveSessionId,
              learn_rule: learnRule,
              keyword: learnRule ? keyword : undefined
            }
          }
        )
        // The API response includes recalculated VAT fields
        apiResponseData = response.data
      }

      if (merchant !== (transaction.merchant || '')) {
        await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}/merchant`,
          { merchant: merchant || null },
          { params: { session_id: effectiveSessionId } }
        )
      }

      if (applyCategorySimilar && (category !== (transaction.category || ''))) {
        // Use client_id to apply across all statements when available
        const bulkParams: any = clientId
          ? { client_id: clientId }
          : { session_id: effectiveSessionId }

        await axios.post(
          `${API_BASE_URL}/bulk-categorise`,
          {
            keyword: categoryKeyword,
            category: category,
            only_uncategorised: false
          },
          { params: bulkParams }
        )
        setApplyCategorySimilar(false)
        onRefresh?.()
      }

      setSuccess('Changes saved')
      setTimeout(() => setSuccess(null), 2000)

      // Merge API response (with VAT fields) with existing transaction data
      const updatedTxn: Transaction = {
        ...transaction,
        category,
        merchant: merchant || null,
        description: editingDescription ? description : cleanDescription(transaction.description),
      }

      // If the API returned VAT data, include it in the update
      if (apiResponseData) {
        if (apiResponseData.vat_amount !== undefined) updatedTxn.vat_amount = apiResponseData.vat_amount
        if (apiResponseData.amount_excl_vat !== undefined) updatedTxn.amount_excl_vat = apiResponseData.amount_excl_vat
        if (apiResponseData.amount_incl_vat !== undefined) updatedTxn.amount_incl_vat = apiResponseData.amount_incl_vat
      }

      onSave?.(updatedTxn)
    } catch (err: any) {
      console.error('Failed to save transaction:', err)
      let errorMessage = err.response?.data?.detail || 'Failed to save changes'

      if (err.response?.status === 404) {
        if (errorMessage.includes('database may have been reset') || errorMessage.includes('No transactions found')) {
          errorMessage = 'Database was reset. Please reload the page to upload a new statement.'
        } else if (errorMessage.includes('session')) {
          errorMessage = 'Session mismatch. Please refresh the page to reload current transactions.'
        } else {
          errorMessage = 'Transaction not found. Please refresh the page to reload current transactions.'
        }
      }

      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !transaction) {
    return null
  }

  const hasChanges = category !== (transaction.category || '') || merchant !== (transaction.merchant || '')

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 z-40 flex h-full w-[420px] flex-col bg-white shadow-2xl ring-1 ring-neutral-200 animate-in slide-in-from-right">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2">
              <Pencil className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900">Edit Transaction</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Transaction Summary Card */}
          <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-4 space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400">
              Transaction Details
            </p>

            {/* Date */}
            <div>
              <span className="text-xs font-medium text-neutral-500">Date</span>
              <p className="text-sm font-medium text-neutral-900">
                {new Date(transaction.date).toLocaleDateString('en-ZA')}
              </p>
            </div>

            {/* Description */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-neutral-500">Description</span>
                <button
                  onClick={() => setEditingDescription(!editingDescription)}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {editingDescription ? 'Cancel' : 'Edit'}
                </button>
              </div>
              {editingDescription ? (
                <div className="space-y-2">
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                  />
                  <div className="flex items-start gap-2 rounded-lg bg-amber-50 ring-1 ring-amber-200 p-2.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-amber-800">
                      <span className="font-medium">Warning:</span> Editing may affect categorization rules and merchant matching. Changes apply only to this transaction.
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm break-words">
                  {description ? (
                    <span className="text-neutral-900">{description}</span>
                  ) : (
                    <span className="italic text-neutral-400">[No description provided]</span>
                  )}
                </p>
              )}
            </div>

            {/* Amount */}
            <div>
              <span className="text-xs font-medium text-neutral-500">Amount</span>
              <p
                className={`text-sm font-semibold ${
                  transaction.amount >= 0 ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                {transaction.amount >= 0 ? '+' : ''}R{Math.abs(transaction.amount).toLocaleString('en-ZA', {
                  minimumFractionDigits: 2,
                })}
              </p>
            </div>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="flex items-start gap-2.5 rounded-xl bg-red-50 ring-1 ring-red-200 px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="flex items-start gap-2.5 rounded-xl bg-emerald-50 ring-1 ring-emerald-200 px-4 py-3">
              <CheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-emerald-800">{success}</p>
            </div>
          )}

          {/* ─── Category Section ─── */}
          {!showCreateCategory ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-neutral-400" />
                <label className="text-sm font-semibold text-neutral-700">Category</label>
              </div>

              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
              >
                <option value="">(None)</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>

              <button
                onClick={() => setShowCreateCategory(true)}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Create New Category
              </button>

              {/* Learn Rule */}
              {category && category !== (transaction.category || '') && (
                <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-3 space-y-3">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={learnRule}
                      onChange={(e) => setLearnRule(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-neutral-900">
                        Apply to all matching transactions
                      </span>
                      <p className="text-xs text-neutral-500 mt-0.5">
                        Auto-categorize similar transactions in the future
                      </p>
                    </div>
                  </label>

                  {learnRule && (
                    <div className="ml-6.5 space-y-1.5">
                      <label className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400">
                        Keyword (min 3 chars)
                      </label>
                      <input
                        type="text"
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                        placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                        className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <p className="text-xs text-neutral-500">
                        Will match all transactions containing this keyword
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Apply Category to Similar */}
              <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-3 space-y-3">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={applyCategorySimilar}
                    onChange={(e) => setApplyCategorySimilar(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-neutral-900">
                      Apply category to similar transactions
                    </span>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      Update existing transactions with matching descriptions
                    </p>
                  </div>
                </label>

                {applyCategorySimilar && (
                  <div className="ml-6.5 space-y-2">
                    <label className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400">
                      Keyword (min 3 chars)
                    </label>
                    <input
                      type="text"
                      value={categoryKeyword}
                      onChange={(e) => setCategoryKeyword(e.target.value.toUpperCase())}
                      placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                      className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-neutral-500">
                      Will apply to all transactions containing this keyword
                    </p>
                    <button
                      onClick={handleApplyCategorySimilar}
                      disabled={loading || (category || '').trim().length === 0 || categoryKeyword.trim().length < 3}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Applying...
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Apply Category to Similar
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Create New Category */
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Plus className="w-4 h-4 text-neutral-400" />
                <label className="text-sm font-semibold text-neutral-700">New Category Name</label>
              </div>
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => {
                  setNewCategoryName(e.target.value)
                  setCreateError('')
                }}
                placeholder="e.g., Pet Care, Subscriptions"
                className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {createError && (
                <div className="flex items-start gap-2 text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{createError}</span>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={handleCreateCategory}
                  disabled={loading || !newCategoryName.trim()}
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowCreateCategory(false)
                    setNewCategoryName('')
                    setCreateError('')
                  }}
                  className="flex-1 rounded-lg px-4 py-2 text-sm font-medium text-neutral-700 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* ─── Merchant Section ─── */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Store className="w-4 h-4 text-neutral-400" />
              <label className="text-sm font-semibold text-neutral-700">Merchant</label>
            </div>
            <input
              type="text"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              placeholder="e.g., Shell, Spar, FNB"
              className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
            />
            <p className="text-xs text-neutral-500">Optional: Helps track spending by vendor</p>

            {/* Apply Merchant to Similar */}
            <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-3 space-y-3">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={applyMerchantSimilar}
                  onChange={(e) => setApplyMerchantSimilar(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-medium text-neutral-900">
                    Apply merchant to similar transactions
                  </span>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    Match by keyword and update learned rules
                  </p>
                </div>
              </label>

              {applyMerchantSimilar && (
                <div className="ml-6.5 space-y-2">
                  <label className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400">
                    Keyword (min 3 chars)
                  </label>
                  <input
                    type="text"
                    value={merchantKeyword}
                    onChange={(e) => setMerchantKeyword(e.target.value.toUpperCase())}
                    placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                    className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-neutral-500">
                    Will apply to all transactions containing this keyword
                  </p>
                  <button
                    onClick={handleApplyMerchantSimilar}
                    disabled={loading || (merchant || '').trim().length === 0 || merchantKeyword.trim().length < 3}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Apply Merchant to Similar
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* No Changes Hint */}
          {!hasChanges && (
            <div className="flex items-center gap-2.5 rounded-xl bg-neutral-50 ring-1 ring-neutral-200 px-4 py-3">
              <Sparkles className="w-4 h-4 text-neutral-400 flex-shrink-0" />
              <p className="text-sm text-neutral-500">No changes made</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex gap-3 border-t border-neutral-200 bg-neutral-50/60 px-6 py-4">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg px-4 py-2.5 text-sm font-medium text-neutral-700 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100"
          >
            Close
          </button>
          <button
            onClick={handleSave}
            disabled={loading || !hasChanges}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </>
  )
}
