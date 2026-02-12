'use client'

import { useState } from 'react'
import axios from '@/lib/axiosClient'
import LoadingButton from './LoadingButton'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface BulkCategoryModalProps {
  isOpen: boolean
  onClose: () => void
  selectedTransaction: {
    id: number
    description: string
    category: string
  } | null
  sessionId: string
  categories: string[]
  onSuccess: (message: string, updatedCount: number) => void
  onCategoryCreated?: (newCategories: string[]) => void
}

export default function BulkCategoryModal({
  isOpen,
  onClose,
  selectedTransaction,
  sessionId,
  categories,
  onSuccess,
  onCategoryCreated,
}: BulkCategoryModalProps) {
  const [selectedCategory, setSelectedCategory] = useState('')
  const [applyBulk, setApplyBulk] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmMode, setConfirmMode] = useState(false)
  const [showCreateCategory, setShowCreateCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [createError, setCreateError] = useState('')

  if (!isOpen || !selectedTransaction) {
    return null
  }

  const extractKeyword = (description: string): string => {
    const words = description.split(/\s+/)
    const commonWords = ['the', 'a', 'an', 'deposit', 'payment', 'transfer']
    for (const word of words) {
      const clean = word.toLowerCase().replace(/[^a-z0-9]/g, '')
      if (clean.length >= 3 && !commonWords.includes(clean)) {
        return clean.toUpperCase()
      }
    }
    return description.substring(0, 10).toUpperCase()
  }

  const handleApplyBulkToggle = () => {
    if (!applyBulk) {
      const extracted = extractKeyword(selectedTransaction.description)
      setKeyword(extracted)
      setApplyBulk(true)
    } else {
      setApplyBulk(false)
      setKeyword('')
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

    if (newCategoryName.length > 30) {
      setCreateError('Category name must be 30 characters or less')
      return
    }

    try {
      setLoading(true)
      const response = await axios.post(
        `${API_BASE_URL}/categories`,
        { category_name: newCategoryName },
        { params: { session_id: sessionId } }
      )

      if (response.data.success) {
        onCategoryCreated?.(response.data.categories)
        setSelectedCategory(newCategoryName)
        setNewCategoryName('')
        setShowCreateCategory(false)
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to create category'
      setCreateError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleBulkApply = async () => {
    if (!selectedCategory) {
      alert('Please select a category')
      return
    }

    if (applyBulk && !keyword) {
      alert('Please enter a keyword')
      return
    }

    if (applyBulk && !confirmMode) {
      setConfirmMode(true)
      return
    }

    setLoading(true)
    try {
      if (applyBulk) {
        const response = await axios.post(
          `${API_BASE_URL}/bulk-categorise`,
          {
            keyword: keyword,
            category: selectedCategory,
            only_uncategorised: false,
          },
          {
            params: { session_id: sessionId },
          }
        )

        const { updated_count, message } = response.data
        onSuccess(message, updated_count)
      } else {
        // Update single transaction category
        const response = await axios.put(
          `${API_BASE_URL}/transactions/${selectedTransaction.id}`,
          { category: selectedCategory },
          {
            params: { session_id: sessionId },
          }
        )

        onSuccess(`Updated category to "${selectedCategory}"`, 1)
      }

      setSelectedCategory('')
      setApplyBulk(false)
      setKeyword('')
      setConfirmMode(false)
      onClose()
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to apply category'
      alert(`Error: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg max-w-md w-full max-h-96 overflow-y-auto">
          {!confirmMode ? (
            <>
              <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50 sticky top-0">
                <h2 className="font-bold text-neutral-900">Update Category</h2>
              </div>

              <div className="px-6 py-4 space-y-4">
                {!showCreateCategory ? (
                  <>
                    <div className="bg-neutral-50 p-3 rounded border border-neutral-200">
                      <div className="text-sm text-neutral-600">Transaction:</div>
                      <div className="text-sm font-medium text-neutral-900 truncate">
                        {selectedTransaction.description}
                      </div>
                      <div className="text-xs text-neutral-500 mt-1">
                        Current: {selectedTransaction.category || 'Uncategorized'}
                      </div>
                    </div>

                    <div>
                      <label htmlFor="category-select" className="block text-sm font-medium text-neutral-700 mb-2">
                        New Category
                      </label>
                      <select
                        id="category-select"
                        name="category"
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-800"
                      >
                        <option value="">Select category...</option>
                        {categories.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={() => {
                        setShowCreateCategory(true)
                        setCreateError('')
                      }}
                      className="w-full text-center py-2 text-sm text-neutral-600 border-t border-neutral-200 hover:text-neutral-900 hover:bg-neutral-50"
                    >
                      + Create New Category
                    </button>

                    <div className="border-t border-neutral-200 pt-4">
                      <label htmlFor="apply-bulk-checkbox" className="flex items-start gap-3 cursor-pointer">
                        <input
                          id="apply-bulk-checkbox"
                          name="applyBulk"
                          type="checkbox"
                          checked={applyBulk}
                          onChange={handleApplyBulkToggle}
                          className="mt-1"
                        />
                        <div className="text-sm">
                          <div className="font-medium text-neutral-900">
                            Apply to all matching transactions
                          </div>
                          <div className="text-neutral-600">
                            Automatically categorize similar transactions
                          </div>
                        </div>
                      </label>
                    </div>

                    {applyBulk && (
                      <div>
                        <label htmlFor="keyword-input" className="block text-sm font-medium text-neutral-700 mb-2">
                          Keyword (min 3 chars)
                        </label>
                        <input
                          id="keyword-input"
                          name="keyword"
                          type="text"
                          value={keyword}
                          onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                          placeholder="e.g., ENGEN"
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-800"
                          maxLength={20}
                        />
                        <div className="text-xs text-neutral-500 mt-1">
                          Will match all transactions containing this keyword
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div>
                      <h3 className="font-medium text-neutral-900 mb-3">Create New Category</h3>
                      <input
                        id="new-category-input"
                        name="newCategory"
                        type="text"
                        value={newCategoryName}
                        onChange={(e) => {
                          setNewCategoryName(e.target.value)
                          setCreateError('')
                        }}
                        placeholder="e.g., Software & Tools"
                        maxLength={30}
                        className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-800 mb-2"
                        autoFocus
                      />
                      <div className="text-xs text-neutral-500">
                        Name must be 2-30 characters
                      </div>

                      {createError && (
                        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2 mt-2">
                          {createError}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>

              <div className="px-6 py-4 border-t border-neutral-200 bg-neutral-50 sticky bottom-0 flex gap-3">
                {!showCreateCategory ? (
                  <>
                    <button
                      onClick={onClose}
                      disabled={loading}
                      className="flex-1 px-4 py-2 text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <LoadingButton
                      onClick={handleBulkApply}
                      loading={loading}
                      loadingText="Processing..."
                      variant="primary"
                      disabled={loading || !selectedCategory}
                      className="flex-1"
                    >
                      Apply
                    </LoadingButton>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setShowCreateCategory(false)
                        setNewCategoryName('')
                        setCreateError('')
                      }}
                      disabled={loading}
                      className="flex-1 px-4 py-2 text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 disabled:opacity-50"
                    >
                      Back
                    </button>
                    <LoadingButton
                      onClick={handleCreateCategory}
                      loading={loading}
                      loadingText="Creating..."
                      variant="primary"
                      disabled={loading || !newCategoryName.trim()}
                      className="flex-1"
                    >
                      Create
                    </LoadingButton>
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50">
                <h2 className="font-bold text-neutral-900">Confirm Bulk Categorization</h2>
              </div>

              <div className="px-6 py-6 space-y-4">
                <div className="bg-neutral-50 p-4 rounded border border-neutral-200 text-sm">
                  <div className="space-y-2 text-neutral-700">
                    <div>
                      <span className="font-medium">Keyword:</span> {keyword}
                    </div>
                    <div>
                      <span className="font-medium">Category:</span> {selectedCategory}
                    </div>
                    <div>
                      <span className="font-medium">Match type:</span> Contains (case-insensitive)
                    </div>
                  </div>
                </div>

                <div className="text-sm text-neutral-600 p-3 bg-amber-50 border border-amber-200 rounded">
                  ⚠ This action can be undone with the Undo button
                </div>
              </div>

              <div className="px-6 py-4 border-t border-neutral-200 bg-neutral-50 flex gap-3">
                <button
                  onClick={() => setConfirmMode(false)}
                  disabled={loading}
                  className="flex-1 px-4 py-2 text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 disabled:opacity-50"
                >
                  Back
                </button>
                <LoadingButton
                  onClick={handleBulkApply}
                  loading={loading}
                  loadingText="Processing..."
                  variant="primary"
                  disabled={loading}
                  className="flex-1"
                >
                  Confirm & Apply
                </LoadingButton>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
