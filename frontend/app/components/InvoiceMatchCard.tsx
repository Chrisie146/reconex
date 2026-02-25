"use client"

import React, { useState } from "react"
import { apiFetch } from "@/lib/apiFetch"
import { toast } from 'sonner'
import {
  Check, X, ArrowRight, Download, Calendar, Receipt,
  Loader2, FileText, ShieldCheck, ShieldClose, Clock
} from 'lucide-react'

import { API_BASE_URL as API_BASE } from '@/lib/apiBase'

/* ── Types ─────────────────────────────────────────────────────── */

type Invoice = {
  id: number
  supplier_name: string
  invoice_date: string
  invoice_number?: string
  total_amount: number
  vat_amount?: number | null
  file_reference?: string | null
}

type Transaction = {
  id: number
  date: string
  description: string
  amount: number
}

type Props = {
  invoice: Invoice
  suggested?: {
    transaction?: Transaction
    confidence?: number
    classification?: string
    explanation?: string
    status?: string
  }
  sessionId: string | null
  onUpdate?: () => void
}

/* ── Component ─────────────────────────────────────────────────── */

export default function InvoiceMatchCard({ invoice, suggested, sessionId, onUpdate }: Props) {
  const [busy, setBusy] = useState(false)

  const postConfirm = async (confirm: boolean) => {
    if (!sessionId) return
    setBusy(true)
    try {
      const body: any = { invoice_id: invoice.id, confirm }
      if (suggested?.transaction) body.transaction_id = suggested.transaction.id
      const result = await apiFetch(
        `${API_BASE}/invoice/match/confirm?session_id=${encodeURIComponent(sessionId)}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      )
      if (result.success) {
        toast.success(confirm ? 'Match confirmed' : 'Match rejected')
        onUpdate?.()
      }
    } catch (e) {
      toast.error('Action failed: ' + String(e))
    } finally {
      setBusy(false)
    }
  }

  const isConfirmed = suggested?.status === 'confirmed'
  const isRejected  = suggested?.status === 'rejected'
  const isSuggested = suggested?.status === 'suggested'
  const confidence   = suggested?.confidence ?? 0

  const confColor = confidence >= 80 ? 'bg-emerald-500' : confidence >= 50 ? 'bg-amber-500' : 'bg-red-400'
  const confBg    = confidence >= 80 ? 'bg-emerald-50'  : confidence >= 50 ? 'bg-amber-50'  : 'bg-red-50'
  const confText  = confidence >= 80 ? 'text-emerald-700' : confidence >= 50 ? 'text-amber-700' : 'text-red-600'

  return (
    <div className="px-5 py-4 hover:bg-neutral-50/50 transition-colors">
      <div className="flex items-start gap-4">
        {/* Status indicator */}
        <div className={`mt-0.5 flex items-center justify-center w-8 h-8 rounded-lg shrink-0 ${
          isConfirmed ? 'bg-emerald-100' : isRejected ? 'bg-red-100' : isSuggested ? 'bg-amber-100' : 'bg-neutral-100'
        }`}>
          {isConfirmed ? <ShieldCheck className="w-4 h-4 text-emerald-600" />
            : isRejected ? <ShieldClose className="w-4 h-4 text-red-500" />
            : isSuggested ? <Clock className="w-4 h-4 text-amber-600" />
            : <FileText className="w-4 h-4 text-neutral-400" />}
        </div>

        {/* Invoice details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-neutral-800 truncate">{invoice.supplier_name}</p>
            {invoice.invoice_number && (
              <span className="rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-mono text-neutral-500">
                {invoice.invoice_number}
              </span>
            )}
            {isConfirmed && (
              <span className="rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                Confirmed
              </span>
            )}
            {isRejected && (
              <span className="rounded-full bg-red-100 text-red-700 border border-red-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                Rejected
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1 text-xs text-neutral-500">
            <span className="inline-flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {invoice.invoice_date}
            </span>
            <span className="inline-flex items-center gap-1">
              <Receipt className="w-3 h-3" />
              R {Math.abs(invoice.total_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
            </span>
            {invoice.vat_amount != null && invoice.vat_amount !== 0 && (
              <span className="text-neutral-400">
                VAT: R {Math.abs(invoice.vat_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </span>
            )}
          </div>

          {/* Match details */}
          {suggested?.transaction && (
            <div className="mt-2.5 flex items-start gap-3 rounded-lg bg-neutral-50 border border-neutral-100 px-3 py-2.5">
              <ArrowRight className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-neutral-700 truncate">
                  {suggested.transaction.description}
                </p>
                <p className="text-[11px] text-neutral-500">
                  {suggested.transaction.date} — R {Math.abs(suggested.transaction.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </p>
                {suggested.explanation && (
                  <p className="text-[11px] text-neutral-400 mt-1 italic">{suggested.explanation}</p>
                )}
              </div>
              {/* Confidence */}
              {confidence > 0 && (
                <div className="shrink-0 w-16 text-right">
                  <p className={`text-xs font-bold tabular-nums ${confText}`}>{confidence}%</p>
                  <div className={`mt-1 h-1.5 w-full rounded-full ${confBg}`}>
                    <div
                      className={`h-full rounded-full ${confColor} transition-all`}
                      style={{ width: `${confidence}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {!suggested && (
            <p className="mt-2 text-[11px] text-neutral-400 italic">
              No match found — run matching to find transactions
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          {invoice.file_reference && (
            <a
              href={`${API_BASE}/invoice/download?session_id=${encodeURIComponent(sessionId || '')}&invoice_id=${invoice.id}`}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-neutral-200 bg-white p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 transition-colors"
              title="Download PDF">
              <Download className="w-3.5 h-3.5" />
            </a>
          )}
          {isSuggested && suggested?.transaction && (
            <>
              <button
                onClick={() => postConfirm(true)}
                disabled={busy}
                className="rounded-lg bg-emerald-600 p-2 text-white hover:bg-emerald-700 disabled:opacity-40 transition-colors"
                title="Confirm match">
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => postConfirm(false)}
                disabled={busy}
                className="rounded-lg border border-red-200 bg-red-50 p-2 text-red-600 hover:bg-red-100 disabled:opacity-40 transition-colors"
                title="Reject match">
                <X className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
