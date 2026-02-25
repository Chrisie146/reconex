'use client'

import React, { useState, useEffect, useCallback } from 'react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { useClient } from '@/lib/clientContext'
import { X, ArrowRight, Columns, AlertCircle, CheckCircle } from 'lucide-react'

import { API_BASE_URL } from '@/lib/apiBase'

interface ColumnMappingModalProps {
  isOpen: boolean
  file: File | null
  onClose: () => void
  onSaved: (sessionId: string, count: number, categories: string[]) => void
}

interface ColumnMapping {
  date: string
  description: string
  amount?: string
  debit?: string
  credit?: string
  balance?: string
  date_format?: string
}

const DATE_FORMATS = [
  { label: 'Auto-detect', value: '' },
  { label: 'DD/MM/YYYY (e.g. 25/01/2024)', value: '%d/%m/%Y' },
  { label: 'YYYY-MM-DD (e.g. 2024-01-25)', value: '%Y-%m-%d' },
  { label: 'YYYY/MM/DD (e.g. 2024/01/25)', value: '%Y/%m/%d' },
  { label: 'DD-MM-YYYY (e.g. 25-01-2024)', value: '%d-%m-%Y' },
  { label: 'YYYYMMDD (e.g. 20240125)', value: '%Y%m%d' },
  { label: 'DD Mon YYYY (e.g. 25 Jan 2024)', value: '%d %b %Y' },
]

