'use client'

import { useEffect, useState, useMemo, type ReactNode, useRef } from 'react'
import { AlertTriangle, ChevronDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, FileText, Pencil, X, Trash2, Search, Check, ArrowUpDown, ArrowUp, ArrowDown, RefreshCw, RotateCcw, CheckSquare, Square, MinusSquare, Calculator, PanelRightOpen } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { isAxiosError } from 'axios'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove, SortableContext, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import BulkEditModal from './BulkEditModal'
import { LoadingSection } from './Spinner'
import InvoiceUploadModal from './InvoiceUploadModal'
import TransactionEditPanel from './TransactionEditPanel'
import { getAuthUser } from '@/lib/auth'
import { useClient } from '@/lib/clientContext'

import { API_BASE_URL } from '@/lib/apiBase'
const PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const
const DEFAULT_PAGE_SIZE = 50

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
  suggested_category?: string | null
  invoice_id?: number | null
  merchant?: string | null
  vat_amount?: number | null
  amount_excl_vat?: number | null
  amount_incl_vat?: number | null
  account_id?: number | null
  account_code?: string | null
  account_name?: string | null
  account_type?: string | null
  suggested_account_id?: number | null
  suggested_account_code?: string | null
  suggested_account_name?: string | null
  suggested_account_type?: string | null
  mapping_confidence?: number | null
  mapping_source?: string | null
  mapping_reason?: string | null
}

type QuickFilter = 'all' | 'income' | 'expenses' | 'uncategorized'

const DEFAULT_COLUMN_ORDER = ['date', 'description', 'merchant', 'amount', 'vat_amount', 'amount_excl_vat', 'account', 'category', 'invoice', 'running_balance'] as const
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
      className={`${className} ${isDragging ? 'bg-blue-50 shadow-lg z-10' : ''}`}
    >
      <div className={`flex items-center gap-1.5 ${align === 'right' ? 'justify-end' : 'justify-start'}`}>
        <span
          className="cursor-grab text-neutral-300 hover:text-neutral-500 transition-colors text-xs"
          onClick={(e) => e.stopPropagation()}
          {...attributes}
          {...listeners}
        >
          ⠿
        </span>
        <div className="flex items-center gap-1.5">
          {children}
        </div>
      </div>
    </th>
  )
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])
  return debouncedValue
}

