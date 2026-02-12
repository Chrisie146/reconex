"use client"

import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import { Search, Plus, Trash2, Tag } from 'lucide-react'

interface CategoriesManagerProps {
  sessionId: string
}

interface Category {
  name: string
  is_built_in: boolean
  vat_applicable: boolean
  vat_rate: number
}

export default function CategoriesManager({ sessionId }: CategoriesManagerProps) {
  const [categories, setCategories] = useState<Category[]>([])
  const [filteredCategories, setFilteredCategories] = useState<Category[]>([])
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

  useEffect(() => {
    loadCategories()
    loadVATConfig()
  }, [sessionId])

  useEffect(() => {
    // Filter categories based on search query
    if (searchQuery.trim() === '') {
      setFilteredCategories(categories)
    } else {
      const query = searchQuery.toLowerCase()
      setFilteredCategories(
        categories.filter(cat => 
          cat.name.toLowerCase().includes(query)
        )
      )
    }
  }, [searchQuery, categories])

  const loadCategories = async () => {
    try {
      const response = await apiFetch(`/categories/with-vat?session_id=${sessionId}`)
      if (!response.ok) throw new Error('Failed to load categories')
      const data = await response.json()
      setCategories(data.categories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load categories')
    }
  }

  const loadVATConfig = async () => {
    try {
      const response = await apiFetch(`/vat/config?session_id=${sessionId}`)
      if (!response.ok) throw new Error('Failed to load VAT config')
      const data = await response.json()
      setVatEnabled(data.vat_enabled || false)
    } catch (err) {
      console.error('Failed to load VAT config:', err)
    }
  }

  const handleToggleVAT = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiFetch(`/vat/config?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vat_enabled: !vatEnabled,
          default_vat_rate: 15.0
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to update VAT')
      }

      const data = await response.json()
      setVatEnabled(!vatEnabled)
      setSuccess(data.message)
      
      // Reload categories to refresh VAT calculations
      await loadCategories()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle VAT')
    } finally {
      setLoading(false)
    }
  }

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!newCategoryName.trim()) {
      setError('Please enter a category name')
      return
    }

    setLoading(true)
    try {
      // Create category
      const response = await apiFetch(`/categories?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_name: newCategoryName })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to create category')
      }

      // Update VAT settings for the new category
      const vatResponse = await apiFetch(`/categories/${encodeURIComponent(newCategoryName)}/vat`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vat_applicable: newCategoryVAT,
          vat_rate: newCategoryRate
        })
      })

      if (!vatResponse.ok) {
        console.error('Failed to set VAT settings for new category')
      }

      // Reload categories
      await loadCategories()
      
      setNewCategoryName('')
      setNewCategoryVAT(false)
      setNewCategoryRate(15.0)
      setSuccess('Category created successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateCategoryVAT = async (categoryName: string, vatApplicable: boolean, vatRate: number) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiFetch(`/categories/${encodeURIComponent(categoryName)}/vat`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vat_applicable: vatApplicable,
          vat_rate: vatRate
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to update VAT settings')
      }

      // Recalculate VAT for all transactions after updating category settings
      if (vatEnabled) {
        await recalculateVAT()
      }

      await loadCategories()
      setSuccess(`VAT settings updated for ${categoryName}. Transactions recalculated.`)
      setTimeout(() => setSuccess(null), 3000)
      setEditingRate(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update VAT settings')
      setTimeout(() => setError(null), 5000)
    } finally {
      setLoading(false)
    }
  }

  const recalculateVAT = async () => {
    try {
      const response = await apiFetch(`/vat/recalculate?session_id=${sessionId}`, {
        method: 'POST'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to recalculate VAT')
      }

      const data = await response.json()
      return data
    } catch (err) {
      console.error('VAT recalculation failed:', err)
      throw err
    }
  }

  const handleManualRecalculate = async () => {
    if (!vatEnabled) {
      setError('VAT must be enabled to recalculate')
      setTimeout(() => setError(null), 5000)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await recalculateVAT()
      setSuccess(`VAT recalculated successfully. ${data.stats?.total_recalculated || 0} transactions updated.`)
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to recalculate VAT')
      setTimeout(() => setError(null), 5000)
    } finally {
      setLoading(false)
    }
  }

  const handleRateEdit = (categoryName: string, currentRate: number) => {
    setEditingRate(categoryName)
    setTempRate(currentRate)
  }

  const handleRateSave = async (categoryName: string, vatApplicable: boolean) => {
    if (tempRate >= 0 && tempRate <= 100) {
      await handleUpdateCategoryVAT(categoryName, vatApplicable, tempRate)
    }
  }

  const handleRateCancel = () => {
    setEditingRate(null)
    setTempRate(0)
  }

  const handleDeleteCategory = async (categoryName: string) => {
    if (!confirm(`Delete category "${categoryName}"? This cannot be undone.`)) return

    setError(null)
    setLoading(true)

    try {
      // Remove from local state (backend delete endpoint to be implemented)
      setCategories(cats => cats.filter(c => c.name !== categoryName))
      setSuccess(`Category "${categoryName}" deleted`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete category')
      setTimeout(() => setError(null), 5000)
    } finally {
      setLoading(false)
    }
  }

  const sortedCategories = [...filteredCategories].sort((a, b) => {
    // Sort: built-in first, then custom, alphabetically within each group
    if (a.is_built_in && !b.is_built_in) return -1
    if (!a.is_built_in && b.is_built_in) return 1
    return a.name.localeCompare(b.name)
  })

  return (
    <div className="space-y-6">
      {/* Header with VAT Toggle */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Categories & VAT Settings</h1>
            <p className="text-sm text-gray-600">
              Manage transaction categories and configure VAT rates (South African 15% standard)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">VAT Calculation:</span>
            <button
              onClick={handleToggleVAT}
              disabled={loading}
              className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors ${
                vatEnabled ? 'bg-green-600' : 'bg-gray-300'
              } disabled:opacity-50`}
            >
              <span
                className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                  vatEnabled ? 'translate-x-9' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${vatEnabled ? 'text-green-700' : 'text-gray-500'}`}>
              {vatEnabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
        {vatEnabled && (
          <div className="flex items-center justify-between pt-4 border-t border-purple-200">
            <p className="text-sm text-gray-700">
              💡 Changed VAT settings? Click here to recalculate all transactions
            </p>
            <button
              onClick={handleManualRecalculate}
              disabled={loading}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 font-medium transition-colors flex items-center gap-2"
            >
              <span>🔄</span>
              {loading ? 'Recalculating...' : 'Recalculate VAT'}
            </button>
          </div>
        )}
      </div>

      {/* Status Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-red-600 text-xl">⚠️</span>
          <div className="flex-1 text-red-700 text-sm">{error}</div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-green-600 text-xl">✓</span>
          <div className="flex-1 text-green-700 text-sm">{success}</div>
          <button onClick={() => setSuccess(null)} className="text-green-400 hover:text-green-600">✕</button>
        </div>
      )}

      {/* Add New Category Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Plus className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-bold text-gray-900">Add New Category</h2>
        </div>
        <form onSubmit={handleAddCategory} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="lg:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Category Name</label>
              <input
                type="text"
                value={newCategoryName}
                onChange={e => setNewCategoryName(e.target.value)}
                placeholder="e.g., Pet Care, Subscriptions"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">VAT Rate (%)</label>
              <input
                type="number"
                value={newCategoryRate}
                onChange={e => setNewCategoryRate(parseFloat(e.target.value))}
                min="0"
                max="100"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                disabled={loading || !newCategoryVAT}
              />
            </div>
            <div className="flex flex-col justify-end">
              <label className="flex items-center gap-2 mb-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={newCategoryVAT}
                  onChange={e => setNewCategoryVAT(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">VAT Applicable</span>
              </label>
              <button
                type="submit"
                disabled={loading || !newCategoryName.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-medium transition-colors"
              >
                {loading ? 'Adding...' : 'Add Category'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Search and Category Count */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search categories..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div className="text-sm text-gray-600">
          <span className="font-medium">{filteredCategories.length}</span> of <span className="font-medium">{categories.length}</span> categories
        </div>
      </div>

      {/* Categories Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Category Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  VAT Applicable
                </th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  VAT Rate (%)
                </th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedCategories.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    {searchQuery ? 'No categories match your search' : 'No categories found'}
                  </td>
                </tr>
              ) : (
                sortedCategories.map(cat => (
                  <tr
                    key={cat.name}
                    className={`hover:bg-gray-50 transition-colors ${
                      cat.is_built_in ? 'bg-blue-50/30' : ''
                    }`}
                  >
                    {/* Category Name */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Tag className={`w-4 h-4 ${cat.is_built_in ? 'text-blue-600' : 'text-purple-600'}`} />
                        <span className="font-medium text-gray-900">{cat.name}</span>
                      </div>
                    </td>

                    {/* Type Badge */}
                    <td className="px-6 py-4">
                      {cat.is_built_in ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Built-in
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          Custom
                        </span>
                      )}
                    </td>

                    {/* VAT Applicable Checkbox */}
                    <td className="px-6 py-4 text-center">
                      <input
                        type="checkbox"
                        checked={cat.vat_applicable}
                        onChange={e => handleUpdateCategoryVAT(cat.name, e.target.checked, cat.vat_rate)}
                        disabled={loading}
                        className="w-5 h-5 text-green-600 rounded focus:ring-2 focus:ring-green-500 cursor-pointer disabled:opacity-50"
                      />
                    </td>

                    {/* VAT Rate */}
                    <td className="px-6 py-4 text-center">
                      {cat.vat_applicable ? (
                        editingRate === cat.name ? (
                          <div className="flex items-center justify-center gap-2">
                            <input
                              type="number"
                              value={tempRate}
                              onChange={e => setTempRate(parseFloat(e.target.value))}
                              onKeyDown={e => {
                                if (e.key === 'Enter') handleRateSave(cat.name, cat.vat_applicable)
                                if (e.key === 'Escape') handleRateCancel()
                              }}
                              min="0"
                              max="100"
                              step="0.1"
                              className="w-20 px-2 py-1 border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 outline-none text-center"
                              autoFocus
                            />
                            <button
                              onClick={() => handleRateSave(cat.name, cat.vat_applicable)}
                              className="text-green-600 hover:text-green-700 font-bold"
                              title="Save"
                            >
                              ✓
                            </button>
                            <button
                              onClick={handleRateCancel}
                              className="text-red-600 hover:text-red-700 font-bold"
                              title="Cancel"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleRateEdit(cat.name, cat.vat_rate)}
                            className="text-gray-900 hover:text-blue-600 font-medium underline decoration-dotted"
                            disabled={loading}
                          >
                            {cat.vat_rate}%
                          </button>
                        )
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-center">
                      {cat.is_built_in ? (
                        <span className="text-xs text-gray-400">Protected</span>
                      ) : (
                        <button
                          onClick={() => handleDeleteCategory(cat.name)}
                          disabled={loading}
                          className="inline-flex items-center gap-1 px-3 py-1 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                          title="Delete category"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
            <span className="text-lg">ℹ️</span>
            Built-in Categories
          </h3>
          <p className="text-blue-800 text-sm">
            Built-in categories have default VAT settings based on South African tax regulations. 
            You can modify their VAT settings but cannot delete them.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
            <span className="text-lg">🌐</span>
            Multilingual Support
          </h3>
          <p className="text-green-800 text-sm">
            Categories support English and Afrikaans keywords. Add keywords in either language 
            and the system will match them accurately.
          </p>
        </div>
      </div>
    </div>
  )
}