export default function ColumnMappingModal({ isOpen, file, onClose, onSaved }: ColumnMappingModalProps) {
  const [headers, setHeaders] = useState<string[]>([])
  const [sampleRows, setSampleRows] = useState<string[][]>([])
  const [rowCount, setRowCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Mapping state
  const [dateCol, setDateCol] = useState('')
  const [descCol, setDescCol] = useState('')
  const [amountMode, setAmountMode] = useState<'single' | 'split'>('single')
  const [amountCol, setAmountCol] = useState('')
  const [debitCol, setDebitCol] = useState('')
  const [creditCol, setCreditCol] = useState('')
  const [balanceCol, setBalanceCol] = useState('')
  const [dateFormat, setDateFormat] = useState('')

  const { currentClient } = useClient()

  // Fetch preview when modal opens
  const fetchPreview = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await axios.post(`${API_BASE_URL}/column-mapping/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setHeaders(res.data.headers || [])
      setSampleRows(res.data.sample_rows || [])
      setRowCount(res.data.row_count || 0)

      // Auto-suggest columns based on header names
      autoSuggest(res.data.headers || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to read file')
    } finally {
      setLoading(false)
    }
  }, [file])

  // Reset all field selections when the file changes
  useEffect(() => {
    setDateCol('')
    setDescCol('')
    setAmountMode('single')
    setAmountCol('')
    setDebitCol('')
    setCreditCol('')
    setBalanceCol('')
    setDateFormat('')
    setError('')
  }, [file])

  useEffect(() => {
    if (isOpen && file) {
      fetchPreview()
    }
  }, [isOpen, file, fetchPreview])

  const autoSuggest = (hdrs: string[]) => {
    const lower = hdrs.map(h => h.toLowerCase())

    // Reset all first so stale selections don't linger
    setDateCol('')
    setDescCol('')
    setAmountMode('single')
    setAmountCol('')
    setDebitCol('')
    setCreditCol('')
    setBalanceCol('')

    // Date
    const dateIdx = lower.findIndex(h =>
      /\bdate\b/.test(h) || /\bdatum\b/.test(h) || /\bposting\b/.test(h)
    )
    if (dateIdx >= 0) setDateCol(hdrs[dateIdx])

    // Description / Reference
    const descIdx = lower.findIndex(h =>
      /\bdescription\b/.test(h) || /\bdetails?\b/.test(h) || /\bnarration\b/.test(h) ||
      /\bparticulars\b/.test(h) || /\bbeskrywing\b/.test(h) ||
      /\bref(erence)?\b/.test(h) || /\btransaction.*desc\b/.test(h)
    )
    if (descIdx >= 0) setDescCol(hdrs[descIdx])

    // Amount vs Debit/Credit
    const amtIdx = lower.findIndex(h => /\bamount\b/.test(h) || /\bbedrag\b/.test(h))
    const debitIdx = lower.findIndex(h => /\bdebit\b/.test(h) || /\bdebiet\b/.test(h))
    const creditIdx = lower.findIndex(h => /\bcredit\b/.test(h) || /\bkrediet\b/.test(h))

    if (debitIdx >= 0 && creditIdx >= 0) {
      setAmountMode('split')
      setDebitCol(hdrs[debitIdx])
      setCreditCol(hdrs[creditIdx])
    } else if (amtIdx >= 0) {
      setAmountMode('single')
      setAmountCol(hdrs[amtIdx])
    }

    // Balance (optional)
    const balIdx = lower.findIndex(h => /\bbalance\b/.test(h) || /\bsaldo\b/.test(h))
    if (balIdx >= 0) setBalanceCol(hdrs[balIdx])
  }

  const isValid = dateCol && descCol && (
    (amountMode === 'single' && amountCol) ||
    (amountMode === 'split' && (debitCol || creditCol))
  )

  const handleSubmit = async () => {
    if (!file || !isValid) return
    setSaving(true)
    setError('')

    const mapping: ColumnMapping = {
      date: dateCol,
      description: descCol,
    }
    if (amountMode === 'single') {
      mapping.amount = amountCol
    } else {
      if (debitCol) mapping.debit = debitCol
      if (creditCol) mapping.credit = creditCol
    }
    if (balanceCol) mapping.balance = balanceCol
    if (dateFormat) mapping.date_format = dateFormat

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('column_mapping', JSON.stringify(mapping))

      let params = ''
      if (currentClient?.id) {
        params += `client_id=${currentClient.id}`
      }

      const res = await axios.post(
        `${API_BASE_URL}/column-mapping/upload${params ? '?' + params : ''}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      const { session_id, transaction_count, skipped_count, categories } = res.data
      const skipMsg = skipped_count > 0 ? ` (${skipped_count} rows skipped – invalid dates)` : ''
      toast.success(`Uploaded ${transaction_count} transactions${skipMsg}`)
      onSaved(session_id, transaction_count, categories || [])
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Upload failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  const selectClass = 'w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <Columns className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-neutral-900">Map Your Columns</h2>
          </div>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-6">
          {/* Info banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
            We couldn&apos;t automatically detect the bank format. Please tell us which columns
            contain the <strong>date</strong>, <strong>description</strong>, and <strong>amount</strong>.
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-8 text-neutral-500">Loading file preview...</div>
          ) : (
            <>
              {/* Sample data table */}
              {headers.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-neutral-700 mb-2">
                    File Preview ({rowCount} rows)
                  </h3>
                  <div className="border rounded-lg overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-neutral-100">
                          {headers.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left font-medium text-neutral-700 whitespace-nowrap border-b">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sampleRows.slice(0, 5).map((row, ri) => (
                          <tr key={ri} className="border-b last:border-b-0">
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-3 py-1.5 text-neutral-600 whitespace-nowrap">
                                {cell || <span className="text-neutral-300">–</span>}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Column mapping form */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Date column */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Date Column <span className="text-red-500">*</span>
                  </label>
                  <select value={dateCol} onChange={e => setDateCol(e.target.value)} className={selectClass}>
                    <option value="">Select column...</option>
                    {headers.map((h, i) => (
                      <option key={i} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                {/* Description column */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Description Column <span className="text-red-500">*</span>
                  </label>
                  <select value={descCol} onChange={e => setDescCol(e.target.value)} className={selectClass}>
                    <option value="">Select column...</option>
                    {headers.map((h, i) => (
                      <option key={i} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                {/* Amount mode toggle */}
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Amount Type <span className="text-red-500">*</span>
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={amountMode === 'single'}
                        onChange={() => setAmountMode('single')}
                        className="accent-blue-600"
                      />
                      <span className="text-sm text-neutral-700">Single Amount column</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={amountMode === 'split'}
                        onChange={() => setAmountMode('split')}
                        className="accent-blue-600"
                      />
                      <span className="text-sm text-neutral-700">Separate Debit / Credit columns</span>
                    </label>
                  </div>
                </div>

                {amountMode === 'single' ? (
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">
                      Amount Column <span className="text-red-500">*</span>
                    </label>
                    <select value={amountCol} onChange={e => setAmountCol(e.target.value)} className={selectClass}>
                      <option value="">Select column...</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>{h}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Debit Column (expenses)
                      </label>
                      <select value={debitCol} onChange={e => setDebitCol(e.target.value)} className={selectClass}>
                        <option value="">Select column...</option>
                        {headers.map((h, i) => (
                          <option key={i} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Credit Column (income)
                      </label>
                      <select value={creditCol} onChange={e => setCreditCol(e.target.value)} className={selectClass}>
                        <option value="">Select column...</option>
                        {headers.map((h, i) => (
                          <option key={i} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>
                  </>
                )}

                {/* Date format */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Date Format
                  </label>
                  <select value={dateFormat} onChange={e => setDateFormat(e.target.value)} className={selectClass}>
                    {DATE_FORMATS.map((f, i) => (
                      <option key={i} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </div>

                {/* Balance column (optional) */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Balance Column <span className="text-neutral-400 font-normal">(optional)</span>
                  </label>
                  <select value={balanceCol} onChange={e => setBalanceCol(e.target.value)} className={selectClass}>
                    <option value="">None</option>
                    {headers.map((h, i) => (
                      <option key={i} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Validation status */}
              {isValid && (
                <div className="flex items-center gap-2 text-sm text-green-700">
                  <CheckCircle className="w-4 h-4" />
                  Mapping looks good! Ready to upload.
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-6 py-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValid || saving || loading}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Uploading...' : (
              <>
                Upload with Mapping
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
