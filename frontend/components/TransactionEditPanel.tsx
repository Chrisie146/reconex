'use client'

import { X } from 'lucide-react'
import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'
import LoadingButton from './LoadingButton'

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
  date: string
  description: string
  amount: number
  category: string
  merchant?: string | null
}

interface TransactionEditPanelProps {
  isOpen: boolean
  transaction: Transaction | null
  sessionId: string
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
      setLearnRule(false) // Reset checkbox when transaction changes
      setKeyword(extractKeyword(transaction.description))
      setApplyMerchantSimilar(false)
      setApplyCategorySimilar(false)
      setMerchantKeyword(extractKeyword(transaction.description))
      setCategoryKeyword(extractKeyword(transaction.description))
    }
  }, [transaction, isOpen])

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
      // Ensure the current transaction merchant is saved
      await axios.put(
        `${API_BASE_URL}/transactions/${transaction.id}/merchant`,
        { merchant: trimmedMerchant || null },
        { params: { session_id: sessionId } }
      )

      // Apply merchant to matching transactions in this session
      const response = await axios.post(
        `${API_BASE_URL}/bulk-merchant`,
        { keyword: trimmedKeyword, merchant: trimmedMerchant, only_unassigned: false },
        { params: { session_id: sessionId } }
      )

      // Update learned rules (auto-apply on future uploads)
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

    setError(null)
    setLoading(true)

    try {
      // Find similar transactions based on keyword
      const response = await axios.post(
        `${API_BASE_URL}/bulk-categorise`,
        {
          keyword: trimmedKeyword,
          category: trimmedCategory,
          only_uncategorised: false // Allow overwriting existing categories for similar transactions
        },
        { params: { session_id: sessionId } }
      )

      const updated = response.data?.updated_count || 0
      setSuccess(`Applied category to ${updated} transaction(s)`)
      setTimeout(() => setSuccess(null), 2000)

      onSave?.({
        ...transaction,
        category: trimmedCategory,
        merchant,
      })
      
      setApplyCategorySimilar(false) // Reset after applying
      onRefresh?.() // Refresh the transaction list
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
      console.log('Creating category:', { newCategoryName, sessionId })
      
      const response = await axios.post(
        `${API_BASE_URL}/categories`,
        { category_name: newCategoryName },
        { params: { session_id: sessionId } }
      )

      console.log('Category created successfully:', response.data)
      
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
      
      // Save category and/or description
      const categoryChanged = category !== (transaction.category || '')
      const descriptionChanged = editingDescription && description !== cleanedOriginalDesc
      
      if (categoryChanged || descriptionChanged) {
        const requestBody: any = {}
        if (categoryChanged) {
          requestBody.category = category
        }
        if (descriptionChanged) {
          requestBody.description = description
        }
        
        await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}`,
          requestBody,
          { params: { 
            session_id: sessionId, 
            learn_rule: learnRule,
            keyword: learnRule ? keyword : undefined
          } }
        )
      }

      // Save merchant
      if (merchant !== (transaction.merchant || '')) {
        await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}/merchant`,
          { merchant: merchant || null },
          { params: { session_id: sessionId } }
        )
      }

      // Apply category to similar transactions if requested
      if (applyCategorySimilar && categoryChanged) {
        await axios.post(
          `${API_BASE_URL}/bulk-categorise`,
          {
            keyword: categoryKeyword,
            category: category,
            only_uncategorised: false
          },
          { params: { session_id: sessionId } }
        )
        setApplyCategorySimilar(false) // Reset after applying
        onRefresh?.() // Refresh the transaction list
      }

      setSuccess('Changes saved')
      setTimeout(() => setSuccess(null), 2000)

      // Notify parent
      onSave?.({
        ...transaction,
        category,
        merchant: merchant || null,
        description: editingDescription ? description : cleanDescription(transaction.description),
      })
    } catch (err: any) {
      console.error('Failed to save transaction:', err)
      let errorMessage = err.response?.data?.detail || 'Failed to save changes'
      
      // Provide helpful message for 404 errors
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
        className="fixed inset-0 bg-black bg-opacity-30 z-30 transition-opacity"
        onClick={onClose}
      />

      {/* Side Panel */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-40 overflow-y-auto animate-in slide-in-from-right">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-neutral-200 px-6 py-4 flex items-center justify-between">
          <h2 className="font-bold text-lg text-neutral-900">Edit Transaction</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 rounded transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Transaction Summary */}
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 space-y-2">
            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase">Date</label>
              <p className="text-sm font-medium text-neutral-900">
                {new Date(transaction.date).toLocaleDateString('en-ZA')}
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-500 uppercase">Description</label>
                <button
                  onClick={() => setEditingDescription(!editingDescription)}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  {editingDescription ? 'Cancel' : 'Edit'}
                </button>
              </div>
              {editingDescription ? (
                <div className="space-y-2">
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full text-sm text-neutral-900 border border-neutral-300 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                  />
                  <div className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded">
                    <svg className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <p className="text-xs text-amber-800">
                      <strong>Warning:</strong> Editing the description may affect categorization rules and merchant matching. Changes apply only to this transaction.
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm break-words">
                  {description ? (
                    <span className="text-neutral-900">{description}</span>
                  ) : (
                    <span className="text-neutral-400 italic">[No description provided]</span>
                  )}
                </p>
              )}
            </div>
            <div>
              <label className="text-xs font-semibold text-neutral-500 uppercase">Amount</label>
              <p
                className={`text-sm font-semibold ${
                  transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {transaction.amount >= 0 ? '+' : ''}R{Math.abs(transaction.amount).toLocaleString('en-ZA', {
                  minimumFractionDigits: 2,
                })}
              </p>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
              ⚠️ {error}
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-700">
              ✓ {success}
            </div>
          )}

          {/* Category Selection */}
          {!showCreateCategory ? (
            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                + Create New Category
              </button>
              
              {/* Learn Rule Checkbox */}
              {category && category !== (transaction.category || '') && (
                <div className="mt-3 pt-3 border-t border-neutral-200">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={learnRule}
                      onChange={(e) => setLearnRule(e.target.checked)}
                      className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-sm font-medium text-neutral-900">
                        Apply to all matching transactions
                      </div>
                      <div className="text-xs text-neutral-500 mt-0.5">
                        Automatically categorize similar transactions in the future
                      </div>
                    </div>
                  </label>
                  
                  {/* Keyword Input (shown when checkbox is checked) */}
                  {learnRule && (
                    <div className="mt-3 ml-6">
                      <label className="block text-xs font-semibold text-neutral-700 mb-1">
                        Keyword (min 3 chars)
                      </label>
                      <input
                        type="text"
                        value={keyword}
                        onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                        placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                        className="w-full px-3 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <div className="text-xs text-neutral-500 mt-1">
                        Will match all transactions containing this keyword
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Apply Category to Similar */}
              <div className="mt-3 pt-3 border-t border-neutral-200">
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={applyCategorySimilar}
                    onChange={(e) => setApplyCategorySimilar(e.target.checked)}
                    className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-neutral-900">
                      Apply category to similar transactions
                    </div>
                    <div className="text-xs text-neutral-500 mt-0.5">
                      Update existing transactions with matching descriptions
                    </div>
                  </div>
                </label>

                {applyCategorySimilar && (
                  <div className="mt-3 ml-6">
                    <label className="block text-xs font-semibold text-neutral-700 mb-1">
                      Keyword (min 3 chars)
                    </label>
                    <input
                      type="text"
                      value={categoryKeyword}
                      onChange={(e) => setCategoryKeyword(e.target.value.toUpperCase())}
                      placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                      className="w-full px-3 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <div className="text-xs text-neutral-500 mt-1">
                      Will apply to all transactions containing this keyword
                    </div>
                    <LoadingButton
                      onClick={handleApplyCategorySimilar}
                      loading={loading}
                      loadingText="Applying..."
                      variant="primary"
                      disabled={loading || (category || '').trim().length === 0 || categoryKeyword.trim().length < 3}
                      className="w-full mt-2"
                    >
                      Apply Category to Similar
                    </LoadingButton>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">New Category Name</label>
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => {
                  setNewCategoryName(e.target.value)
                  setCreateError('')
                }}
                placeholder="e.g., Pet Care, Subscriptions"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
              />
              {createError && (
                <p className="text-sm text-red-600 mb-2">⚠️ {createError}</p>
              )}
              <div className="flex gap-2">
                <LoadingButton
                  onClick={handleCreateCategory}
                  loading={loading}
                  loadingText="Creating..."
                  variant="primary"
                  disabled={loading || !newCategoryName.trim()}
                  className="flex-1 text-sm"
                >
                  Create
                </LoadingButton>
                <button
                  onClick={() => {
                    setShowCreateCategory(false)
                    setNewCategoryName('')
                    setCreateError('')
                  }}
                  className="flex-1 px-3 py-2 bg-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-300 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Merchant Input */}
          <div>
            <label className="block text-sm font-semibold text-neutral-700 mb-2">Merchant</label>
            <input
              type="text"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              placeholder="e.g., Shell, Spar, FNB"
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-neutral-500 mt-1">Optional: Helps track spending by vendor</p>

            <div className="mt-3 pt-3 border-t border-neutral-200">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={applyMerchantSimilar}
                  onChange={(e) => setApplyMerchantSimilar(e.target.checked)}
                  className="mt-0.5 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div>
                  <div className="text-sm font-medium text-neutral-900">
                    Apply merchant to similar transactions
                  </div>
                  <div className="text-xs text-neutral-500 mt-0.5">
                    Match by keyword and update learned rules
                  </div>
                </div>
              </label>

              {applyMerchantSimilar && (
                <div className="mt-3 ml-6">
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Keyword (min 3 chars)
                  </label>
                  <input
                    type="text"
                    value={merchantKeyword}
                    onChange={(e) => setMerchantKeyword(e.target.value.toUpperCase())}
                    placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                    className="w-full px-3 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="text-xs text-neutral-500 mt-1">
                    Will apply to all transactions containing this keyword
                  </div>
                  <LoadingButton
                    onClick={handleApplyMerchantSimilar}
                    loading={loading}
                    loadingText="Applying..."
                    variant="primary"
                    disabled={loading || (merchant || '').trim().length === 0 || merchantKeyword.trim().length < 3}
                    className="w-full"
                  >
                    Apply Merchant to Similar
                  </LoadingButton>
                </div>
              )}
            </div>
          </div>

          {/* Current Values */}
          {!hasChanges && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-700">
              No changes made
            </div>
          )}
        </div>

        {/* Footer / Action Buttons */}
        <div className="sticky bottom-0 border-t border-neutral-200 bg-white px-6 py-4 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 font-medium transition-colors"
          >
            Close
          </button>
          <LoadingButton
            onClick={handleSave}
            loading={loading}
            loadingText="Saving..."
            variant="primary"
            disabled={loading || !hasChanges}
            className="w-full"
          >
            Save Changes
          </LoadingButton>
        </div>
      </div>
    </>
  )
}
