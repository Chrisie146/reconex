'use client'

import React, { useState } from 'react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { useClient } from '@/lib/clientContext'
import { posthog } from '@/lib/posthog'
import { X, Check, Loader2, FileText, AlertCircle, Plus, Trash2, ArrowUpRight, ArrowDownRight, Scale, ChevronDown, ChevronUp } from 'lucide-react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ParsedRow {
  date: string
  description: string
  amount: number | string
  _manual?: boolean
}

interface Props {
  isOpen: boolean
  onClose: () => void
  parsed: ParsedRow[]
  isPdf?: boolean
  file?: File | null
  onSaved?: (sessionId: string, count: number, categories: string[]) => void
}

export default function UploadPreviewModal({ isOpen, onClose, parsed, isPdf = false, file = null, onSaved }: Props) {
  const [rows, setRows] = useState<ParsedRow[]>(parsed || [])
  const [selected, setSelected] = useState<boolean[]>(parsed.map(() => true))
  const [saving, setSaving] = useState(false)
  const [openingBalance, setOpeningBalance] = useState('')
  const [closingBalance, setClosingBalance] = useState('')
  const [showBalanceCheck, setShowBalanceCheck] = useState(false)

  const { currentClient } = useClient()

  React.useEffect(() => {
    // Convert numeric amounts to strings for editing
    setRows((parsed || []).map(r => ({ ...r, amount: String(r.amount ?? 0) })))
    setSelected((parsed || []).map(() => true))
  }, [parsed])

  if (!isOpen) return null

  const toggleSelect = (idx: number) => {
    setSelected(prev => prev.map((v, i) => i === idx ? !v : v))
  }

  const toggleAll = () => {
    const allSelected = selected.every(Boolean)
    setSelected(selected.map(() => !allSelected))
  }

  const updateField = (idx: number, field: keyof ParsedRow, value: any) => {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r))
  }

  const addTransaction = () => {
    const today = new Date().toISOString().slice(0, 10)
    // Use the date of the last row as default, or today
    const defaultDate = rows.length > 0 ? rows[rows.length - 1].date : today
    const newRow: ParsedRow = { date: defaultDate, description: '', amount: '', _manual: true }
    setRows(prev => [...prev, newRow])
    setSelected(prev => [...prev, true])
    // Scroll to bottom after render
    setTimeout(() => {
      const tableContainer = document.querySelector('[data-preview-table]')
      if (tableContainer) tableContainer.scrollTop = tableContainer.scrollHeight
    }, 50)
  }

  const removeRow = (idx: number) => {
    setRows(prev => prev.filter((_, i) => i !== idx))
    setSelected(prev => prev.filter((_, i) => i !== idx))
  }

  const selectedCount = selected.filter(Boolean).length

  // ── Balance / reconciliation helpers ──
  const selectedAmounts = rows
    .filter((_, i) => selected[i])
    .map(r => parseFloat(String(r.amount)) || 0)

  const totalInflows = selectedAmounts.filter(a => a > 0).reduce((s, a) => s + a, 0)
  const totalOutflows = selectedAmounts.filter(a => a < 0).reduce((s, a) => s + a, 0)
  const netMovement = totalInflows + totalOutflows

  const openBal = parseFloat(openingBalance)
  const closeBal = parseFloat(closingBalance)
  const hasBalanceInputs = !isNaN(openBal) && !isNaN(closeBal) && openingBalance !== '' && closingBalance !== ''
  const expectedClosing = hasBalanceInputs ? openBal + netMovement : null
  const balanceDiff = hasBalanceInputs ? Math.abs(closeBal - expectedClosing!) : null
  const balanceMatches = hasBalanceInputs && balanceDiff! < 0.02 // within 1 cent tolerance

  const fmt = (n: number) =>
    n.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  const handleSave = async () => {
    const toSave = rows
      .filter((_, i) => selected[i])
      .map(({ _manual, amount, ...rest }) => ({
        ...rest,
        amount: parseFloat(String(amount)) || 0,
      }))

    if (toSave.length === 0) {
      toast.error('No rows selected to save')
      return
    }

    // Validate manually-added rows have required fields
    const invalid = toSave.find(r => !r.date || !r.description)
    if (invalid) {
      toast.error('All transactions must have a date and description')
      return
    }

    setSaving(true)
    try {
      let params = ''
      if (currentClient?.id) {
        params = `client_id=${currentClient.id}`
      }

      const query = params ? `?${params}` : ''
      const res = await axios.post(`${API_BASE_URL}/save_parsed${query}`, { transactions: toSave })
      posthog.capture('file_uploaded', {
        file_type: isPdf ? 'pdf' : 'csv',
        transaction_count: res.data.transaction_count,
      })
      onSaved?.(res.data.session_id, res.data.transaction_count, res.data.categories || [])
      onClose()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start md:items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="relative w-[90%] max-w-[940px] max-h-[90vh] flex flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-neutral-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900">Preview Parsed Transactions</h3>
              <p className="text-sm text-neutral-500">
                Review rows below. Uncheck rows to exclude, or edit fields directly.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded-lg p-2 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Selection Summary */}
        <div className="flex items-center justify-between border-b border-neutral-100 bg-neutral-50 px-6 py-2.5 shrink-0">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedCount === rows.length}
                onChange={toggleAll}
                className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-neutral-600">Select all</span>
            </label>
            <div className="h-4 w-px bg-neutral-300" />
            <button
              onClick={addTransaction}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200 transition-colors hover:bg-emerald-100"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Transaction
            </button>
          </div>
          <span className="text-xs text-neutral-500">
            {selectedCount} of {rows.length} rows selected
          </span>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto px-6 py-3 min-h-[200px]" data-preview-table>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="pb-2 pr-3 text-[11px] font-semibold uppercase tracking-widest text-neutral-400 w-12">Keep</th>
                <th className="pb-2 pr-3 text-[11px] font-semibold uppercase tracking-widest text-neutral-400 w-36">Date</th>
                <th className="pb-2 pr-3 text-[11px] font-semibold uppercase tracking-widest text-neutral-400">Description</th>
                <th className="pb-2 text-right text-[11px] font-semibold uppercase tracking-widest text-neutral-400 w-32">Amount</th>
                <th className="pb-2 text-center text-[11px] font-semibold uppercase tracking-widest text-neutral-400 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {rows.map((r, i) => (
                <tr
                  key={i}
                  className={`transition-colors ${r._manual ? 'bg-emerald-50/40' : ''} ${selected[i] ? '' : 'bg-neutral-50 opacity-50'}`}
                >
                  <td className="py-2 pr-3">
                    <div className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={selected[i]}
                        onChange={() => toggleSelect(i)}
                        className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                      />
                      {r._manual && (
                        <span className="inline-block rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 leading-tight">
                          NEW
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <input
                      className="w-full rounded-lg bg-neutral-50 px-2.5 py-1.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={r.date}
                      placeholder="YYYY-MM-DD"
                      onChange={(e) => updateField(i, 'date', e.target.value)}
                    />
                  </td>
                  <td className="py-2 pr-3">
                    <input
                      className="w-full rounded-lg bg-neutral-50 px-2.5 py-1.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={r.description}
                      placeholder="Transaction description"
                      onChange={(e) => updateField(i, 'description', e.target.value)}
                    />
                  </td>
                  <td className="py-2 pr-3">
                    <input
                      className="w-full rounded-lg bg-neutral-50 px-2.5 py-1.5 text-right text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={String(r.amount)}
                      placeholder="0.00"
                      onChange={(e) => updateField(i, 'amount', e.target.value)}
                    />
                  </td>
                  <td className="py-2 text-center">
                    {r._manual ? (
                      <button
                        onClick={() => removeRow(i)}
                        className="rounded p-1 text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-500"
                        title="Remove row"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {rows.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-neutral-400">
              <AlertCircle className="w-6 h-6 mb-2" />
              <p className="text-sm mb-3">No transactions were parsed from this file.</p>
              <button
                onClick={addTransaction}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 ring-1 ring-emerald-200 transition-colors hover:bg-emerald-100"
              >
                <Plus className="w-4 h-4" />
                Add Transaction Manually
              </button>
            </div>
          )}
        </div>

        {/* Balance Checker */}
        {rows.length > 0 && (
          <div className="border-t border-neutral-200 shrink-0">
            <button
              onClick={() => setShowBalanceCheck(v => !v)}
              className="flex w-full items-center justify-between px-6 py-2.5 text-xs font-semibold uppercase tracking-widest text-neutral-500 hover:bg-neutral-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Scale className="w-3.5 h-3.5" />
                Quick Balance Check
              </div>
              {showBalanceCheck ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showBalanceCheck && (
              <div className="px-6 pb-4 space-y-3">
                {/* Totals row */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg bg-emerald-50 px-3 py-2.5 ring-1 ring-emerald-100">
                    <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-emerald-600 mb-0.5">
                      <ArrowDownRight className="w-3 h-3" />
                      Total Inflows
                    </div>
                    <p className="text-sm font-semibold text-emerald-700">R {fmt(totalInflows)}</p>
                  </div>
                  <div className="rounded-lg bg-red-50 px-3 py-2.5 ring-1 ring-red-100">
                    <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-red-600 mb-0.5">
                      <ArrowUpRight className="w-3 h-3" />
                      Total Outflows
                    </div>
                    <p className="text-sm font-semibold text-red-700">R {fmt(Math.abs(totalOutflows))}</p>
                  </div>
                  <div className={`rounded-lg px-3 py-2.5 ring-1 ${
                    netMovement >= 0
                      ? 'bg-blue-50 ring-blue-100'
                      : 'bg-amber-50 ring-amber-100'
                  }`}>
                    <div className={`flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest mb-0.5 ${
                      netMovement >= 0 ? 'text-blue-600' : 'text-amber-600'
                    }`}>
                      <Scale className="w-3 h-3" />
                      Net Movement
                    </div>
                    <p className={`text-sm font-semibold ${
                      netMovement >= 0 ? 'text-blue-700' : 'text-amber-700'
                    }`}>
                      {netMovement >= 0 ? '+' : '-'}R {fmt(Math.abs(netMovement))}
                    </p>
                  </div>
                </div>

                {/* Opening / Closing balance inputs */}
                <div className="flex items-end gap-3">
                  <div className="flex-1">
                    <label className="block text-[10px] font-semibold uppercase tracking-widest text-neutral-500 mb-1">
                      Opening Balance (from statement)
                    </label>
                    <div className="relative">
                      <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-neutral-400">R</span>
                      <input
                        className="w-full rounded-lg bg-white pl-7 pr-3 py-1.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={openingBalance}
                        placeholder="0.00"
                        onChange={e => setOpeningBalance(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex-1">
                    <label className="block text-[10px] font-semibold uppercase tracking-widest text-neutral-500 mb-1">
                      Closing Balance (from statement)
                    </label>
                    <div className="relative">
                      <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-neutral-400">R</span>
                      <input
                        className="w-full rounded-lg bg-white pl-7 pr-3 py-1.5 text-sm text-neutral-900 ring-1 ring-neutral-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={closingBalance}
                        placeholder="0.00"
                        onChange={e => setClosingBalance(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex-1">
                    {hasBalanceInputs ? (
                      <div className={`rounded-lg px-3 py-1.5 text-center ring-1 ${
                        balanceMatches
                          ? 'bg-emerald-50 ring-emerald-200'
                          : 'bg-red-50 ring-red-200'
                      }`}>
                        <p className={`text-[10px] font-semibold uppercase tracking-widest mb-0.5 ${
                          balanceMatches ? 'text-emerald-600' : 'text-red-600'
                        }`}>
                          {balanceMatches ? '\u2713 Balanced' : '\u2717 Mismatch'}
                        </p>
                        <p className={`text-sm font-semibold ${
                          balanceMatches ? 'text-emerald-700' : 'text-red-700'
                        }`}>
                          {balanceMatches
                            ? `R ${fmt(closeBal)}`
                            : `Off by R ${fmt(balanceDiff!)}`}
                        </p>
                      </div>
                    ) : (
                      <p className="text-[11px] text-neutral-400 text-center py-2">
                        Enter both balances to verify
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-neutral-200 bg-neutral-50/60 px-6 py-3 rounded-b-2xl shrink-0">
          <p className="text-xs text-neutral-500">
            {selectedCount} transaction{selectedCount !== 1 ? 's' : ''} will be saved
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="rounded-lg px-4 py-2 text-sm font-medium text-neutral-700 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || selectedCount === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Save Selected
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
