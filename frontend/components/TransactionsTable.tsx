'use client'

import { useEffect, useState, type ReactNode, useRef } from 'react'
import { ChevronDown, FileText, X, Tag, Users, Trash2, Search, Settings, Check } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove, SortableContext, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import FilteredCategorizeModal from './FilteredCategorizeModal'
import BulkMerchantModal from './BulkMerchantModal'
import { LoadingSection } from './Spinner'
import InvoiceUploadModal from './InvoiceUploadModal'
import TransactionEditPanel from './TransactionEditPanel'
import { getAuthUser } from '@/lib/auth'
import { useClient } from '@/lib/clientContext'

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

interface TransactionsTableProps {
  sessionId: string | null
  onTransactionSelect?: (transaction: Transaction) => void
  categories: string[]
  refreshTrigger?: number
  highlightTxnId?: number | null
  selectedStatement?: string
  onStatementChange?: (statementId: string) => void
}

interface Transaction {
  id: number
  session_id?: string
  statement_name?: string
  date: string
  description: string
  amount: number
  category: string
  merchant?: string | null
  vat_amount?: number | null
  amount_excl_vat?: number | null
  amount_incl_vat?: number | null
}

const DEFAULT_COLUMN_ORDER = ['date', 'description', 'merchant', 'amount', 'vat_amount', 'amount_excl_vat', 'category', 'invoice', 'running_balance'] as const
type ColumnId = typeof DEFAULT_COLUMN_ORDER[number]

interface SortableHeaderCellProps {
  id: ColumnId
  onClick?: () => void
  className: string
  align?: 'left' | 'right'
  children: ReactNode
}

function SortableHeaderCell({ id, onClick, className, align = 'left', children }: SortableHeaderCellProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <th
      ref={setNodeRef}
      style={style}
      onClick={onClick}
      className={`${className} ${isDragging ? 'bg-blue-50' : ''}`}
    >
      <div className={`flex items-center gap-2 ${align === 'right' ? 'justify-end' : 'justify-start'}`}>
        <span
          className="cursor-grab text-neutral-400"
          onClick={(e) => e.stopPropagation()}
          {...attributes}
          {...listeners}
        >
          ⠿
        </span>
        <div className="flex items-center gap-2">
          {children}
        </div>
      </div>
    </th>
  )
}

