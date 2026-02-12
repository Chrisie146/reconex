'use client'

import { useEffect, useState } from 'react'
import { X, FileSpreadsheet, AlertCircle } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CategoriesExportModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
}

interface Category {
  name: string
  transaction_count: number
}

export default function CategoriesExportModal({
  isOpen,
  onClose,
  sessionId
}: CategoriesExportModalProps) {
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [useFullPeriod, setUseFullPeriod] = useState<boolean>(true)
  const [includeVAT, setIncludeVAT] = useState<boolean>(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  
  // Transaction date range from session
  const [sessionDateFrom, setSessionDateFrom] = useState<string | null>(null)
  const [sessionDateTo, setSessionDateTo] = useState<string | null>(null)
  
  // Categories
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [loadingCategories, setLoadingCategories] = useState(false)

  useEffect(() => {
    if (!isOpen || !sessionId) return

    const fetchSessionInfo = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/sessions`)
        const sessions = response.data.sessions || []
        const currentSession = sessions.find((s: any) => s.session_id === sessionId)
        
        if (currentSession) {
          setSessionDateFrom(currentSession.date_from)
          setSessionDateTo(currentSession.date_to)
          setDateFrom(currentSession.date_from || '')
          setDateTo(currentSession.date_to || '')
        }
      } catch (error) {
        console.error('Failed to fetch session info:', error)
      }
    }

    const fetchCategories = async () => {
      setLoadingCategories(true)
      try {
        const response = await axios.get(`${API_BASE_URL}/categories`, {
          params: { session_id: sessionId }
        })
        // API returns { categories: [...] }
        const cats: Category[] = Array.isArray(response.data?.categories) 
          ? response.data.categories 
          : []
        setCategories(cats)
        // Select all by default
        setSelectedCategories(cats.map(c => c.name))
      } catch (error) {
        console.error('Failed to fetch categories:', error)
        setCategories([])
        setSelectedCategories([])
      } finally {
        setLoadingCategories(false)
      }
    }

    fetchSessionInfo()
    fetchCategories()
  }, [isOpen, sessionId])

  useEffect(() => {
    // Reset to full period when checkbox is toggled
    if (useFullPeriod && sessionDateFrom && sessionDateTo) {
      setDateFrom(sessionDateFrom)
      setDateTo(sessionDateTo)
      setWarning(null)
    }
  }, [useFullPeriod, sessionDateFrom, sessionDateTo])

  useEffect(() => {
    // Validate date range when dates change
    if (!dateFrom || !dateTo || !sessionDateFrom || !sessionDateTo) {
      setWarning(null)
      return
    }

    const fromDate = new Date(dateFrom)
    const toDate = new Date(dateTo)
    const sessionFromDate = new Date(sessionDateFrom)
    const sessionToDate = new Date(sessionDateTo)

    if (fromDate < sessionFromDate || toDate > sessionToDate) {
      const actualFrom = fromDate < sessionFromDate ? sessionDateFrom : dateFrom
      const actualTo = toDate > sessionToDate ? sessionDateTo : dateTo
      setWarning(
        `Selected range extends beyond transaction dates. Export will include data from ${actualFrom} to ${actualTo}.`
      )
    } else {
      setWarning(null)
    }
  }, [dateFrom, dateTo, sessionDateFrom, sessionDateTo])

  const handleCategoryToggle = (categoryName: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryName)) {
        return prev.filter(c => c !== categoryName)
      } else {
        return [...prev, categoryName]
      }
    })
  }

  const handleSelectAll = () => {
    if (Array.isArray(categories)) {
      setSelectedCategories(categories.map(c => c.name))
    }
  }

  const handleDeselectAll = () => {
    setSelectedCategories([])
  }

  const handleExport = async () => {
    if (!sessionId) return
    
    if (selectedCategories.length === 0) {
      setError('Please select at least one category to export.')
      return
    }

    setExporting(true)
    setError(null)

    try {
      const params: any = {
        session_id: sessionId,
        include_vat: includeVAT
      }

      console.log('[EXPORT DEBUG] Export params:', {
        session_id: sessionId,
        include_vat: includeVAT,
        includeVAT_type: typeof includeVAT,
        dateFrom,
        dateTo,
        useFullPeriod,
        totalCategories: categories.length,
        selectedCategories: selectedCategories,
        selectedCount: selectedCategories.length
      })

      // Add date range if not using full period
      if (!useFullPeriod && dateFrom && dateTo) {
        params.date_from = dateFrom
        params.date_to = dateTo
      }

      // Add selected categories
      if (Array.isArray(categories) && selectedCategories.length < categories.length) {
        params.categories = selectedCategories.join(',')
        console.log('[EXPORT DEBUG] Sending filtered categories:', params.categories)
      } else {
        console.log('[EXPORT DEBUG] Sending ALL categories (no filter)')
      }

      console.log('[EXPORT DEBUG] Final request params:', params)

      const response = await axios.get(`${API_BASE_URL}/export/categories`, {
        params,
        responseType: 'blob',
      })

      // Generate filename
      const dateRangeStr = dateFrom && dateTo ? `${dateFrom}_to_${dateTo}` : sessionId.substring(0, 8)
      const vatStr = includeVAT ? '_with_vat' : ''
      const filename = `categories${vatStr}_${dateRangeStr}.xlsx`

      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      onClose()
    } catch (error: any) {
      console.error('Categories export failed:', error)
      setError(error.response?.data?.detail || 'Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            <h2 className="text-xl font-bold text-neutral-900">Export Categories Report</h2>
            {includeVAT && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded">
                VAT ENABLED
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-neutral-600" />
          </button>
        </div>

        {/* Content - Scrollable */}
        <div className="px-6 py-4 space-y-5 overflow-y-auto flex-1">
          {/* Date Range Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">📅</span>
              <h3 className="font-semibold text-neutral-900">Date Range</h3>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useFullPeriod}
                onChange={(e) => setUseFullPeriod(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-neutral-700">Use full statement period</span>
            </label>

            {!useFullPeriod && (
              <div className="grid grid-cols-2 gap-3 pl-6">
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {warning && (
              <div className="flex gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <AlertCircle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-yellow-800">{warning}</p>
              </div>
            )}
          </div>

          {/* Categories Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">📁</span>
                <h3 className="font-semibold text-neutral-900">Select Categories</h3>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSelectAll}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  Select All
                </button>
                <span className="text-xs text-neutral-400">|</span>
                <button
                  onClick={handleDeselectAll}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  Deselect All
                </button>
              </div>
            </div>

            {loadingCategories ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-neutral-200 rounded-md p-3">
                {!Array.isArray(categories) || categories.length === 0 ? (
                  <div className="col-span-2 text-center py-4 text-sm text-neutral-500">
                    No categories found
                  </div>
                ) : (
                  categories.map((cat, index) => (
                    <label
                      key={`${cat.name}-${index}`}
                      className="flex items-center gap-2 p-2 hover:bg-neutral-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(cat.name)}
                        onChange={() => handleCategoryToggle(cat.name)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm text-neutral-700 flex-1 truncate">
                        {cat.name}
                      </span>
                      <span className="text-xs text-neutral-500">
                        ({cat.transaction_count})
                      </span>
                    </label>
                  ))
                )}
              </div>
            )}

            <div className="text-xs text-neutral-600">
              {selectedCategories.length} of {Array.isArray(categories) ? categories.length : 0} categories selected
            </div>
          </div>

          {/* VAT Columns Option */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">📊</span>
              <h3 className="font-semibold text-neutral-900">Display Options</h3>
            </div>

            <label className={`flex items-start gap-3 cursor-pointer p-3 rounded-md transition-colors border-2 ${
              includeVAT 
                ? 'bg-blue-50 border-blue-500 hover:bg-blue-100' 
                : 'border-neutral-200 hover:bg-neutral-50'
            }`}>
              <input
                type="checkbox"
                checked={includeVAT}
                onChange={(e) => {
                  const newValue = e.target.checked
                  setIncludeVAT(newValue)
                  console.log('[VAT CHECKBOX] Changed to:', newValue)
                }}
                className="w-4 h-4 text-blue-600 mt-0.5 rounded focus:ring-2 focus:ring-blue-500"
              />
              <div>
                <div className="text-sm font-medium text-neutral-900">
                  Include VAT columns {includeVAT && <span className="text-blue-600">✓ ENABLED</span>}
                </div>
                <div className="text-xs text-neutral-600">
                  Adds VAT Amount, Amount (Incl VAT), and Amount (Excl VAT) columns
                </div>
              </div>
            </label>
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={exporting}
            className="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={exporting || !dateFrom || !dateTo || selectedCategories.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {exporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <FileSpreadsheet className="w-4 h-4" />
                Export Report
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
