'use client'

import { X, Loader2, AlertCircle, CheckCircle, AlertTriangle, Plus, Pencil, Tag, Store, Sparkles, Copy, Save, Layers } from 'lucide-react'
import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'
import AccountSelector from './AccountSelector'

import { API_BASE_URL } from '@/lib/apiBase'

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
  invoice_id?: number | null
  account_id?: number | null
  account_code?: string | null
  account_name?: string | null
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
  const [accountId, setAccountId] = useState<number | null>(null)
  const [merchant, setMerchant] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showCreateCategory, setShowCreateCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [createError, setCreateError] = useState('')
  const [appliedRules, setAppliedRules] = useState<any[]>([])
  const [keyword, setKeyword] = useState('')
  const [applyMerchantSimilar, setApplyMerchantSimilar] = useState(false)
  const [applyCategorySimilar, setApplyCategorySimilar] = useState(false)
  const [rememberMappingRule, setRememberMappingRule] = useState(true)
  const [description, setDescription] = useState('')
  const [editingDescription, setEditingDescription] = useState(false)

  // Smart keyword extractor for SA bank transaction descriptions
  const extractSmartKeyword = (description: string): string => {
    if (!description) return ''
    let desc = description.toUpperCase().trim()

    // Strip common SA bank transaction prefixes (order matters — longest first)
    const prefixes = [
      /^POS PURCHASE\s+/,
      /^CARD PURCHASE\s+/,
      /^CARD PAYMENT\s+/,
      /^INTERNET PURCHASE\s+/,
      /^INTERNET PAYMENT\s+(?:TO\s+)?/,
      /^INTERNET TRANSFER\s+(?:TO\s+)?/,
      /^ONLINE PAYMENT\s+(?:TO\s+)?/,
      /^ONLINE TRANSFER\s+(?:TO\s+)?/,
      /^RECURRING PAYMENT\s+/,
      /^DIRECT DEBIT\s+/,
      /^DEBIT ORDER\s+/,
      /^ACB DEBIT\s+/,
      /^ACB\s+/,
      /^NAEDO\s+/,
      /^EFT PAYMENT\s+(?:TO\s+)?/,
      /^EFT\s+/,
      /^ATM CASH WITHDRAWAL\s+/,
      /^ATM WITHDRAWAL\s+/,
      /^CASH DEPOSIT\s+/,
      /^CASH WITHDRAWAL\s+/,
      /^PAYMENT TO\s+/,
      /^PAYMENT\s+/,
      /^TRANSFER TO\s+/,
      /^TRANSFER FROM\s+/,
      /^TRANSFER\s+/,
      /^PAYSHAP\s+(?:CREDIT|DEBIT)?\s*/,
      /^DISCOVERY BANK\s+/,
      /^STANDARD BANK\s+/,
      /^CAPITEC\s+/,
      /^NEDBANK\s+/,
      /^ABSA\s+/,
      /^FNB\s+/,
    ]
    for (const p of prefixes) {
      const stripped = desc.replace(p, '')
      if (stripped !== desc) { desc = stripped.trim(); break }
    }

    // Words too generic to be a useful keyword
    const tooGeneric = new Set([
      'THE','A','AN','TO','FROM','FOR','AT','IN','OF','AND','OR','BY','WITH',
      'DEPOSIT','PAYMENT','TRANSFER','PURCHASE','WITHDRAWAL','CASH','CASHBACK',
      'CARD','BANK','ACCOUNT','MONTHLY','ANNUAL','FEE','FEES','CHARGE','CHARGES',
      'SERVICE','DEBIT','CREDIT','ORDER','BALANCE','TRANSACTION',
      'REFERENCE','REF','NO','NUM','NUMBER',
      'INTERNET','MOBILE','ONLINE','APP','WEB',
      'BUY','SALE','STORE','SHOP','MARKET','CENTRE','CENTER','MALL',
      'ATM','EFT','ACB','NAEDO','RTC','ZA','SA',
      'SALARY','WAGES','INCOME','PAY','PAYROLL',
      'INSURANCE','PREMIUM','RENEWAL','LEVY','LEVIES',
      'DIRECT','AUTO','AUTOMATIC','RECURRING',
      'POS','SWIPE','TAP','CONTACTLESS',
      'STD','GEN','GENERAL','MISC','MISCELLANEOUS',
    ])

    const words = desc.split(/\s+/).filter(w => w.length > 0)
    const candidates: string[] = []

    for (const word of words) {
      if (/^\d+$/.test(word)) break          // stop at store/ref number
      if (word.startsWith('#')) break         // stop at #CODE
      if (word.includes('*')) break           // stop at S2S*MERCHANT codes
      if (/^\d{2}\/\d{2}/.test(word)) break  // stop at date-like tokens

      // Remove punctuation, keep letters; handle DOMAIN.COM → just domain
      const cleaned = word.replace(/[^A-Z]/g, '')
      if (cleaned.length < 3) continue
      if (tooGeneric.has(cleaned)) continue

      candidates.push(cleaned)
      // One strong word (5+ chars) is ideal — specific enough on its own
      if (cleaned.length >= 5) break
      // Two short words combined (e.g. PICK + PAY) form a safe enough keyword
      if (candidates.length >= 2) break
    }

    if (candidates.length === 0) return ''
    // Always prefer a single word if it's 5+ chars
    if (candidates[0].length >= 5) return candidates[0]
    // Combine two short words for specificity (e.g. "PICK PAY")
    return candidates.join(' ')
  }

  /** @deprecated use extractSmartKeyword */
  const extractKeyword = extractSmartKeyword

  // Sync state when transaction changes
  useEffect(() => {
    if (transaction) {
      setCategory(transaction.category || '')
      setAccountId(transaction.account_id ?? null)
      setMerchant(transaction.merchant || '')
      setDescription(cleanDescription(transaction.description))
      setEditingDescription(false)
      setError(null)
      setSuccess(null)
      setShowCreateCategory(false)
      setNewCategoryName('')
      const smartKw = extractSmartKeyword(transaction.description)
      setKeyword(smartKw)
      setApplyMerchantSimilar(false)
      setApplyCategorySimilar(false)
      setRememberMappingRule(true)
    }
  }, [transaction, isOpen])

  // Resolve the effective session_id: prefer the transaction's own session_id, fall back to prop
  const effectiveSessionId = transaction?.session_id || sessionId

  const handleApplyMerchantSimilar = async () => {
    if (!transaction) return

    const trimmedMerchant = (merchant || '').trim()
    const trimmedKeyword = (keyword || '').trim()

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

      await axios.post(
        `${API_BASE_URL}/merchant-rules/learn`,
        { keyword: trimmedKeyword, merchant: trimmedMerchant, auto_apply: true, enabled: true },
        clientId ? { params: { client_id: clientId } } : {}
      )

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
    const trimmedKeyword = (keyword || '').trim()

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

  const createManualMappingRule = async () => {
    const trimmedKeyword = keyword.trim()
    const trimmedCategory = category.trim()

    if (!clientId || trimmedKeyword.length < 3 || (!trimmedCategory && accountId == null)) {
      return null
    }

    const ruleNameTarget = trimmedCategory || transaction?.account_name || 'Account'
    const response = await axios.post(
      `${API_BASE_URL}/rules`,
      {
        name: `${trimmedKeyword} -> ${ruleNameTarget}`,
        enabled: true,
        priority: 100,
        conditions: {
          match_type: 'any',
          conditions: [
            { field: 'description', op: 'contains', value: trimmedKeyword },
          ],
        },
        action: {
          type: 'set_category',
          category: trimmedCategory || null,
          account_id: accountId,
        },
        auto_apply: true,
      },
      { params: { client_id: clientId } }
    )

    return response.data?.id ?? null
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
      const accountChanged = accountId !== (transaction.account_id ?? null)
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
              learn_rule: false
            }
          }
        )
        // The API response includes recalculated VAT fields
        apiResponseData = response.data
      }

      if (accountChanged) {
        const acctResponse = await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}/account`,
          { account_id: accountId },
          { params: { session_id: effectiveSessionId } }
        )
        if (!apiResponseData) apiResponseData = acctResponse.data
      }

      if (merchant !== (transaction.merchant || '')) {
        await axios.put(
          `${API_BASE_URL}/transactions/${transaction.id}/merchant`,
          { merchant: merchant || null },
          { params: { session_id: effectiveSessionId } }
        )
      }

      let createdRuleId: number | null = null
      if (rememberMappingRule && keyword.trim().length >= 3 && (category.trim() || accountId != null)) {
        createdRuleId = await createManualMappingRule()
      }

      if (applyCategorySimilar && createdRuleId) {
        await axios.post(
          `${API_BASE_URL}/rules/${createdRuleId}/apply`,
          { session_id: effectiveSessionId }
        )
        setApplyCategorySimilar(false)
        onRefresh?.()
      }

      setSuccess(createdRuleId ? 'Saved and added to Manual Rules' : 'Changes saved')
      setTimeout(() => setSuccess(null), 2000)

      // Merge API response (with VAT fields) with existing transaction data
      const updatedTxn: Transaction = {
        ...transaction,
        category,
        account_id: accountId,
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

  const descriptionChangedLocally = editingDescription && description !== cleanDescription(transaction.description)
  const hasChanges = category !== (transaction.category || '') || accountId !== (transaction.account_id ?? null) || merchant !== (transaction.merchant || '') || descriptionChangedLocally
  const canCreateRule = rememberMappingRule && keyword.trim().length >= 3 && (!!category.trim() || accountId != null)
  const ruleTargetSummary = [
    category.trim() ? category.trim() : null,
    accountId != null ? 'selected CoA account' : null,
  ].filter(Boolean).join(' + ')

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 z-40 flex h-full w-full max-w-[520px] flex-col bg-white shadow-2xl ring-1 ring-neutral-200 animate-in slide-in-from-right">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2">
              <Pencil className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">Transaction workspace</h2>
              <p className="text-xs text-neutral-500">Map, verify VAT, and apply similar changes.</p>
            </div>
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

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-white p-3 ring-1 ring-neutral-200">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-400">VAT breakdown</p>
              <div className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between gap-3">
                  <span className="text-neutral-500">Incl. VAT</span>
                  <span className="font-mono font-semibold text-neutral-900">
                    R{Math.abs(transaction.amount_incl_vat ?? transaction.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-neutral-500">Excl. VAT</span>
                  <span className="font-mono text-neutral-700">
                    {transaction.amount_excl_vat != null ? `R${Math.abs(transaction.amount_excl_vat).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}` : '-'}
                  </span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-neutral-500">VAT</span>
                  <span className="font-mono text-violet-700">
                    {transaction.vat_amount != null ? `R${Math.abs(transaction.vat_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}` : '-'}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-lg bg-white p-3 ring-1 ring-neutral-200">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-400">Evidence</p>
              <div className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between gap-3">
                  <span className="text-neutral-500">Invoice</span>
                  <span className={`font-semibold ${transaction.invoice_id ? 'text-blue-700' : 'text-neutral-400'}`}>
                    {transaction.invoice_id ? `Linked #${transaction.invoice_id}` : 'Not linked'}
                  </span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-neutral-500">Statement</span>
                  <span className="max-w-[160px] truncate text-neutral-700">{transaction.statement_name || transaction.session_id || 'Current'}</span>
                </div>
              </div>
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
          <div className="rounded-xl bg-white ring-1 ring-neutral-200 p-4 space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700 ring-1 ring-blue-100">
                1
              </div>
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">Map this transaction</h3>
                <p className="text-xs text-neutral-500">Choose a category, a Chart of Accounts account, or both.</p>
              </div>
            </div>

            {!showCreateCategory ? (
              <>
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Tag className="w-4 h-4 text-neutral-400" />
                      <label className="text-sm font-medium text-neutral-700">Category</label>
                    </div>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                    >
                      <option value="">No category</option>
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-neutral-400" />
                      <label className="text-sm font-medium text-neutral-700">Chart of Accounts account</label>
                    </div>
                    <AccountSelector
                      clientId={clientId ?? null}
                      value={accountId}
                      onChange={(id, _acct) => setAccountId(id)}
                      postableOnly
                      placeholder="No CoA account"
                    />
                  </div>
                </div>

                <button
                  onClick={() => setShowCreateCategory(true)}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Create new category
                </button>
              </>
            ) : (
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-neutral-700">New category name</label>
                  <input
                    type="text"
                    value={newCategoryName}
                    onChange={(e) => {
                      setNewCategoryName(e.target.value)
                      setCreateError('')
                    }}
                    placeholder="e.g., Subscriptions"
                    className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
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
          </div>

          <div className="rounded-xl bg-blue-50 ring-1 ring-blue-200 p-4 space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-semibold text-blue-700 ring-1 ring-blue-200">
                2
              </div>
              <div>
                <h3 className="text-sm font-semibold text-blue-950">Remember this mapping</h3>
                <p className="text-xs text-blue-700">Save a Manual Rule so future matching transactions are mapped the same way.</p>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-blue-950">Match keyword</label>
                {keyword.trim().length >= 5 ? (
                  <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200">Specific</span>
                ) : keyword.trim().length >= 3 ? (
                  <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-amber-200">Broad</span>
                ) : (
                  <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-blue-700 ring-1 ring-blue-200">Required for rules</span>
                )}
              </div>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-blue-700">Use the shortest text that reliably identifies this merchant or payment.</p>
            </div>

            <div className="space-y-3">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMappingRule}
                  onChange={(e) => {
                    setRememberMappingRule(e.target.checked)
                    if (!e.target.checked) setApplyCategorySimilar(false)
                  }}
                  className="mt-0.5 h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-medium text-blue-950">Save as Manual Rule</span>
                  <p className="text-xs text-blue-700 mt-0.5">The rule will appear under Manual Rules and run on future uploads.</p>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 ${canCreateRule ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'}`}>
                <input
                  type="checkbox"
                  checked={applyCategorySimilar}
                  onChange={(e) => setApplyCategorySimilar(e.target.checked)}
                  disabled={!canCreateRule}
                  className="mt-0.5 h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
                />
                <div>
                  <span className="text-sm font-medium text-blue-950">Also update matching rows in this statement</span>
                  <p className="text-xs text-blue-700 mt-0.5">
                    Requires a keyword of at least 3 characters and a category or CoA account.
                  </p>
                </div>
              </label>
            </div>

            <div className="rounded-lg bg-white/80 px-3 py-2 text-xs text-blue-900 ring-1 ring-blue-100">
              {canCreateRule ? (
                <>Rule preview: when description contains <span className="font-semibold">{keyword.trim()}</span>, map to <span className="font-semibold">{ruleTargetSummary}</span>.</>
              ) : (
                <>Choose a mapping and enter a keyword to save a Manual Rule.</>
              )}
            </div>
          </div>

          <div className="rounded-xl bg-white ring-1 ring-neutral-200 p-4 space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-neutral-50 text-sm font-semibold text-neutral-700 ring-1 ring-neutral-200">
                3
              </div>
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">Merchant is optional</h3>
                <p className="text-xs text-neutral-500">Use this only when you want vendor-level reporting.</p>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <Store className="w-4 h-4 text-neutral-400" />
                <label className="text-sm font-medium text-neutral-700">Merchant</label>
              </div>
              <input
                type="text"
                value={merchant}
                onChange={(e) => setMerchant(e.target.value)}
                placeholder="e.g., Shell, Spar, FNB"
                className="w-full rounded-lg bg-white px-3 py-2.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
              />
            </div>

            <label className="flex items-start gap-2.5 cursor-pointer rounded-lg bg-neutral-50 p-3 ring-1 ring-neutral-200">
              <input
                type="checkbox"
                checked={applyMerchantSimilar}
                onChange={(e) => setApplyMerchantSimilar(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <span className="text-sm font-medium text-neutral-900">Also apply merchant to matching rows</span>
                <p className="text-xs text-neutral-500 mt-0.5">Uses the same keyword from the Manual Rule section.</p>
              </div>
            </label>

            {applyMerchantSimilar && (
              <button
                onClick={handleApplyMerchantSimilar}
                disabled={loading || (merchant || '').trim().length === 0 || keyword.trim().length < 3}
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
                    Apply Merchant to Matching Rows
                  </>
                )}
              </button>
            )}
          </div>

          {false && (<>{!showCreateCategory ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-neutral-400" />
                <label className="text-sm font-semibold text-neutral-700">Category</label>
              </div>

              <select
                value={category}
                onChange={(e) => {
                  const newCat = e.target.value
                  setCategory(newCat)
                  if (newCat && newCat !== (transaction?.category || '')) {
                    setApplyCategorySimilar(true)
                  } else {
                    setApplyCategorySimilar(false)
                  }
                }}
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

              {/* Combined: Learn Rule + Apply to Similar (shown when category changes) */}
              {category && category !== (transaction?.category || '') && (
                <div className="rounded-xl bg-blue-50 ring-1 ring-blue-200 p-3 space-y-3">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.405A4.975 4.975 0 0112 17a4.975 4.975 0 01-2.09-.455l-.347-.405z" />
                    </svg>
                    <div>
                      <span className="text-sm font-medium text-blue-900">Learn &amp; apply this rule</span>
                      <p className="text-xs text-blue-700 mt-0.5">
                        One keyword — used for learning, applying to similar, and merchant matching below.
                      </p>
                    </div>
                  </div>

                  {/* Single shared keyword input */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-semibold uppercase tracking-widest text-blue-600">Keyword</label>
                      {keyword.trim().length >= 5 ? (
                        <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-full px-2 py-0.5">Specific ✓</span>
                      ) : keyword.trim().length >= 3 ? (
                        <span className="text-[10px] font-medium text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">May match broadly</span>
                      ) : (
                        <span className="text-[10px] font-medium text-neutral-500 bg-neutral-100 ring-1 ring-neutral-200 rounded-full px-2 py-0.5">Optional</span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={keyword}
                      onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                      placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                      className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-blue-600">Leave blank to use the full description for learning.</p>
                  </div>

                  {/* Apply to similar checkbox */}
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={applyCategorySimilar}
                      onChange={(e) => setApplyCategorySimilar(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-blue-900">Apply category to similar now</span>
                      <p className="text-xs text-blue-700 mt-0.5">
                        {keyword.trim().length >= 3
                          ? <>Updates transactions containing <span className="font-semibold">{keyword}</span> in this statement</>
                          : 'Updates matching transactions in this statement'
                        }
                      </p>
                    </div>
                  </label>

                  {applyCategorySimilar && (
                    <button
                      onClick={handleApplyCategorySimilar}
                      disabled={loading || (category || '').trim().length === 0 || keyword.trim().length < 3}
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
                          Apply Category to All Matching
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
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

          {/* ─── Account Section (Phase 2: Chart of Accounts) ─── */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4 5h16a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V7a2 2 0 012-2z" />
              </svg>
              <label className="text-sm font-semibold text-neutral-700">Account (CoA)</label>
            </div>
            <AccountSelector
              clientId={clientId ?? null}
              value={accountId}
              onChange={(id, _acct) => setAccountId(id)}
              postableOnly
              placeholder="Select account..."
            />
            <p className="text-xs text-neutral-500">
              Assign a Chart of Accounts account for financial reporting.
            </p>
          </div>

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
                    Apply merchant to similar
                  </span>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    Update matching transactions and save a learned rule
                  </p>
                </div>
              </label>

              {applyMerchantSimilar && (
                <div className="ml-6 space-y-2">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400">Keyword</label>
                      {keyword.trim().length >= 5 ? (
                        <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-full px-2 py-0.5">Specific ✓</span>
                      ) : keyword.trim().length >= 3 ? (
                        <span className="text-[10px] font-medium text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">May match broadly</span>
                      ) : null}
                    </div>
                    <input
                      type="text"
                      value={keyword}
                      onChange={(e) => setKeyword(e.target.value.toUpperCase())}
                      placeholder="e.g., WOOLWORTHS, NETFLIX, UBER"
                      className="w-full rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-neutral-500">
                      Only transactions containing this keyword will be updated.
                    </p>
                  </div>
                  <button
                    onClick={handleApplyMerchantSimilar}
                    disabled={loading || (merchant || '').trim().length === 0 || keyword.trim().length < 3}
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
          </>)}

          {/* No Changes Hint */}
          {!hasChanges && !canCreateRule && (
            <div className="flex items-center gap-2.5 rounded-xl bg-neutral-50 ring-1 ring-neutral-200 px-4 py-3">
              <Sparkles className="w-4 h-4 text-neutral-400 flex-shrink-0" />
              <p className="text-sm text-neutral-500">No changes made</p>
            </div>
          )}
          {!hasChanges && canCreateRule && (
            <div className="flex items-center gap-2.5 rounded-xl bg-blue-50 ring-1 ring-blue-200 px-4 py-3">
              <Sparkles className="w-4 h-4 text-blue-500 flex-shrink-0" />
              <p className="text-sm text-blue-800">Ready to save a Manual Rule</p>
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
            disabled={loading || (!hasChanges && !canCreateRule)}
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