export default function TransactionsTable({ sessionId, onTransactionSelect, categories, refreshTrigger, highlightTxnId, selectedStatement = '', onStatementChange }: TransactionsTableProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'date' | 'amount' | 'category' | 'description' | 'merchant'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [undoAvailable, setUndoAvailable] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [query, setQuery] = useState('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [dateError, setDateError] = useState<string | null>(null)
  const [showFilteredModal, setShowFilteredModal] = useState(false)
  const [filteredModalTransactions, setFilteredModalTransactions] = useState<Transaction[] | null>(null)
  const [editingTransaction, setEditingTransaction] = useState<any | null>(null)
  const [showBulkMerchantModal, setShowBulkMerchantModal] = useState(false)
  const [categoriesList, setCategoriesList] = useState<string[]>(categories || [])
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [editingMerchantId, setEditingMerchantId] = useState<number | null>(null)
  const [editingMerchantValue, setEditingMerchantValue] = useState<string>('')
  const [invoices, setInvoices] = useState<any[]>([])
  const [invoicesByAmount, setInvoicesByAmount] = useState<Record<number, any[]>>({})
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null)
  const [showInvoiceModal, setShowInvoiceModal] = useState(false)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [showInvoiceUploadModal, setShowInvoiceUploadModal] = useState(false)
  const [transactionForUpload, setTransactionForUpload] = useState<any | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [hasActiveFilters, setHasActiveFilters] = useState(false)
  const [selectedTransactionForEdit, setSelectedTransactionForEdit] = useState<Transaction | null>(null)
  const [showEditPanel, setShowEditPanel] = useState(false)
  const [showRunningBalance, setShowRunningBalance] = useState(false)
  const [openingBalance, setOpeningBalance] = useState<string>('0')
  const [showClearCategoriesModal, setShowClearCategoriesModal] = useState(false)
  const [clearingCategories, setClearingCategories] = useState(false)
  const [columnOrder, setColumnOrder] = useState<ColumnId[]>([...DEFAULT_COLUMN_ORDER])
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnId>>(new Set(DEFAULT_COLUMN_ORDER))
  const [showColumnPicker, setShowColumnPicker] = useState(false)
  const columnPickerRef = useRef<HTMLDivElement>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [searchTrigger, setSearchTrigger] = useState(0)
  const [txnFilter, setTxnFilter] = useState<string | null>(null)

  const authUser = getAuthUser()
  const userKey = authUser?.user_id ? String(authUser.user_id) : 'anonymous'
  const { currentClient } = useClient()
  const columnStorageKey = `txn_table_columns_${userKey}`
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const handleRefreshData = () => {
    setRefreshKey(prev => prev + 1)
  }

  const buildTransactionParams = () => {
    const params: any = { q: query, date_from: dateFrom || undefined, date_to: dateTo || undefined, _t: Date.now() }
    
    console.log('[buildTransactionParams] dateFrom:', dateFrom, 'dateTo:', dateTo)
    
    // Priority logic:
    // 1. If user selected a client in the UI (currentClient exists), use client_id
    // 2. Only fall back to sessionId if no currentClient is selected
    // This prevents stale sessionId from URL overriding user's client selection
    
    if (currentClient?.id) {
      params.client_id = currentClient.id
      // If a specific statement is selected, filter by that session_id
      if (selectedStatement) {
        params.session_id = selectedStatement
      }
      return params
    }
    
    if (sessionId) {
      params.session_id = sessionId
      return params
    }
    
    return null
  }

  const normalizeColumnOrder = (order: string[]): ColumnId[] => {
    const clean = order.filter((col) => (DEFAULT_COLUMN_ORDER as readonly string[]).includes(col)) as ColumnId[]
    const missing = DEFAULT_COLUMN_ORDER.filter((col) => !clean.includes(col))
    return [...clean, ...missing]
  }

  const columnVisibilityStorageKey = `txn_table_visible_columns_${userKey}`

  useEffect(() => {
    try {
      const raw = localStorage.getItem(columnStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          setColumnOrder(normalizeColumnOrder(parsed))
        }
      }
    } catch (e) {
      // ignore
    }
  }, [columnStorageKey])

  useEffect(() => {
    try {
      localStorage.setItem(columnStorageKey, JSON.stringify(columnOrder))
    } catch (e) {
      // ignore
    }
  }, [columnOrder, columnStorageKey])

  // Load visible columns from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(columnVisibilityStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          setVisibleColumns(new Set(parsed as ColumnId[]))
        }
      }
    } catch (e) {
      // ignore
    }
  }, [columnVisibilityStorageKey])

  // Save visible columns to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(columnVisibilityStorageKey, JSON.stringify(Array.from(visibleColumns)))
    } catch (e) {
      // ignore
    }
  }, [visibleColumns, columnVisibilityStorageKey])

  // Close column picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (columnPickerRef.current && !columnPickerRef.current.contains(event.target as Node)) {
        setShowColumnPicker(false)
      }
    }
    if (showColumnPicker) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showColumnPicker])

  // Update hasActiveFilters whenever filters change
  useEffect(() => {
    setHasActiveFilters(query !== '' || dateFrom !== '' || dateTo !== '' || selectedStatement !== '')
  }, [query, dateFrom, dateTo, selectedStatement])

  // Separate effect to read URL params on mount ONLY
  useEffect(() => {
    // Read optional filters from URL (e.g. ?txn_filter=expenses|income|uncategorized&date_from=2025-02-01&date_to=2025-02-28)
    try {
      const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null
      const tf = params?.get('txn_filter')
      if (tf) {
        console.log('[TransactionsTable] Setting txn_filter from URL:', tf)
        setTxnFilter(tf)
      }
      
      const df = params?.get('date_from')
      if (df) {
        console.log('[TransactionsTable] Setting date_from from URL:', df)
        setDateFrom(df)
        setShowFilters(true) // Auto-expand filters when date filter is present
      }
      
      const dt = params?.get('date_to')
      if (dt) {
        console.log('[TransactionsTable] Setting date_to from URL:', dt)
        setDateTo(dt)
        setShowFilters(true) // Auto-expand filters when date filter is present
      }
    } catch (e) {
      // ignore
    }
  }, []) // Empty dependency array - run only on mount

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Clear existing data when switching clients to ensure clean state
        setLoading(true)
        setTransactions([]) // Clear immediately when effect runs
        
        // Use client_id if current client is selected, otherwise use session_id for backward compatibility
        const params = buildTransactionParams()
        console.log('[TransactionsTable] Effect triggered. currentClient id:', currentClient?.id, 'name:', currentClient?.name, 'sessionId:', sessionId, 'selectedStatement:', selectedStatement)
        console.log('[TransactionsTable] Params to send:', JSON.stringify(params))
        
        if (!params) {
          console.log('[TransactionsTable] No params available (no client or session)')
          setTransactions([])
          setInvoices([])
          setInvoicesByAmount({})
          setLoading(false)
          return
        }

        console.log('[TransactionsTable] Fetching transactions from http://localhost:8000/transactions with:', JSON.stringify(params))
        const txnResponse = await axios.get(`${API_BASE_URL}/transactions`, { params })
        let txns = txnResponse.data.transactions || []
        console.log('[TransactionsTable] API Response - Fetched', txns.length, 'transactions. First transaction:', txns[0])

        // Apply client-side filter from URL if present
        if (txnFilter) {
          switch (txnFilter) {
            case 'expenses':
              txns = txns.filter((t: any) => Number(t.amount) < 0)
              break
            case 'income':
              txns = txns.filter((t: any) => Number(t.amount) > 0)
              break
            case 'uncategorized':
              txns = txns.filter((t: any) => !t.category || t.category === '')
              break
            default:
              // no-op for unknown filters
              break
          }
          console.log('[TransactionsTable] Applied txn_filter=', txnFilter, ' ->', txns.length, 'rows')
        }

        setTransactions(txns)

        // Fetch invoices - use same params as transactions to get client/session specific invoices
        const invoiceParams = currentClient?.id ? { client_id: currentClient.id } : (sessionId ? { session_id: sessionId } : {})
        console.log('[TransactionsTable] Fetching invoices with params:', JSON.stringify(invoiceParams))
        if (Object.keys(invoiceParams).length > 0) {
          const invResponse = await axios.get(`${API_BASE_URL}/invoices`, {
            params: invoiceParams,
          })
          const invs = invResponse.data.invoices || []
          console.log('[TransactionsTable] Fetched', invs.length, 'invoices')
          setInvoices(invs)

          // Build a map of amount -> invoices for quick lookup
          const byAmount: Record<number, any[]> = {}
          invs.forEach((inv: any) => {
            const amt = Math.round(inv.total_amount * 100) // Handle floating point
            if (!byAmount[amt]) byAmount[amt] = []
            byAmount[amt].push(inv)
          })
          setInvoicesByAmount(byAmount)
        } else {
          setInvoices([])
          setInvoicesByAmount({})
        }
      } catch (error) {
        console.error('[TransactionsTable] Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [sessionId, currentClient?.id, refreshTrigger, dateFrom, dateTo, currentClient, refreshKey, searchTrigger, selectedStatement, txnFilter])

  useEffect(() => {
    // If parent didn't pass categories, fetch them from API
    if ((!categoriesList || categoriesList.length === 0) && sessionId) {
      axios.get(`${API_BASE_URL}/categories`, { params: { session_id: sessionId } })
        .then(res => {
          // Extract just the names from the category objects
          const categoryNames = (res.data.categories || []).map((cat: any) => 
            typeof cat === 'string' ? cat : cat.name
          )
          setCategoriesList(categoryNames)
        })
        .catch(() => {})
    }
    // Keep in sync if parent passes categories later
    if (categories && categories.length > 0) {
      setCategoriesList(categories)
    }
  }, [sessionId])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // validate date range
    setDateError(null)
    if (dateFrom && dateTo) {
      const df = new Date(dateFrom)
      const dt = new Date(dateTo)
      if (df > dt) {
        setDateError('Start date must be on or before end date')
        return
      }
    }
    // Trigger search by updating searchTrigger
    setSearchTrigger(prev => prev + 1)
  }

  const handleCategorizeFiltered = () => {
    setShowFilteredModal(true)
  }

  const handleApplyToSimilar = (txn: Transaction) => {
    // Normalize description by removing common noisy tokens (POS Purchase, POS,
    // DebiCheck, etc.), strip punctuation and collapse whitespace. Use this
    // both to select a meaningful keyword and to match other transactions.
    const normalize = (s: string) => {
      if (!s) return ''
      return s
        .toLowerCase()
        .replace(/\b(pos\s*purchase|pos|debi\s*check|debicheck|debit\s*order|eft)\b/ig, ' ')
        .replace(/[^a-z0-9\s]/ig, ' ')
        .replace(/\s+/g, ' ')
        .trim()
    }

    const raw = txn.description || ''
    const cleaned = normalize(raw)
    const words = cleaned.split(/\s+/).filter(Boolean)
    let kw = words.find(w => w.length > 3) || words[0] || ''
    // fallback: if nothing meaningful in cleaned, use a short token from raw
    if (!kw) {
      const fallback = (raw || '').split(/\s+/).map(w => w.replace(/[^a-zA-Z0-9]/g, '')).find(Boolean)
      kw = fallback || ''
    }
    const kwLower = kw.toLowerCase()

    const matches = transactions.filter(t => {
      const td = normalize(t.description || '')
      return kwLower && td.includes(kwLower)
    })

    // Ensure the selected transaction itself is included in the matches
    if (!matches.some(m => m.id === txn.id)) matches.unshift(txn)

    setFilteredModalTransactions(matches)
    setShowFilteredModal(true)
  }

  const handleUndo = async () => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/bulk-categorise/undo`,
        {},
        {
          params: { session_id: sessionId },
        }
      )

      if (response.data.success) {
        const txns = response.data.transactions || []
        setTransactions(txns)
        setUndoAvailable(response.data.undo_available)
        setSuccessMessage('Categorization reverted')
        setTimeout(() => setSuccessMessage(''), 4000)
      }
    } catch (error) {
      console.error('Undo failed:', error)
    }
  }

  const handleSaveMerchant = async (txnId: number, newMerchant: string) => {
    setSavingId(txnId)
    try {
      await axios.put(
        `${API_BASE_URL}/transactions/${txnId}/merchant`,
        { merchant: newMerchant || null },
        { params: { session_id: sessionId } }
      )
      setTransactions(prev =>
        prev.map(t =>
          t.id === txnId ? { ...t, merchant: newMerchant || null } : t
        )
      )
      setEditingMerchantId(null)
      setSuccessMessage('Merchant saved')
      setTimeout(() => setSuccessMessage(''), 2000)
    } catch (error) {
      console.error('Failed to save merchant:', error)
      setSuccessMessage('Failed to save merchant')
      setTimeout(() => setSuccessMessage(''), 2000)
    } finally {
      setSavingId(null)
    }
  }

  const handleSaveCategory = async (txnId: number, newCategory: string) => {
    setSavingId(txnId)
    try {
      await axios.put(
        `${API_BASE_URL}/transactions/${txnId}`,
        { category: newCategory },
        { params: { session_id: sessionId } }
      )
      setTransactions(prev =>
        prev.map(t => (t.id === txnId ? { ...t, category: newCategory } : t))
      )
      setEditingCategoryId(null)
      setSuccessMessage('Category saved')
      setTimeout(() => setSuccessMessage(''), 2000)
    } catch (error) {
      console.error('Failed to save category:', error)
      setSuccessMessage('Failed to save category')
      setTimeout(() => setSuccessMessage(''), 2000)
    } finally {
      setSavingId(null)
    }
  }

  if (loading) {
    return <LoadingSection message="Loading transactions..." size="lg" />
  }

  const handleHeaderClick = (field: 'date' | 'amount' | 'category' | 'description' | 'merchant') => {
    if (sortBy === field) {
      // Toggle direction if clicking the same header
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // New field: default to ascending
      setSortBy(field)
      setSortDirection('asc')
    }
  }

  const getSortIndicator = (field: string) => {
    if (sortBy !== field) return '⇅' // Both directions (neutral)
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const handleDragEnd = (event: any) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    setColumnOrder((prev) => {
      const oldIndex = prev.indexOf(active.id as ColumnId)
      const newIndex = prev.indexOf(over.id as ColumnId)
      return arrayMove(prev, oldIndex, newIndex)
    })
  }

  const handleResetColumns = () => {
    setColumnOrder([...DEFAULT_COLUMN_ORDER])
    try {
      localStorage.removeItem(columnStorageKey)
    } catch (e) {
      // ignore
    }
  }

  const toggleColumnVisibility = (col: ColumnId) => {
    const newVisible = new Set(visibleColumns)
    if (newVisible.has(col)) {
      newVisible.delete(col)
    } else {
      newVisible.add(col)
    }
    setVisibleColumns(newVisible)
  }

  const getColumnLabel = (col: ColumnId): string => {
    const labels: Record<ColumnId, string> = {
      date: 'Date',
      description: 'Description',
      merchant: 'Merchant',
      amount: 'Amount',
      vat_amount: 'VAT Amount',
      amount_excl_vat: 'Amount Excl VAT',
      category: 'Category',
      invoice: 'Invoice',
      running_balance: 'Running Balance',
    }
    return labels[col] || col
  }

  const clearTxnFilter = () => {
    try {
      setTxnFilter(null)
      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search)
        params.delete('txn_filter')
        const newQs = params.toString()
        const newUrl = window.location.pathname + (newQs ? `?${newQs}` : '')
        window.history.replaceState({}, '', newUrl)
      }
      setSearchTrigger(prev => prev + 1)
    } catch (e) {
      // ignore
    }
  }

  const calculateRunningBalance = (txns: Transaction[]) => {
    const balanceMap = new Map<number, number>()
    let balance = parseFloat(openingBalance) || 0
    
    txns.forEach((txn) => {
      balance += txn.amount
      balanceMap.set(txn.id, balance)
    })
    
    return balanceMap
  }

  const sortedTransactions = [...transactions].sort((a, b) => {
    let compareValue = 0

    switch (sortBy) {
      case 'date':
        compareValue = new Date(a.date).getTime() - new Date(b.date).getTime()
        break
      case 'amount':
        compareValue = Math.abs(a.amount) - Math.abs(b.amount)
        break
      case 'category':
        compareValue = (a.category || '').localeCompare(b.category || '')
        break
      case 'description':
        compareValue = (a.description || '').localeCompare(b.description || '')
        break
      case 'merchant':
        compareValue = (a.merchant || '').localeCompare(b.merchant || '')
        break
      default:
        compareValue = 0
    }

    return sortDirection === 'asc' ? compareValue : -compareValue
  })

  return (
    <div className="card overflow-hidden">
      {/* Header with Title and Controls */}
      <div className="border-b border-neutral-200 bg-white">
        {/* Top Bar - Title and Primary Actions */}
        <div className="px-8 py-5 flex items-center justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-2xl font-semibold text-neutral-900">Transactions</h2>
            <p className="text-sm text-neutral-500 mt-1">{transactions.length} total</p>
          </div>
          
          {/* Primary Action Buttons - Right Side */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCategorizeFiltered}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-800 text-white font-medium rounded-lg hover:bg-neutral-700 active:bg-neutral-900 transition-colors"
              title="Categorize filtered transactions"
            >
              <Tag size={18} />
              Categorize
            </button>
            <button
              onClick={() => setShowBulkMerchantModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-700 text-white font-medium rounded-lg hover:bg-neutral-600 active:bg-neutral-800 transition-colors"
              title="Assign merchant to transactions"
            >
              <Users size={18} />
              Merchant
            </button>
            <button
              onClick={() => setShowClearCategoriesModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-100 text-neutral-700 border border-neutral-300 font-medium rounded-lg hover:bg-neutral-200 active:bg-neutral-150 transition-colors"
              title="Clear all transaction categories"
            >
              <Trash2 size={18} />
              Clear
            </button>
          </div>
        </div>

        {/* Control Bar - Filters, Sort, and Options */}
        <div className="px-8 py-3 bg-neutral-50 border-t border-neutral-200 flex items-center gap-4">
          {/* Filter Toggle Button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              hasActiveFilters
                ? 'bg-neutral-200 text-neutral-800 border border-neutral-400'
                : 'bg-white text-neutral-700 border border-neutral-200 hover:bg-neutral-100'
            }`}
            title={`${showFilters ? 'Hide' : 'Show'} filters`}
          >
            <Search size={16} />
            <span>Filters</span>
            <ChevronDown
              size={16}
              className={`transition-transform ${showFilters ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Divider */}
          <div className="h-5 w-px bg-neutral-300" />

          {/* Sort Dropdown */}
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm font-medium text-neutral-700">Sort by:</label>
            <select
              id="sort-select"
              name="sortBy"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="text-sm px-3 py-1.5 border border-neutral-200 rounded-md bg-white font-medium text-neutral-700 hover:border-neutral-300 focus:outline-none focus:ring-2 focus:ring-neutral-400"
            >
              <option value="date">Date</option>
              <option value="amount">Amount</option>
              <option value="category">Category</option>
              <option value="description">Description</option>
            </select>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* View Options */}
          {txnFilter && (
            <div className="inline-flex items-center gap-3 mr-2">
              <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm font-medium">
                Filter: {txnFilter}
              </div>
              <button onClick={clearTxnFilter} className="px-2 py-1.5 text-sm text-neutral-700 bg-white border border-neutral-200 rounded hover:bg-neutral-50">Clear</button>
            </div>
          )}
          <button
            onClick={handleRefreshData}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white border border-blue-600 rounded-md hover:bg-blue-700 transition-colors"
            title="Refresh transaction data from database"
          >
            ↻ Refresh
          </button>
          <button
            onClick={handleResetColumns}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-100 transition-colors"
            title="Reset column order to default"
          >
            ↺ Reset Columns
          </button>

          {/* Column Visibility Picker */}
          <div className="relative" ref={columnPickerRef}>
            <button
              onClick={() => setShowColumnPicker(!showColumnPicker)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-100 transition-colors"
              title="Show/hide columns"
            >
              <Settings size={16} />
              Columns
            </button>

            {/* Dropdown Menu */}
            {showColumnPicker && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-neutral-300 rounded-lg shadow-lg z-50">
                <div className="p-3 border-b border-neutral-200">
                  <p className="text-xs font-semibold text-neutral-700 uppercase tracking-wide">Visible Columns</p>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {DEFAULT_COLUMN_ORDER.map((col) => (
                    <label
                      key={col}
                      className="flex items-center gap-2 px-4 py-2.5 hover:bg-neutral-50 cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={visibleColumns.has(col)}
                        onChange={() => toggleColumnVisibility(col)}
                        className="w-4 h-4 rounded border-neutral-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-neutral-700">{getColumnLabel(col)}</span>
                      {visibleColumns.has(col) && (
                        <Check size={14} className="ml-auto text-blue-600" />
                      )}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {/* Collapsible Filter Panel */}
        {showFilters && (
          <div className="mb-3 p-4 bg-white border border-neutral-200 rounded-lg space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Search */}
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">Search</label>
                <input
                  type="text"
                  placeholder="Description..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full text-sm px-2 py-1.5 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Date From */}
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">From Date</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full text-sm px-2 py-1.5 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Date To */}
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">To Date</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full text-sm px-2 py-1.5 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Filter Buttons */}
              <div className="flex items-end gap-2">
                <button
                  onClick={handleSearch}
                  className="flex-1 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Apply
                </button>
                <button
                  onClick={() => {
                    setQuery('')
                    setDateFrom('')
                    setDateTo('')
                    setDateError(null)
                    setSearchTrigger(prev => prev + 1)  // Auto-apply cleared filters
                  }}
                  className="flex-1 px-3 py-1.5 text-sm font-medium bg-white text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Running Balance Section */}
            <div className="border-t border-neutral-200 pt-3">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showRunningBalance}
                    onChange={(e) => setShowRunningBalance(e.target.checked)}
                    className="w-4 h-4 border border-neutral-200 rounded cursor-pointer"
                  />
                  <span className="text-sm font-medium text-neutral-700">Show Running Balance</span>
                </label>
                
                {showRunningBalance && (
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-neutral-700">Opening Balance:</label>
                    <input
                      type="number"
                      step="0.01"
                      value={openingBalance}
                      onChange={(e) => setOpeningBalance(e.target.value)}
                      className="w-32 text-sm px-2 py-1.5 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Date Error Message */}
            {dateError && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                ⚠️ {dateError}
              </div>
            )}
          </div>
        )}

        {/* Success message + Undo button */}
        {(successMessage || undoAvailable) && (
          <div className="flex items-center justify-between text-sm bg-green-50 border border-green-200 rounded p-2">
            <div className="text-green-700 font-medium">{successMessage || 'Ready to undo'}</div>
            {undoAvailable && (
              <button
                onClick={handleUndo}
                className="text-sm font-medium text-green-700 hover:text-green-800 underline"
              >
                Undo
              </button>
            )}
          </div>
        )}
      </div>

      <FilteredCategorizeModal
        isOpen={showFilteredModal}
        onClose={() => { setShowFilteredModal(false); setFilteredModalTransactions(null) }}
        transactions={filteredModalTransactions || transactions}
        categories={categoriesList}
        sessionId={sessionId || ''}
        initialSelectAll={!!filteredModalTransactions}
        onApplied={(message, count) => {
          setSuccessMessage(message)
          setShowFilteredModal(false)
          setTimeout(() => setSuccessMessage(''), 4000)
          // Trigger refresh by refetching
          // Here we simply refetch current filtered list
          // (the modal already returned updated transactions in response, but we'll re-query)
          setLoading(true)
          const params = buildTransactionParams()
          if (!params) {
            setTransactions([])
            setLoading(false)
            return
          }
          axios.get(`${API_BASE_URL}/transactions`, { params })
            .then((res) => setTransactions(res.data.transactions || []))
            .catch((e) => console.error('Refetch failed', e))
            .finally(() => setLoading(false))
        }}
      />

      <BulkMerchantModal
        isOpen={showBulkMerchantModal}
        onClose={() => setShowBulkMerchantModal(false)}
        transactions={transactions}
        sessionId={sessionId || ''}
        onApplied={(message, count) => {
          setShowBulkMerchantModal(false)
          setSuccessMessage(message)
          setTimeout(() => setSuccessMessage(''), 4000)
          // refresh list
          setLoading(true)
          const params = buildTransactionParams()
          if (!params) {
            setTransactions([])
            setLoading(false)
            return
          }
          axios.get(`${API_BASE_URL}/transactions`, { params })
            .then((res) => setTransactions(res.data.transactions || []))
            .catch((e) => console.error('Refetch failed', e))
            .finally(() => setLoading(false))
        }}
      />

      {/* Clear Categories Confirmation Modal */}
      {showClearCategoriesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-red-200">
              <h2 className="text-lg font-semibold text-red-900">Clear All Categories?</h2>
              <button
                onClick={() => setShowClearCategoriesModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <p className="text-sm text-neutral-700">
                This will remove categories from <strong>all {transactions.length} transactions</strong> in this session.
              </p>
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                ⚠️ This action cannot be undone.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-neutral-200 bg-neutral-50">
              <button
                onClick={() => setShowClearCategoriesModal(false)}
                disabled={clearingCategories}
                className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-200 rounded-md hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setClearingCategories(true)
                  try {
                    await axios.post(
                      `${API_BASE_URL}/transactions/clear-categories`,
                      {},
                      { params: currentClient?.id ? { client_id: currentClient.id } : { session_id: sessionId } }
                    )
                    setShowClearCategoriesModal(false)
                    setSuccessMessage(`Cleared categories from ${transactions.length} transactions`)
                    setTimeout(() => setSuccessMessage(''), 4000)
                    // Refresh transactions
                    setLoading(true)
                    const params = buildTransactionParams()
                    if (!params) {
                      setTransactions([])
                      setLoading(false)
                      return
                    }
                    axios.get(`${API_BASE_URL}/transactions`, { params })
                      .then((res) => setTransactions(res.data.transactions || []))
                      .catch((e) => console.error('Refetch failed', e))
                      .finally(() => setLoading(false))
                  } catch (error: any) {
                    console.error('Failed to clear categories:', error)
                    if (axios.isAxiosError(error) && error.response?.data) {
                      console.error('Backend error details:', error.response.data)
                      setSuccessMessage(`Failed to clear categories: ${error.response.data.detail || 'Unknown error'}`)
                    } else {
                      setSuccessMessage('Failed to clear categories')
                    }
                    setTimeout(() => setSuccessMessage(''), 4000)
                  } finally {
                    setClearingCategories(false)
                  }
                }}
                disabled={clearingCategories}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {clearingCategories ? 'Clearing...' : 'Clear All Categories'}
              </button>
            </div>
          </div>
        </div>
      )}



      <div className="overflow-x-auto">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table className="w-full text-sm">
            <SortableContext items={columnOrder.filter((c) => visibleColumns.has(c) && (c !== 'running_balance' || showRunningBalance))} strategy={horizontalListSortingStrategy}>
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50">
                  {columnOrder.filter((c) => visibleColumns.has(c) && (c !== 'running_balance' || showRunningBalance)).map((col) => {
                    switch (col) {
                      case 'date':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            onClick={() => handleHeaderClick('date')}
                            className="text-left px-6 py-3 font-medium text-neutral-700 cursor-pointer hover:bg-neutral-100 transition-colors select-none"
                          >
                            Date
                            <span className={`text-xs ${sortBy === 'date' ? 'text-blue-600 font-bold' : 'text-neutral-400'}`}>
                              {getSortIndicator('date')}
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'description':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            onClick={() => handleHeaderClick('description')}
                            className="text-left px-6 py-3 font-medium text-neutral-700 cursor-pointer hover:bg-neutral-100 transition-colors select-none"
                          >
                            Description
                            <span className={`text-xs ${sortBy === 'description' ? 'text-blue-600 font-bold' : 'text-neutral-400'}`}>
                              {getSortIndicator('description')}
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'merchant':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            onClick={() => handleHeaderClick('merchant')}
                            className="text-left px-6 py-3 font-medium text-neutral-700 cursor-pointer hover:bg-neutral-100 transition-colors select-none"
                          >
                            Merchant
                            <span className={`text-xs ${sortBy === 'merchant' ? 'text-blue-600 font-bold' : 'text-neutral-400'}`}>
                              {getSortIndicator('merchant')}
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'amount':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            onClick={() => handleHeaderClick('amount')}
                            className="text-right px-6 py-3 font-medium text-neutral-700 cursor-pointer hover:bg-neutral-100 transition-colors select-none"
                            align="right"
                          >
                            Amount
                            <span className={`text-xs ${sortBy === 'amount' ? 'text-blue-600 font-bold' : 'text-neutral-400'}`}>
                              {getSortIndicator('amount')}
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'vat_amount':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            className="text-right px-6 py-3 font-medium text-neutral-700"
                            align="right"
                          >
                            <span className="flex items-center gap-1">
                              VAT
                              <span className="text-xs text-neutral-500">(15%)</span>
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'amount_excl_vat':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            className="text-right px-6 py-3 font-medium text-neutral-700"
                            align="right"
                          >
                            Excl. VAT
                          </SortableHeaderCell>
                        )
                      case 'category':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            onClick={() => handleHeaderClick('category')}
                            className="text-left px-6 py-3 font-medium text-neutral-700 cursor-pointer hover:bg-neutral-100 transition-colors select-none"
                          >
                            Category
                            <span className={`text-xs ${sortBy === 'category' ? 'text-blue-600 font-bold' : 'text-neutral-400'}`}>
                              {getSortIndicator('category')}
                            </span>
                          </SortableHeaderCell>
                        )
                      case 'invoice':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            className="text-left px-6 py-3 font-medium text-neutral-700"
                          >
                            Invoice
                          </SortableHeaderCell>
                        )
                      case 'running_balance':
                        return (
                          <SortableHeaderCell
                            key={col}
                            id={col}
                            className="text-right px-6 py-3 font-medium text-neutral-700"
                            align="right"
                          >
                            Running Balance
                          </SortableHeaderCell>
                        )
                      default:
                        return null
                    }
                  })}
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const balanceMap = calculateRunningBalance(sortedTransactions)
                  return sortedTransactions.map((txn) => (
                    <tr
                      key={txn.id}
                      onClick={() => onTransactionSelect?.(txn)}
                      className={`border-b border-neutral-100 cursor-pointer transition-colors ${
                        highlightTxnId === txn.id 
                          ? 'bg-yellow-100 hover:bg-yellow-150' 
                          : 'hover:bg-blue-50'
                      }`}
                    >
                      {columnOrder.filter((c) => visibleColumns.has(c) && (c !== 'running_balance' || showRunningBalance)).map((col) => {
                        switch (col) {
                          case 'date':
                            return (
                              <td key={`${txn.id}-${col}`} className="px-6 py-3 text-neutral-600">
                                {new Date(txn.date).toLocaleDateString('en-ZA')}
                              </td>
                            )
                          case 'description':
                            const displayDesc = cleanDescription(txn.description)
                            return (
                              <td 
                                key={`${txn.id}-${col}`} 
                                className="px-6 py-3 text-neutral-900 max-w-xs"
                              >
                                <div className="flex flex-col gap-1">
                                  <div
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setSelectedTransactionForEdit(txn)
                                      setShowEditPanel(true)
                                    }}
                                    className="cursor-pointer hover:text-blue-600 hover:underline whitespace-normal break-words"
                                    title="Click to edit transaction details"
                                  >
                                    {displayDesc ? (
                                      displayDesc
                                    ) : (
                                      <span className="text-neutral-400 italic">[No description provided]</span>
                                    )}
                                  </div>
                                  {/* Show statement badge when viewing all statements (not filtered by statement) */}
                                  {!selectedStatement && txn.statement_name && txn.statement_name !== 'Unknown Statement' && (
                                    <span className="text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded inline-block self-start">
                                      📄 {txn.statement_name}
                                    </span>
                                  )}
                                </div>
                              </td>
                            )
                          case 'merchant':
                            return (
                              <td key={`${txn.id}-${col}`} className="px-6 py-3 text-neutral-700 max-w-xs truncate">
                                <div
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setSelectedTransactionForEdit(txn)
                                    setShowEditPanel(true)
                                  }}
                                  className="group flex items-center justify-between px-2 py-1 rounded hover:bg-blue-50 cursor-pointer"
                                >
                                  <span className="text-sm text-neutral-700">
                                    {txn.merchant || <span className="text-neutral-400 italic">Add merchant</span>}
                                  </span>
                                  <span className="text-xs text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                    ✎
                                  </span>
                                </div>
                              </td>
                            )
                          case 'amount':
                            return (
                              <td key={`${txn.id}-${col}`} className={`text-right px-6 py-3 font-medium ${
                                txn.amount >= 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {txn.amount >= 0 ? '+' : ''}R{Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                              </td>
                            )
                          case 'vat_amount':
                            return (
                              <td key={`${txn.id}-${col}`} className="text-right px-6 py-3 text-purple-600 text-sm">
                                {txn.vat_amount != null ? (
                                  `R${Math.abs(txn.vat_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}`
                                ) : (
                                  <span className="text-neutral-300">-</span>
                                )}
                              </td>
                            )
                          case 'amount_excl_vat':
                            return (
                              <td key={`${txn.id}-${col}`} className="text-right px-6 py-3 text-neutral-600 text-sm">
                                {txn.amount_excl_vat != null ? (
                                  `R${Math.abs(txn.amount_excl_vat).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}`
                                ) : (
                                  <span className="text-neutral-300">-</span>
                                )}
                              </td>
                            )
                          case 'category':
                            return (
                              <td key={`${txn.id}-${col}`} className="px-6 py-3">
                                <div
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setSelectedTransactionForEdit(txn)
                                    setShowEditPanel(true)
                                  }}
                                  className="group flex items-center justify-between px-2 py-1 rounded bg-neutral-100 hover:bg-blue-100 cursor-pointer transition-colors"
                                >
                                  <span className="text-xs font-medium text-neutral-700">
                                    {txn.category || <span className="text-neutral-400 italic">Add category</span>}
                                  </span>
                                  <span className="text-xs text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                    ✎
                                  </span>
                                </div>
                              </td>
                            )
                          case 'invoice':
                            return (
                              <td key={`${txn.id}-${col}`} className="px-6 py-3">
                                {(() => {
                                  const amt = Math.round(Math.abs(txn.amount) * 100)
                                  const matchingInvoices = invoicesByAmount[amt] || []
                                  return matchingInvoices.length > 0 ? (
                                    <button
                                      className="flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium hover:bg-blue-100 transition-colors"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setSelectedInvoice(matchingInvoices[0])
                                        setShowInvoiceModal(true)
                                      }}
                                    >
                                      <FileText size={14} />
                                      {matchingInvoices.length}
                                    </button>
                                  ) : (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setTransactionForUpload({
                                          id: txn.id,
                                          date: txn.date,
                                          description: txn.description,
                                          amount: txn.amount,
                                        })
                                        setShowInvoiceUploadModal(true)
                                      }}
                                      className="px-3 py-1 bg-neutral-100 text-neutral-600 rounded text-xs font-medium hover:bg-neutral-200 transition-colors"
                                      title="Click to upload invoice"
                                    >
                                      + Upload Invoice
                                    </button>
                                  )
                                })()}
                              </td>
                            )
                          case 'running_balance':
                            return (
                              <td key={`${txn.id}-${col}`} className="text-right px-6 py-3 font-medium text-neutral-700">
                                {(() => {
                                  const balance = balanceMap.get(txn.id)
                                  const isNegative = balance !== undefined && balance < 0
                                  return (
                                    <span className={isNegative ? 'text-red-600' : 'text-green-600'}>
                                      R{balance !== undefined ? Math.abs(balance).toLocaleString('en-ZA', { minimumFractionDigits: 2 }) : '0.00'}
                                    </span>
                                  )
                                })()}
                              </td>
                            )
                          default:
                            return null
                        }
                      })}
                    </tr>
                  ))
                })()}
              </tbody>
            </SortableContext>
          </table>
        </DndContext>
      </div>

      {transactions.length === 0 && (
        <div className="px-6 py-8 text-center text-neutral-600">
          No transactions found
        </div>
      )}

      {/* Invoice Detail Modal */}
      {showInvoiceModal && selectedInvoice && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-96 overflow-auto">
            <div className="sticky top-0 flex items-center justify-between p-6 border-b bg-white">
              <h2 className="text-lg font-semibold">Invoice Details</h2>
              <button
                onClick={() => setShowInvoiceModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700">Supplier</label>
                <p className="mt-1 text-neutral-900">{selectedInvoice.supplier_name}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700">Invoice Date</label>
                  <p className="mt-1 text-neutral-900">
                    {new Date(selectedInvoice.invoice_date).toLocaleDateString('en-ZA')}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700">Invoice Number</label>
                  <p className="mt-1 text-neutral-900">{selectedInvoice.invoice_number || 'N/A'}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700">Total Amount</label>
                  <p className="mt-1 text-neutral-900 font-medium">
                    R{selectedInvoice.total_amount.toFixed(2)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700">VAT Amount</label>
                  <p className="mt-1 text-neutral-900">
                    R{(selectedInvoice.vat_amount || 0).toFixed(2)}
                  </p>
                </div>
              </div>

              {selectedInvoice.file_reference && (
                <div>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const response = await axios.get(`${API_BASE_URL}/invoice/download`, {
                          params: { session_id: sessionId, invoice_id: selectedInvoice.id },
                          responseType: 'blob'
                        })
                        const url = window.URL.createObjectURL(new Blob([response.data]))
                        const link = document.createElement('a')
                        link.href = url
                        link.download = `invoice_${selectedInvoice.id}.pdf`
                        document.body.appendChild(link)
                        link.click()
                        link.remove()
                        window.URL.revokeObjectURL(url)
                      } catch (error) {
                        console.error('Failed to download invoice:', error)
                      }
                    }}
                    className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Download PDF
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <InvoiceUploadModal
        isOpen={showInvoiceUploadModal}
        onClose={() => {
          setShowInvoiceUploadModal(false)
          setTransactionForUpload(null)
        }}
        transaction={transactionForUpload}
        sessionId={sessionId || ''}
        onUploadSuccess={(message, invoice) => {
          setSuccessMessage(message)
          setShowInvoiceUploadModal(false)
          setTransactionForUpload(null)
          setTimeout(() => setSuccessMessage(''), 3000)
          
          // Immediately update local state with the new invoice
          if (invoice && transactionForUpload) {
            // Add invoice to invoices list
            setInvoices(prev => [...prev, invoice])
            
            // Update invoicesByAmount map
            const amt = Math.round(Math.abs(transactionForUpload.amount) * 100)
            setInvoicesByAmount(prev => ({
              ...prev,
              [amt]: [...(prev[amt] || []), invoice]
            }))
          }
        }}
      />

      {/* Transaction Edit Panel (Side Sheet) */}
      <TransactionEditPanel
        isOpen={showEditPanel}
        transaction={selectedTransactionForEdit}
        sessionId={sessionId || ''}
        categories={categoriesList}
        onClose={() => {
          setShowEditPanel(false)
          setSelectedTransactionForEdit(null)
        }}
        onSave={(updatedTransaction) => {
          // Update transaction in local state
          setTransactions(prev =>
            prev.map(t =>
              t.id === updatedTransaction.id ? updatedTransaction : t
            )
          )
          setSuccessMessage('Transaction updated')
          setTimeout(() => setSuccessMessage(''), 2000)
        }}
        onCategoryCreated={(newCategories) => {
          setCategoriesList(newCategories)
        }}
        onRefresh={() => {
          // Trigger refresh
          setRefreshKey(prev => prev + 1)
        }}
      />
    </div>
  )
}