export default function TransactionsTable({ sessionId, onTransactionSelect, categories, refreshTrigger, highlightTxnId, selectedStatement = '', onStatementChange }: TransactionsTableProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'date' | 'amount' | 'account' | 'category' | 'description' | 'merchant'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [undoAvailable, setUndoAvailable] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [query, setQuery] = useState('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [dateError, setDateError] = useState<string | null>(null)
  const [filteredModalTransactions, setFilteredModalTransactions] = useState<Transaction[] | null>(null)
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
  const [categoriesList, setCategoriesList] = useState<string[]>(categories || [])
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null)
  const [selectedCategoryValue, setSelectedCategoryValue] = useState<string>('')
  const [editingMerchantId, setEditingMerchantId] = useState<number | null>(null)
  const [editingMerchantValue, setEditingMerchantValue] = useState<string>('')
  const [invoicesById, setInvoicesById] = useState<Record<number, any>>({})
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null)
  const [selectedInvoiceTxnId, setSelectedInvoiceTxnId] = useState<number | null>(null)
  const [showInvoiceModal, setShowInvoiceModal] = useState(false)
  const [deletingInvoice, setDeletingInvoice] = useState(false)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [showInvoiceUploadModal, setShowInvoiceUploadModal] = useState(false)
  const [transactionForUpload, setTransactionForUpload] = useState<any | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [hasActiveFilters, setHasActiveFilters] = useState(false)
  const [selectedTransactionForEdit, setSelectedTransactionForEdit] = useState<Transaction | null>(null)
  const [showEditPanel, setShowEditPanel] = useState(false)
  const [showRunningBalance, setShowRunningBalance] = useState(false)
  const [openingBalance, setOpeningBalance] = useState<string>('0')
  const [recalculatingVAT, setRecalculatingVAT] = useState(false)
  const [vatEnabled, setVatEnabled] = useState(false)
  const [showClearCategoriesModal, setShowClearCategoriesModal] = useState(false)
  const [clearingCategories, setClearingCategories] = useState(false)
  const [columnOrder, setColumnOrder] = useState<ColumnId[]>([...DEFAULT_COLUMN_ORDER])
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnId>>(new Set(DEFAULT_COLUMN_ORDER))
  const [showColumnPicker, setShowColumnPicker] = useState(false)
  const columnPickerRef = useRef<HTMLDivElement>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [searchTrigger, setSearchTrigger] = useState(0)
  const [txnFilter, setTxnFilter] = useState<string | null>(null)

  // New UX state
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [focusedTxnId, setFocusedTxnId] = useState<number | null>(null)
  const [instantQuery, setInstantQuery] = useState('')
  const debouncedInstantQuery = useDebounce(instantQuery, 300)

  const authUser = getAuthUser()
  const userKey = authUser?.user_id ? String(authUser.user_id) : 'anonymous'
  const { currentClient } = useClient()
  const columnStorageKey = `txn_table_columns_${userKey}`
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))
  const tableContainerRef = useRef<HTMLDivElement>(null)

  const handleRefreshData = () => {
    setRefreshKey(prev => prev + 1)
  }

  useEffect(() => {
    const effectiveSessionId = sessionId || selectedStatement || null
    if (!effectiveSessionId) { setVatEnabled(false); return }
    axios.get(`${API_BASE_URL}/vat/config`, { params: { session_id: effectiveSessionId } })
      .then(res => setVatEnabled(res.data?.vat_enabled === true))
      .catch(() => setVatEnabled(false))
  }, [sessionId, selectedStatement])

  const handleRecalculateVAT = async () => {
    if (!currentClient?.id) return
    setRecalculatingVAT(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/vat/recalculate`, null, {
        params: { client_id: currentClient.id }
      })
      const data = response.data
      setSuccessMessage(`VAT recalculated: ${data.stats?.updated || 0} transactions updated`)
      setTimeout(() => setSuccessMessage(''), 4000)
      await refetchTransactions()
    } catch (error) {
      console.error('Failed to recalculate VAT:', error)
      setSuccessMessage('Failed to recalculate VAT')
      setTimeout(() => setSuccessMessage(''), 4000)
    } finally {
      setRecalculatingVAT(false)
    }
  }

  const buildTransactionParams = () => {
    const params: any = { q: query, _t: Date.now() }

    if (currentClient?.id) {
      params.client_id = currentClient.id
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

  const normalizeVisibleColumns = (cols: string[]): Set<ColumnId> => {
    const clean = cols.filter((col) => (DEFAULT_COLUMN_ORDER as readonly string[]).includes(col)) as ColumnId[]
    if (!clean.includes('account')) clean.push('account')
    return new Set(clean)
  }

  const columnVisibilityStorageKey = `txn_table_visible_columns_${userKey}`

  useEffect(() => {
    try {
      const raw = localStorage.getItem(columnStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) setColumnOrder(normalizeColumnOrder(parsed))
      }
    } catch { /* ignore */ }
  }, [columnStorageKey])

  useEffect(() => {
    try { localStorage.setItem(columnStorageKey, JSON.stringify(columnOrder)) } catch { /* ignore */ }
  }, [columnOrder, columnStorageKey])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(columnVisibilityStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) setVisibleColumns(normalizeVisibleColumns(parsed))
      }
    } catch { /* ignore */ }
  }, [columnVisibilityStorageKey])

  useEffect(() => {
    try { localStorage.setItem(columnVisibilityStorageKey, JSON.stringify(Array.from(visibleColumns))) } catch { /* ignore */ }
  }, [visibleColumns, columnVisibilityStorageKey])

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

  useEffect(() => {
    setHasActiveFilters(query !== '' || dateFrom !== '' || dateTo !== '' || selectedStatement !== '' || quickFilter !== 'all')
  }, [query, dateFrom, dateTo, selectedStatement, quickFilter])

  // Read URL params on mount only
  useEffect(() => {
    try {
      const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null
      const tf = params?.get('txn_filter')
      if (tf) {
        setTxnFilter(tf)
        if (tf === 'expenses') setQuickFilter('expenses')
        else if (tf === 'income') setQuickFilter('income')
        else if (tf === 'uncategorized') setQuickFilter('uncategorized')
      }
      const df = params?.get('date_from')
      if (df) { setDateFrom(df); setShowFilters(true) }
      const dt = params?.get('date_to')
      if (dt) { setDateTo(dt); setShowFilters(true) }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(prev => transactions.length === 0 ? true : prev)
        // Don't clear transactions to avoid table flash

        const params = buildTransactionParams()

        if (!params) {
          setTransactions([])
          setInvoicesById({})
          setLoading(false)
          return
        }

        const txnResponse = await axios.get(`${API_BASE_URL}/transactions`, { params })
        let txns = txnResponse.data.transactions || []

        if (txnFilter) {
          switch (txnFilter) {
            case 'expenses': txns = txns.filter((t: any) => Number(t.amount) < 0); break
            case 'income': txns = txns.filter((t: any) => Number(t.amount) > 0); break
            case 'uncategorized': txns = txns.filter((t: any) => !t.category || t.category === '' || t.category === 'Other' || t.category === 'Uncategorized'); break
          }
        }

        setTransactions(txns)
        setLoading(false)

        const invoiceParams = currentClient?.id ? { client_id: currentClient.id } : (sessionId ? { session_id: sessionId } : {})
        if (Object.keys(invoiceParams).length > 0) {
          try {
            const invResponse = await axios.get(`${API_BASE_URL}/invoices`, { params: invoiceParams })
            const invs = invResponse.data.invoices || []
            const byId: Record<number, any> = {}
            invs.forEach((inv: any) => { byId[inv.id] = inv })
            setInvoicesById(byId)
          } catch (invoiceError) {
            console.error('[TransactionsTable] Failed to fetch invoices:', invoiceError)
            setInvoicesById({})
          }
        } else {
          setInvoicesById({})
        }
      } catch (error) {
        console.error('[TransactionsTable] Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [sessionId, currentClient?.id, refreshTrigger, refreshKey, searchTrigger, selectedStatement, txnFilter])

  // Fetch categories whenever session, statement, or client changes
  useEffect(() => {
    const effectiveSessionId = sessionId || selectedStatement || null
    if (!effectiveSessionId && !currentClient?.id) return
    const params: any = { ...(currentClient?.id ? { client_id: currentClient.id } : {}) }
    if (effectiveSessionId) params.session_id = effectiveSessionId
    axios.get(`${API_BASE_URL}/categories`, { params })
      .then(res => {
        const categoryNames = (res.data.categories || []).map((cat: any) =>
          typeof cat === 'string' ? cat : cat.name
        )
        setCategoriesList(categoryNames)
      })
      .catch(() => {})
  }, [sessionId, selectedStatement, currentClient?.id])

  // Sync categories from props when they change (e.g. after upload or category creation)
  useEffect(() => {
    if (categories && categories.length > 0) setCategoriesList(categories)
  }, [categories])

  // Reset ALL filter/sort/search state when switching sessions or statements
  // This prevents stale filters from a previous statement bleeding into the new one
  useEffect(() => {
    setQuickFilter('all')
    setInstantQuery('')
    setQuery('')
    setDateFrom('')
    setDateTo('')
    setDateError(null)
    setCurrentPage(1)
    setSelectedIds(new Set())
    setOpeningBalance('0')
    setEditingCategoryId(null)
    setEditingMerchantId(null)
    setShowEditPanel(false)
    setSelectedTransactionForEdit(null)
    setTxnFilter(null)
  }, [sessionId, selectedStatement, currentClient?.id])

  // Reset page when filters change
  useEffect(() => { setCurrentPage(1) }, [quickFilter, debouncedInstantQuery, sortBy, sortDirection, dateFrom, dateTo, query])

  // Clear selection when page/filter changes
  useEffect(() => { setSelectedIds(new Set()) }, [currentPage, quickFilter, debouncedInstantQuery])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setDateError(null)
    if (dateFrom && dateTo) {
      if (new Date(dateFrom) > new Date(dateTo)) {
        setDateError('Start date must be on or before end date')
        return
      }
    }
    setSearchTrigger(prev => prev + 1)
  }

  const handleUndo = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/bulk-categorise/undo`, {}, { params: { session_id: sessionId } })
      if (response.data.success) {
        setTransactions(response.data.transactions || [])
        setUndoAvailable(response.data.undo_available)
        setSuccessMessage('Categorization reverted')
        setTimeout(() => setSuccessMessage(''), 4000)
      }
    } catch (error) { console.error('Undo failed:', error) }
  }

  const handleSaveMerchant = async (txnId: number, newMerchant: string) => {
    setSavingId(txnId)
    try {
      const txn = transactions.find(t => t.id === txnId)
      const txnSessionId = txn?.session_id || sessionId
      await axios.put(`${API_BASE_URL}/transactions/${txnId}/merchant`, { merchant: newMerchant || null }, { params: { session_id: txnSessionId } })
      setTransactions(prev => prev.map(t => t.id === txnId ? { ...t, merchant: newMerchant || null } : t))
      setEditingMerchantId(null)
      setSuccessMessage('Merchant saved')
      setTimeout(() => setSuccessMessage(''), 2000)
    } catch (error) {
      console.error('Failed to save merchant:', error)
      setSuccessMessage('Failed to save merchant')
      setTimeout(() => setSuccessMessage(''), 2000)
    } finally { setSavingId(null) }
  }

  const handleSaveCategory = async (txnId: number, newCategory: string) => {
    setSavingId(txnId)
    try {
      const txn = transactions.find(t => t.id === txnId)
      const txnSessionId = txn?.session_id || sessionId
      const response = await axios.put(`${API_BASE_URL}/transactions/${txnId}`, { category: newCategory }, { params: { session_id: txnSessionId } })
      // Merge API response (includes recalculated VAT fields) with existing transaction data
      const apiData = response.data || {}
      setTransactions(prev => prev.map(t => (t.id === txnId ? {
        ...t,
        category: newCategory,
        ...(apiData.vat_amount !== undefined ? { vat_amount: apiData.vat_amount } : {}),
        ...(apiData.amount_excl_vat !== undefined ? { amount_excl_vat: apiData.amount_excl_vat } : {}),
        ...(apiData.amount_incl_vat !== undefined ? { amount_incl_vat: apiData.amount_incl_vat } : {}),
      } : t)))
      setEditingCategoryId(null)
      setSuccessMessage('Category saved')
      setTimeout(() => setSuccessMessage(''), 2000)
    } catch (error) {
      console.error('Failed to save category:', error)
      setSuccessMessage('Failed to save category')
      setTimeout(() => setSuccessMessage(''), 2000)
    } finally { setSavingId(null) }
  }

  const handleHeaderClick = (field: 'date' | 'amount' | 'account' | 'category' | 'description' | 'merchant') => {
    if (sortBy === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortDirection('asc')
    }
  }

  const getSortIcon = (field: string) => {
    if (sortBy !== field) return <ArrowUpDown size={12} className="text-neutral-300" />
    return sortDirection === 'asc'
      ? <ArrowUp size={12} className="text-blue-600" />
      : <ArrowDown size={12} className="text-blue-600" />
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
    try { localStorage.removeItem(columnStorageKey) } catch { /* ignore */ }
  }

  const toggleColumnVisibility = (col: ColumnId) => {
    const newVisible = new Set(visibleColumns)
    if (newVisible.has(col)) newVisible.delete(col)
    else newVisible.add(col)
    setVisibleColumns(newVisible)
  }

  const getColumnLabel = (col: ColumnId): string => {
    const labels: Record<ColumnId, string> = {
      date: 'Date', description: 'Description', merchant: 'Merchant', amount: 'Amount',
      vat_amount: 'VAT', amount_excl_vat: 'Excl. VAT', account: 'Chart of Account', category: 'Category',
      invoice: 'Invoice', running_balance: 'Running Balance',
    }
    return labels[col] || col
  }

  const clearTxnFilter = () => {
    try {
      setTxnFilter(null)
      setQuickFilter('all')
      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search)
        params.delete('txn_filter')
        const newQs = params.toString()
        window.history.replaceState({}, '', window.location.pathname + (newQs ? `?${newQs}` : ''))
      }
      setSearchTrigger(prev => prev + 1)
    } catch { /* ignore */ }
  }

  const calculateRunningBalance = (txns: Transaction[]) => {
    const balanceMap = new Map<number, number>()
    let balance = parseFloat(openingBalance) || 0
    txns.forEach((txn) => { balance += txn.amount; balanceMap.set(txn.id, balance) })
    return balanceMap
  }

  // -- Computed: sorted + filtered transactions --
  const sortedAndFilteredTransactions = useMemo(() => {
    let filtered = [...transactions]

    // Client-side date filtering
    if (dateFrom) {
      const fromDate = new Date(dateFrom + 'T00:00:00').getTime()
      filtered = filtered.filter(t => new Date(t.date).getTime() >= fromDate)
    }
    if (dateTo) {
      const toDate = new Date(dateTo + 'T23:59:59').getTime()
      filtered = filtered.filter(t => new Date(t.date).getTime() <= toDate)
    }

    switch (quickFilter) {
      case 'income': filtered = filtered.filter(t => t.amount > 0); break
      case 'expenses': filtered = filtered.filter(t => t.amount < 0); break
      case 'uncategorized': filtered = filtered.filter(t => !t.category || t.category === '' || t.category === 'Other' || t.category === 'Uncategorized'); break
    }

    if (debouncedInstantQuery) {
      const q = debouncedInstantQuery.toLowerCase()
      filtered = filtered.filter(t =>
        (t.description || '').toLowerCase().includes(q) ||
        (t.merchant || '').toLowerCase().includes(q) ||
        (t.category || '').toLowerCase().includes(q) ||
        (t.account_code || '').toLowerCase().includes(q) ||
        (t.account_name || '').toLowerCase().includes(q)
      )
    }

    filtered.sort((a, b) => {
      let cmp = 0
      switch (sortBy) {
        case 'date': cmp = new Date(a.date).getTime() - new Date(b.date).getTime(); break
        case 'amount': cmp = Math.abs(a.amount) - Math.abs(b.amount); break
        case 'account': cmp = (`${a.account_code || ''} ${a.account_name || ''}`).localeCompare(`${b.account_code || ''} ${b.account_name || ''}`); break
        case 'category': cmp = (a.category || '').localeCompare(b.category || ''); break
        case 'description': cmp = (a.description || '').localeCompare(b.description || ''); break
        case 'merchant': cmp = (a.merchant || '').localeCompare(b.merchant || ''); break
      }
      return sortDirection === 'asc' ? cmp : -cmp
    })

    return filtered
  }, [transactions, quickFilter, debouncedInstantQuery, sortBy, sortDirection, dateFrom, dateTo])

  // -- Summary stats --
  const stats = useMemo(() => {
    const income = transactions.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
    const expenses = transactions.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)
    const uncategorized = transactions.filter(t => !t.category || t.category === '' || t.category === 'Other' || t.category === 'Uncategorized').length
    return { income, expenses, net: income - expenses, uncategorized, total: transactions.length }
  }, [transactions])

  const filteredStats = useMemo(() => {
    const income = sortedAndFilteredTransactions.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
    const expenses = sortedAndFilteredTransactions.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)
    return { income, expenses, net: income - expenses, count: sortedAndFilteredTransactions.length }
  }, [sortedAndFilteredTransactions])

  const selectedStats = useMemo(() => {
    const selected = transactions.filter(t => selectedIds.has(t.id))
    const income = selected.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
    const expenses = selected.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)
    return { income, expenses, net: income - expenses, count: selected.length }
  }, [transactions, selectedIds])

  // -- Pagination --
  const totalPages = Math.max(1, Math.ceil(sortedAndFilteredTransactions.length / pageSize))
  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return sortedAndFilteredTransactions.slice(start, start + pageSize)
  }, [sortedAndFilteredTransactions, currentPage, pageSize])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select, button, [role="dialog"]')) return
      if (showEditPanel || showBulkEditModal || showColumnPicker) return
      if (paginatedTransactions.length === 0) return

      const currentIndex = focusedTxnId == null
        ? -1
        : paginatedTransactions.findIndex((txn) => txn.id === focusedTxnId)

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        const next = paginatedTransactions[Math.min(paginatedTransactions.length - 1, currentIndex + 1)]
        if (next) setFocusedTxnId(next.id)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        const next = paginatedTransactions[Math.max(0, currentIndex === -1 ? 0 : currentIndex - 1)]
        if (next) setFocusedTxnId(next.id)
      } else if (event.key === 'Enter' && focusedTxnId != null) {
        const txn = paginatedTransactions.find((item) => item.id === focusedTxnId)
        if (txn) {
          event.preventDefault()
          setSelectedTransactionForEdit(txn)
          setShowEditPanel(true)
        }
      } else if (event.key === ' ' && focusedTxnId != null) {
        event.preventDefault()
        toggleSelect(focusedTxnId)
      } else if ((event.key === 'b' || event.key === 'B') && selectedIds.size > 0) {
        event.preventDefault()
        handleBulkEditSelected()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [focusedTxnId, paginatedTransactions, selectedIds, showBulkEditModal, showColumnPicker, showEditPanel])

  // -- Selection helpers --
  const allPageSelected = paginatedTransactions.length > 0 && paginatedTransactions.every(t => selectedIds.has(t.id))
  const somePageSelected = paginatedTransactions.some(t => selectedIds.has(t.id))

  const toggleSelectAll = () => {
    if (allPageSelected) {
      const newSet = new Set(selectedIds)
      paginatedTransactions.forEach(t => newSet.delete(t.id))
      setSelectedIds(newSet)
    } else {
      const newSet = new Set(selectedIds)
      paginatedTransactions.forEach(t => newSet.add(t.id))
      setSelectedIds(newSet)
    }
  }

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds)
    if (newSet.has(id)) newSet.delete(id)
    else newSet.add(id)
    setSelectedIds(newSet)
  }

  const selectAllFiltered = () => {
    const newSet = new Set(selectedIds)
    sortedAndFilteredTransactions.forEach(t => newSet.add(t.id))
    setSelectedIds(newSet)
  }

  const clearSelection = () => setSelectedIds(new Set())

  const handleBulkEditSelected = () => {
    const selected = transactions.filter(t => selectedIds.has(t.id))
    setFilteredModalTransactions(selected)
    setShowBulkEditModal(true)
  }

  // Refetch helper - silent refetch that preserves table state (no loading spinner)
  const refetchTransactions = () => {
    const params = buildTransactionParams()
    if (!params) { setTransactions([]); return }
    axios.get(`${API_BASE_URL}/transactions`, { params })
      .then((res) => setTransactions(res.data.transactions || []))
      .catch((e) => console.error('Refetch failed', e))
  }

  if (loading) {
    return <LoadingSection message="Loading transactions..." size="lg" />
  }

  const visibleCols = columnOrder.filter((c) => visibleColumns.has(c) && (c !== 'running_balance' || showRunningBalance) && ((c !== 'vat_amount' && c !== 'amount_excl_vat') || vatEnabled))

  return (
    <div className="overflow-hidden rounded-md border border-neutral-300 bg-white shadow-sm dark:border-neutral-700 dark:bg-neutral-900">
      {/* ─── Header ─── */}
      <div className="border-b border-neutral-300">
        {/* Title row */}
        <div className="flex items-center justify-between gap-3 bg-white px-3 py-2">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold tracking-tight text-neutral-950">Transactions</h2>
            <p className="mt-0.5 text-xs text-neutral-500">
              {sortedAndFilteredTransactions.length === transactions.length
                ? `${transactions.length} transactions`
                : `${sortedAndFilteredTransactions.length} of ${transactions.length} transactions`}
              <span className="mx-2 text-neutral-300">|</span>
              Net {filteredStats.net >= 0 ? '+' : '-'}R{Math.abs(filteredStats.net).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
            </p>
          </div>

          {/* Primary actions */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => {
                setFilteredModalTransactions(selectedIds.size > 0 ? transactions.filter(t => selectedIds.has(t.id)) : sortedAndFilteredTransactions)
                setShowBulkEditModal(true)
              }}
              className="inline-flex items-center gap-1.5 rounded bg-neutral-900 px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-neutral-800 active:bg-neutral-950"
              title="Bulk edit selected or filtered transactions"
            >
              Bulk edit
              <span className="rounded bg-white/20 px-1 text-xs">{selectedIds.size || sortedAndFilteredTransactions.length}</span>
            </button>
            <button
              onClick={() => setShowClearCategoriesModal(true)}
              className="inline-flex items-center rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-50 active:bg-neutral-100"
              title="Clear all categories"
            >
              Clear
            </button>
          </div>
        </div>

        {/* ─── Quick Filter Chips + Instant Search ─── */}
        <div className="flex flex-wrap items-center gap-1.5 border-t border-neutral-200 bg-neutral-100/70 px-3 py-2">
          {/* Quick filter chips */}
          <div className="flex items-center gap-1.5">
            {([
              { key: 'all' as QuickFilter, label: 'All', count: stats.total },
              { key: 'income' as QuickFilter, label: 'Income', count: transactions.filter(t => t.amount > 0).length },
              { key: 'expenses' as QuickFilter, label: 'Expenses', count: transactions.filter(t => t.amount < 0).length },
              { key: 'uncategorized' as QuickFilter, label: 'Uncategorized', count: stats.uncategorized },
            ]).map(chip => (
              <button
                key={chip.key}
                onClick={() => { setQuickFilter(chip.key); setTxnFilter(null) }}
                className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  quickFilter === chip.key
                    ? 'border-neutral-800 bg-neutral-800 text-white shadow-sm'
                    : 'bg-white text-neutral-600 border border-neutral-200 hover:bg-neutral-100 hover:border-neutral-300'
                }`}
              >
                {chip.label}
                <span className={`ml-0.5 tabular-nums ${quickFilter === chip.key ? 'opacity-80' : 'text-neutral-400'}`}>
                  {chip.count}
                </span>
              </button>
            ))}
          </div>

          {/* Instant search */}
          <div className="relative min-w-[260px] flex-1">
            <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              placeholder="Search description, merchant, account, category..."
              value={instantQuery}
              onChange={(e) => setInstantQuery(e.target.value)}
              className="h-8 w-full rounded border border-neutral-300 bg-white py-1.5 pl-8 pr-8 text-sm transition-colors placeholder:text-neutral-400 focus:border-neutral-600 focus:outline-none focus:ring-1 focus:ring-neutral-300"
            />
            {instantQuery && (
              <button
                onClick={() => setInstantQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {selectedIds.size > 0 && (
            <div className="inline-flex items-center gap-2 rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700">
              {selectedIds.size} selected
              <span className="font-mono">
                {selectedStats.net >= 0 ? '+' : '-'}R{Math.abs(selectedStats.net).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </span>
            </div>
          )}

          {/* VAT Recalculate button (only when VAT is enabled) */}
          {currentClient?.id && vatEnabled && (
            <button
              onClick={handleRecalculateVAT}
              disabled={recalculatingVAT}
              className="inline-flex items-center gap-1.5 rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              title="Recalculate VAT for all transactions across all statements"
            >
              {recalculatingVAT ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Calculator size={13} />
              )}
              {recalculatingVAT ? 'Recalculating...' : 'Recalculate VAT'}
            </button>
          )}

          {/* Advanced filters toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs font-medium transition-colors ${
              hasActiveFilters && (dateFrom || dateTo || query)
                ? 'border-neutral-800 bg-neutral-800 text-white'
                : 'bg-white text-neutral-600 border border-neutral-200 hover:bg-neutral-100'
            }`}
          >
            Advanced
            <ChevronDown size={13} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>

          <div className="flex-1" />

          {/* View option buttons */}
          <button onClick={handleRefreshData} className="inline-flex h-8 w-8 items-center justify-center rounded border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50" title="Refresh">
            <RefreshCw size={13} />
          </button>
          <button onClick={handleResetColumns} className="inline-flex h-8 w-8 items-center justify-center rounded border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50" title="Reset columns">
            <RotateCcw size={13} />
          </button>

          {/* Column Picker */}
          <div className="relative" ref={columnPickerRef}>
            <button
              onClick={() => setShowColumnPicker(!showColumnPicker)}
              className="inline-flex h-8 items-center rounded border border-neutral-200 bg-white px-2.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
              title="Show/hide columns"
            >
              Columns
            </button>

            {showColumnPicker && (
              <div className="absolute right-0 mt-2 w-52 bg-white border border-neutral-200 rounded-xl shadow-xl z-50 overflow-hidden">
                <div className="px-4 py-2.5 border-b border-neutral-100 bg-neutral-50">
                  <p className="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Visible Columns</p>
                </div>
                <div className="max-h-64 overflow-y-auto py-1">
                  {DEFAULT_COLUMN_ORDER.filter((col) => (col !== 'vat_amount' && col !== 'amount_excl_vat') || vatEnabled).map((col) => (
                    <label key={col} className="flex items-center gap-2.5 px-4 py-2 hover:bg-neutral-50 cursor-pointer text-sm">
                      <input
                        type="checkbox"
                        checked={visibleColumns.has(col)}
                        onChange={() => toggleColumnVisibility(col)}
                        className="w-3.5 h-3.5 rounded border-neutral-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-neutral-700 text-xs font-medium">{getColumnLabel(col)}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ─── Advanced Filter Panel (collapsible) ─── */}
        {showFilters && (
          <div className="px-6 py-4 bg-white border-t border-neutral-100">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="block text-[10px] font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword Search</label>
                <input
                  type="text"
                  placeholder="Search..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-neutral-500 uppercase tracking-wide mb-1">From Date</label>
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:border-transparent" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-neutral-500 uppercase tracking-wide mb-1">To Date</label>
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:border-transparent" />
              </div>
              <div className="flex items-end gap-2">
                <button onClick={handleSearch} className="flex-1 px-4 py-2 text-sm font-medium bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 transition-colors">
                  Apply
                </button>
                <button
                  onClick={() => { setQuery(''); setDateFrom(''); setDateTo(''); setDateError(null); setSearchTrigger(prev => prev + 1) }}
                  className="flex-1 px-4 py-2 text-sm font-medium bg-white text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="border-t border-neutral-100 pt-3 mt-3">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={showRunningBalance} onChange={(e) => setShowRunningBalance(e.target.checked)}
                    className="w-3.5 h-3.5 border border-neutral-300 rounded cursor-pointer" />
                  <span className="text-xs font-medium text-neutral-600">Show Running Balance</span>
                </label>
                {showRunningBalance && (
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-medium text-neutral-600">Opening Balance:</label>
                    <input type="number" step="0.01" value={openingBalance} onChange={(e) => setOpeningBalance(e.target.value)}
                      className="w-28 text-sm px-2 py-1.5 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-400" placeholder="0.00" />
                  </div>
                )}
              </div>
            </div>

            {dateError && (
              <div className="mt-2 flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{dateError}</span>
              </div>
            )}
          </div>
        )}

        {/* Success/Undo bar */}
        {(successMessage || undoAvailable) && (
          <div className="flex items-center justify-between text-sm bg-emerald-50 border-t border-emerald-200 px-6 py-2">
            <div className="text-emerald-700 font-medium flex items-center gap-2">
              <Check size={15} />
              {successMessage || 'Ready to undo'}
            </div>
            {undoAvailable && (
              <button onClick={handleUndo} className="text-sm font-medium text-emerald-700 hover:text-emerald-800 underline">
                Undo
              </button>
            )}
          </div>
        )}

      </div>

      {/* ─── Floating Bulk Actions Bar ─── */}
      {selectedIds.size > 0 && (
        <div className="sticky top-0 z-30 flex items-center justify-between border-b border-blue-300 bg-blue-50 px-4 py-2.5 text-blue-950 shadow-sm">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold">{selectedIds.size} selected</span>
            <span className="text-xs font-mono text-blue-800">
              Net {selectedStats.net >= 0 ? '+' : '-'}R{Math.abs(selectedStats.net).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
            </span>
            <button onClick={selectAllFiltered} className="text-xs font-medium underline text-blue-700 hover:text-blue-900">
              Select all {sortedAndFilteredTransactions.length}
            </button>
            <button onClick={clearSelection} className="text-xs font-medium underline text-blue-700 hover:text-blue-900">
              Clear
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkEditSelected}
              className="inline-flex items-center gap-1.5 rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-neutral-800"
            >
              Bulk edit selected
            </button>
            <button
              onClick={() => {
                const selected = transactions.filter(t => selectedIds.has(t.id))
                setFilteredModalTransactions(selected)
                setShowBulkEditModal(true)
              }}
              className="inline-flex items-center gap-1.5 rounded-md border border-blue-300 bg-white px-3 py-1.5 text-xs font-semibold text-blue-800 transition-colors hover:bg-blue-100"
            >
              <PanelRightOpen size={13} />
              Review rows
            </button>
          </div>
        </div>
      )}

      {/* ─── Modals ─── */}
      <BulkEditModal
        isOpen={showBulkEditModal}
        onClose={() => { setShowBulkEditModal(false); setFilteredModalTransactions(null) }}
        transactions={filteredModalTransactions || transactions}
        categories={categoriesList}
        sessionId={sessionId || ''}
        clientId={currentClient?.id}
        onApplied={(message, count) => {
          setShowBulkEditModal(false)
          setFilteredModalTransactions(null)
          setSuccessMessage(message)
          setSelectedIds(new Set())
          setTimeout(() => setSuccessMessage(''), 4000)
          refetchTransactions()
        }}
      />

      {/* Clear Categories Confirmation Modal */}
      {showClearCategoriesModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full mx-4 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-red-100 bg-red-50">
              <h2 className="text-base font-semibold text-red-900">Clear All Categories?</h2>
              <button onClick={() => setShowClearCategoriesModal(false)} className="p-1 hover:bg-red-100 rounded-md transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="px-6 py-5 space-y-3">
              <p className="text-sm text-neutral-700">
                This will remove categories from <strong>all {transactions.length} transactions</strong> in this session.
              </p>
              <p className="flex items-center gap-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                <span>This action cannot be undone.</span>
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-neutral-100 bg-neutral-50">
              <button onClick={() => setShowClearCategoriesModal(false)} disabled={clearingCategories}
                className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 disabled:opacity-50 transition-colors">
                Cancel
              </button>
              <button
                onClick={async () => {
                  setClearingCategories(true)
                  try {
                    await axios.post(`${API_BASE_URL}/transactions/clear-categories`, {},
                      { params: currentClient?.id ? { client_id: currentClient.id } : { session_id: sessionId } })
                    setShowClearCategoriesModal(false)
                    setSuccessMessage(`Cleared categories from ${transactions.length} transactions`)
                    setTimeout(() => setSuccessMessage(''), 4000)
                    refetchTransactions()
                  } catch (error: any) {
                    console.error('Failed to clear categories:', error)
                    if (isAxiosError(error) && error.response?.data) {
                      setSuccessMessage(`Failed: ${error.response.data.detail || 'Unknown error'}`)
                    } else {
                      setSuccessMessage('Failed to clear categories')
                    }
                    setTimeout(() => setSuccessMessage(''), 4000)
                  } finally { setClearingCategories(false) }
                }}
                disabled={clearingCategories}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {clearingCategories ? 'Clearing...' : 'Clear All'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Table ─── */}
      <div ref={tableContainerRef} className="max-h-[68vh] overflow-auto bg-white">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table className="w-full min-w-[1240px] border-separate border-spacing-0 text-xs">
            <SortableContext items={visibleCols} strategy={horizontalListSortingStrategy}>
              <thead className="sticky top-0 z-20">
                <tr className="bg-neutral-100">
                  {/* Checkbox header */}
                  <th className="sticky left-0 z-30 w-10 border-b border-r border-neutral-300 bg-neutral-100 px-2 py-2 text-center">
                    <button onClick={toggleSelectAll} className="text-neutral-400 hover:text-neutral-700 transition-colors"
                      title={allPageSelected ? 'Deselect all on page' : 'Select all on page'}>
                      {allPageSelected ? <CheckSquare size={16} className="text-blue-600" />
                        : somePageSelected ? <MinusSquare size={16} className="text-blue-400" />
                        : <Square size={16} />}
                    </button>
                  </th>
                  {visibleCols.map((col) => {
                    const base = "border-b border-r border-neutral-300 px-3 py-2 font-semibold text-[11px] uppercase tracking-wide text-neutral-600 select-none whitespace-nowrap bg-neutral-100"
                    switch (col) {
                      case 'date':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('date')} className={`sticky left-10 z-30 min-w-[104px] text-left ${base} cursor-pointer hover:text-neutral-800`}>Date {getSortIcon('date')}</SortableHeaderCell>
                      case 'description':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('description')} className={`min-w-[360px] text-left ${base} cursor-pointer hover:text-neutral-800`}>Description {getSortIcon('description')}</SortableHeaderCell>
                      case 'merchant':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('merchant')} className={`min-w-[160px] text-left ${base} cursor-pointer hover:text-neutral-800`}>Merchant {getSortIcon('merchant')}</SortableHeaderCell>
                      case 'amount':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('amount')} className={`text-right ${base} cursor-pointer hover:text-neutral-800`} align="right">Amount {getSortIcon('amount')}</SortableHeaderCell>
                      case 'vat_amount':
                        return <SortableHeaderCell key={col} id={col} className={`text-right ${base}`} align="right">VAT <span className="text-neutral-400 font-normal">(15%)</span></SortableHeaderCell>
                      case 'amount_excl_vat':
                        return <SortableHeaderCell key={col} id={col} className={`text-right ${base}`} align="right">Excl. VAT</SortableHeaderCell>
                      case 'account':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('account')} className={`min-w-[220px] text-left ${base} cursor-pointer hover:text-neutral-800`}>Chart of Account {getSortIcon('account')}</SortableHeaderCell>
                      case 'category':
                        return <SortableHeaderCell key={col} id={col} onClick={() => handleHeaderClick('category')} className={`min-w-[170px] text-left ${base} cursor-pointer hover:text-neutral-800`}>Category {getSortIcon('category')}</SortableHeaderCell>
                      case 'invoice':
                        return <SortableHeaderCell key={col} id={col} className={`text-left ${base}`}>Invoice</SortableHeaderCell>
                      case 'running_balance':
                        return <SortableHeaderCell key={col} id={col} className={`text-right ${base}`} align="right">Balance</SortableHeaderCell>
                      default: return null
                    }
                  })}
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const balanceMap = calculateRunningBalance(sortedAndFilteredTransactions)
                  return paginatedTransactions.map((txn, idx) => {
                    const isSelected = selectedIds.has(txn.id)
                    const isHighlighted = highlightTxnId === txn.id
                    return (
                      <tr
                        key={txn.id}
                        tabIndex={0}
                        onClick={() => setFocusedTxnId(txn.id)}
                        onDoubleClick={() => { setFocusedTxnId(txn.id); setSelectedTransactionForEdit(txn); setShowEditPanel(true) }}
                        className={`group cursor-default outline-none transition-colors ${
                          isHighlighted ? 'bg-amber-50 hover:bg-amber-100'
                          : isSelected ? 'bg-blue-50 hover:bg-blue-50'
                          : focusedTxnId === txn.id ? 'bg-sky-50 hover:bg-sky-50'
                          : idx % 2 === 0 ? 'bg-white hover:bg-neutral-50'
                          : 'bg-neutral-50/50 hover:bg-neutral-100'
                        }`}
                      >
                        <td className={`sticky left-0 z-10 w-10 border-b border-r border-neutral-200 px-2 py-1.5 text-center ${isSelected ? 'bg-blue-50' : focusedTxnId === txn.id ? 'bg-sky-50' : idx % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}`}>
                          <button onClick={(e) => { e.stopPropagation(); toggleSelect(txn.id) }} className="text-neutral-300 hover:text-blue-600 transition-colors">
                            {isSelected ? <CheckSquare size={15} className="text-blue-600" /> : <Square size={15} className="opacity-0 group-hover:opacity-100 transition-opacity" />}
                          </button>
                        </td>
                        {visibleCols.map((col) => {
                          switch (col) {
                            case 'date':
                              return <td key={`${txn.id}-${col}`} className={`sticky left-10 z-10 whitespace-nowrap border-b border-r border-neutral-200 px-3 py-1.5 text-xs tabular-nums text-neutral-600 ${isSelected ? 'bg-blue-50' : focusedTxnId === txn.id ? 'bg-sky-50' : idx % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}`}>{new Date(txn.date).toLocaleDateString('en-ZA')}</td>
                            case 'description': {
                              const displayDesc = cleanDescription(txn.description)
                              return (
                                <td key={`${txn.id}-${col}`} className="max-w-sm border-b border-r border-neutral-200 px-3 py-1.5">
                                  <div className="flex flex-col gap-0.5">
                                    <div onClick={(e) => { e.stopPropagation(); setSelectedTransactionForEdit(txn); setShowEditPanel(true) }}
                                      className="cursor-pointer whitespace-normal break-words text-xs leading-snug text-neutral-900 transition-colors hover:text-blue-600" title="Click to edit">
                                      {displayDesc || <span className="text-neutral-400 italic text-xs">[No description]</span>}
                                    </div>
                                    {!selectedStatement && txn.statement_name && txn.statement_name !== 'Unknown Statement' && (
                                      <span className="inline-flex items-center gap-1 text-[10px] text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded self-start">
                                        <FileText className="h-3 w-3" />
                                        {txn.statement_name}
                                      </span>
                                    )}
                                  </div>
                                </td>
                              )
                            }
                            case 'merchant':
                              return (
                                <td key={`${txn.id}-${col}`} className="max-w-[180px] border-b border-r border-neutral-200 px-3 py-1.5">
                                  <div onClick={(e) => { e.stopPropagation(); setSelectedTransactionForEdit(txn); setShowEditPanel(true) }}
                                    className="group/merchant flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-neutral-100 cursor-pointer transition-colors">
                                    <span className="text-xs text-neutral-700 truncate">{txn.merchant || <span className="text-neutral-300 italic">Add merchant</span>}</span>
                                    <Pencil className="h-3 w-3 text-neutral-300 opacity-0 group-hover/merchant:opacity-100 transition-opacity" />
                                  </div>
                                </td>
                              )
                            case 'amount': {
                              const isPositive = txn.amount >= 0
                              return (
                                <td key={`${txn.id}-${col}`} className="whitespace-nowrap border-b border-r border-neutral-200 px-3 py-1.5 text-right">
                                  <span className={`inline-flex items-center gap-1 font-mono text-xs font-semibold tabular-nums ${isPositive ? 'text-emerald-700' : 'text-red-700'}`}>
                                    {isPositive ? '+' : '-'}R{Math.abs(txn.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                                  </span>
                                </td>
                              )
                            }
                            case 'vat_amount':
                              return (
                                <td key={`${txn.id}-${col}`} className="whitespace-nowrap border-b border-r border-neutral-200 px-3 py-1.5 text-right">
                                  {txn.vat_amount != null
                                    ? <span className="text-xs text-violet-600 tabular-nums">R{Math.abs(txn.vat_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                                    : <span className="text-neutral-200">—</span>}
                                </td>
                              )
                            case 'amount_excl_vat':
                              return (
                                <td key={`${txn.id}-${col}`} className="whitespace-nowrap border-b border-r border-neutral-200 px-3 py-1.5 text-right">
                                  {txn.amount_excl_vat != null
                                    ? <span className="text-xs text-neutral-600 tabular-nums">R{Math.abs(txn.amount_excl_vat).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</span>
                                    : <span className="text-neutral-200">—</span>}
                                </td>
                              )
                            case 'account': {
                              const accountLabel = txn.account_id
                                ? `${txn.account_code ? `${txn.account_code} ` : ''}${txn.account_name || ''}`.trim()
                                : ''
                              return (
                                <td key={`${txn.id}-${col}`} className="border-b border-r border-neutral-200 px-3 py-1.5">
                                  <div onClick={(e) => { e.stopPropagation(); setSelectedTransactionForEdit(txn); setShowEditPanel(true) }} className="cursor-pointer group/account space-y-1">
                                    {accountLabel ? (
                                      <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-800 hover:text-neutral-950">
                                        {txn.account_code && <span className="font-mono text-[11px] text-neutral-500">{txn.account_code}</span>}
                                        {txn.account_name}
                                        <Pencil size={11} className="opacity-0 transition-opacity group-hover/account:opacity-50" />
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-400 hover:text-neutral-600">
                                        + Add account
                                      </span>
                                    )}
                                    {!txn.account_id && txn.suggested_account_id ? (
                                      <span className="block rounded-md bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-800 ring-1 ring-amber-200">
                                        Suggest: {txn.suggested_account_code ? `${txn.suggested_account_code} ` : ''}{txn.suggested_account_name}
                                        {typeof txn.mapping_confidence === 'number' ? ` (${Math.round(txn.mapping_confidence * 100)}%)` : ''}
                                      </span>
                                    ) : null}
                                  </div>
                                </td>
                              )
                            }
                            case 'category': {
                              return (
                                <td key={`${txn.id}-${col}`} className="border-b border-r border-neutral-200 px-3 py-1.5">
                                  <div onClick={(e) => { e.stopPropagation(); setSelectedTransactionForEdit(txn); setShowEditPanel(true) }} className="cursor-pointer group/cat space-y-1">
                                    {txn.category && txn.category !== 'Uncategorized' ? (
                                      <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-800 hover:text-neutral-950">
                                        {txn.category}
                                        <Pencil size={11} className="opacity-0 transition-opacity group-hover/cat:opacity-50" />
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-400 hover:text-neutral-600">
                                        + Add category
                                      </span>
                                    )}
                                  </div>
                                </td>
                              )
                            }
                            case 'invoice':
                              return (
                                <td key={`${txn.id}-${col}`} className="border-b border-r border-neutral-200 px-3 py-1.5">
                                  {(() => {
                                    const inv = txn.invoice_id ? invoicesById[txn.invoice_id] : null
                                    return inv ? (
                                      <button
                                        className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-md text-[11px] font-medium hover:bg-blue-100 transition-colors"
                                        onClick={(e) => { e.stopPropagation(); setSelectedInvoice(inv); setSelectedInvoiceTxnId(txn.id); setShowInvoiceModal(true) }}
                                        title="View / download invoice">
                                        <FileText size={12} /> Invoice
                                      </button>
                                    ) : (
                                      <button
                                        onClick={(e) => { e.stopPropagation(); setTransactionForUpload({ id: txn.id, date: txn.date, description: txn.description, amount: txn.amount, session_id: txn.session_id }); setShowInvoiceUploadModal(true) }}
                                        className="inline-flex items-center gap-1 px-2 py-1 text-neutral-400 rounded-md text-[11px] font-medium hover:bg-neutral-100 hover:text-neutral-600 transition-colors opacity-0 group-hover:opacity-100"
                                        title="Attach invoice">
                                        + Invoice
                                      </button>
                                    )
                                  })()}
                                </td>
                              )
                            case 'running_balance':
                              return (
                                <td key={`${txn.id}-${col}`} className="whitespace-nowrap border-b border-r border-neutral-200 px-3 py-1.5 text-right">
                                  {(() => {
                                    const balance = balanceMap.get(txn.id)
                                    const isNeg = balance !== undefined && balance < 0
                                    return <span className={`text-xs font-medium tabular-nums ${isNeg ? 'text-red-600' : 'text-emerald-600'}`}>R{balance !== undefined ? Math.abs(balance).toLocaleString('en-ZA', { minimumFractionDigits: 2 }) : '0.00'}</span>
                                  })()}
                                </td>
                              )
                            default: return null
                          }
                        })}
                      </tr>
                    )
                  })
                })()}
              </tbody>
            </SortableContext>

            {/* ─── Summary Footer ─── */}
            {sortedAndFilteredTransactions.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-neutral-200 bg-neutral-50/80">
                  <td className="px-3 py-3" />
                  {visibleCols.map((col) => {
                    switch (col) {
                      case 'description':
                        return <td key={`footer-${col}`} className="px-4 py-3 text-xs font-semibold text-neutral-600">Page {currentPage} of {totalPages} · {paginatedTransactions.length} of {sortedAndFilteredTransactions.length}</td>
                      case 'amount':
                        return (
                          <td key={`footer-${col}`} className="px-4 py-3 text-right">
                            <div className="space-y-0.5">
                              <div className="text-[10px] text-emerald-600 font-semibold tabular-nums">+R{filteredStats.income.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</div>
                              <div className="text-[10px] text-red-600 font-semibold tabular-nums">-R{filteredStats.expenses.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</div>
                              <div className={`text-xs font-bold tabular-nums border-t border-neutral-200 pt-0.5 ${filteredStats.net >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                                {filteredStats.net >= 0 ? '+' : '-'}R{Math.abs(filteredStats.net).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                              </div>
                            </div>
                          </td>
                        )
                      default:
                        return <td key={`footer-${col}`} className="px-4 py-3" />
                    }
                  })}
                </tr>
              </tfoot>
            )}
          </table>
        </DndContext>
      </div>

      {/* ─── Pagination Controls ─── */}
      {sortedAndFilteredTransactions.length > 0 && (
        <div className="border-t border-neutral-200 bg-white px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-500">Rows per page:</span>
            <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1) }}
              className="text-xs px-2 py-1 border border-neutral-200 rounded-md bg-white text-neutral-700 focus:outline-none focus:ring-1 focus:ring-neutral-400">
              {PAGE_SIZE_OPTIONS.map(size => <option key={size} value={size}>{size}</option>)}
            </select>
          </div>

          <div className="text-xs text-neutral-500 tabular-nums">
            {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, sortedAndFilteredTransactions.length)} of {sortedAndFilteredTransactions.length}
          </div>

          <div className="flex items-center gap-1">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1}
              className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors" title="First page">
              <ChevronsLeft size={15} />
            </button>
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
              className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors" title="Previous page">
              <ChevronLeft size={15} />
            </button>

            <div className="flex items-center gap-0.5 mx-1">
              {(() => {
                const pages: number[] = []
                const maxVisible = 5
                let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
                const end = Math.min(totalPages, start + maxVisible - 1)
                if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1)
                for (let i = start; i <= end; i++) pages.push(i)
                return pages.map(page => (
                  <button key={page} onClick={() => setCurrentPage(page)}
                    className={`min-w-[28px] h-7 text-xs font-medium rounded-md transition-colors ${page === currentPage ? 'bg-neutral-900 text-white shadow-sm' : 'text-neutral-600 hover:bg-neutral-100'}`}>
                    {page}
                  </button>
                ))
              })()}
            </div>

            <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}
              className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors" title="Next page">
              <ChevronRight size={15} />
            </button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}
              className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent transition-colors" title="Last page">
              <ChevronsRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* ─── Empty States ─── */}
      {transactions.length === 0 && !loading && (
        <div className="px-6 py-16 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-neutral-100 mb-3">
            <FileText size={20} className="text-neutral-400" />
          </div>
          <p className="text-sm font-medium text-neutral-700">No transactions found</p>
          <p className="text-xs text-neutral-400 mt-1">Upload a statement or select a different client to get started.</p>
        </div>
      )}

      {sortedAndFilteredTransactions.length === 0 && transactions.length > 0 && (
        <div className="px-6 py-12 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-neutral-100 mb-3">
            <Search size={16} className="text-neutral-400" />
          </div>
          <p className="text-sm font-medium text-neutral-600">No matching transactions</p>
          <p className="text-xs text-neutral-400 mt-1">Try adjusting your search or filters.</p>
          <button onClick={() => { setInstantQuery(''); setQuickFilter('all') }}
            className="mt-3 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline">
            Clear filters
          </button>
        </div>
      )}

      {/* Attached Invoice Panel */}
      {showInvoiceModal && selectedInvoice && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowInvoiceModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50">
                  <FileText className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-neutral-900">Attached Invoice</h2>
                  <p className="text-[11px] text-neutral-400">{selectedInvoice.file_reference?.split('/').pop() || 'invoice.pdf'}</p>
                </div>
              </div>
              <button onClick={() => setShowInvoiceModal(false)} className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
                <X size={16} />
              </button>
            </div>

            {/* Actions */}
            <div className="px-5 py-4 flex gap-3">
              {selectedInvoice.file_reference && (
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const txnSessionId = transactions.find(t => t.id === selectedInvoiceTxnId)?.session_id || sessionId
                      const response = await axios.get(`${API_BASE_URL}/invoice/download`, { params: { invoice_id: selectedInvoice.id, ...(txnSessionId ? { session_id: txnSessionId } : {}) }, responseType: 'blob' })
                      try {
                        const text = await (response.data as Blob).text()
                        const json = JSON.parse(text)
                        if (json.download_url) { window.open(json.download_url, '_blank'); return }
                      } catch {}
                      const url = window.URL.createObjectURL(response.data as Blob)
                      const link = document.createElement('a')
                      link.href = url; link.download = selectedInvoice.file_reference.split('/').pop() || `invoice_${selectedInvoice.id}.pdf`
                      document.body.appendChild(link); link.click(); link.remove()
                      window.URL.revokeObjectURL(url)
                    } catch { /* ignore */ }
                  }}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors">
                  <FileText size={14} /> Download
                </button>
              )}
              <button
                type="button"
                disabled={deletingInvoice}
                onClick={async () => {
                  if (!selectedInvoice) return
                  setDeletingInvoice(true)
                  try {
                    const txnSessionId = transactions.find(t => t.id === selectedInvoiceTxnId)?.session_id || sessionId
                    await axios.delete(`${API_BASE_URL}/invoice/${selectedInvoice.id}`, { params: txnSessionId ? { session_id: txnSessionId } : {} })
                    // Remove from local state
                    setInvoicesById(prev => { const next = { ...prev }; delete next[selectedInvoice.id]; return next })
                    // Clear invoice_id from the transaction
                    if (selectedInvoiceTxnId) {
                      setTransactions(prev => prev.map(t => t.id === selectedInvoiceTxnId ? { ...t, invoice_id: null } : t))
                    }
                    setShowInvoiceModal(false)
                    setSelectedInvoice(null)
                    setSelectedInvoiceTxnId(null)
                  } catch {
                    /* ignore */
                  } finally {
                    setDeletingInvoice(false)
                  }
                }}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50">
                <Trash2 size={14} /> {deletingInvoice ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <InvoiceUploadModal
        isOpen={showInvoiceUploadModal}
        onClose={() => { setShowInvoiceUploadModal(false); setTransactionForUpload(null) }}
        transaction={transactionForUpload}
        sessionId={sessionId || ''}
        onUploadSuccess={(message, invoice) => {
          setSuccessMessage(message)
          setShowInvoiceUploadModal(false)
          setTransactionForUpload(null)
          setTimeout(() => setSuccessMessage(''), 3000)
          if (invoice && transactionForUpload) {
            // Register invoice in the id map
            setInvoicesById(prev => ({ ...prev, [invoice.id]: invoice }))
            // Link the invoice to the transaction in local state
            setTransactions(prev => prev.map(t => t.id === transactionForUpload.id ? { ...t, invoice_id: invoice.id } : t))
          }
        }}
      />

      <TransactionEditPanel
        isOpen={showEditPanel}
        transaction={selectedTransactionForEdit}
        sessionId={sessionId || ''}
        clientId={currentClient?.id}
        categories={categoriesList}
        onClose={() => { setShowEditPanel(false); setSelectedTransactionForEdit(null) }}
        onSave={(updatedTransaction) => {
          // Merge updated fields with existing transaction data to preserve all fields (VAT, statement_name, etc.)
          setTransactions(prev => prev.map(t => t.id === updatedTransaction.id ? { ...t, ...updatedTransaction } : t))
          setSuccessMessage('Transaction updated')
          setTimeout(() => setSuccessMessage(''), 2000)
        }}
        onCategoryCreated={(newCategories) => setCategoriesList(newCategories)}
        onRefresh={refetchTransactions}
      />
    </div>
  )
}
