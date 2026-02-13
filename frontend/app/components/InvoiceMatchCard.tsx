"use client"

import React, { useState } from "react"
import { apiFetch } from "@/lib/apiFetch"
import ConfidenceBadge from "./ConfidenceBadge"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type Invoice = {
  id: number
  supplier_name: string
  invoice_date: string
  invoice_number?: string
  total_amount: number
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

export default function InvoiceMatchCard({ invoice, suggested, sessionId, onUpdate }: Props) {
  const [busy, setBusy] = useState(false)

  async function postConfirm(confirm: boolean) {
    if (!sessionId) return
    setBusy(true)
    try {
      const body: any = { invoice_id: invoice.id, confirm }
      if (suggested && suggested.transaction) body.transaction_id = suggested.transaction.id
      const result = await apiFetch(`${API_BASE}/invoice/match/confirm?session_id=${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (result.success) {
        // Always refresh the invoice list to show updated status
        if (onUpdate) onUpdate()
      } else {
        throw new Error('Confirmation failed')
      }
    } catch (e) {
      console.error('Confirm failed', e)
      alert('Confirm failed: ' + String(e))
    } finally {
      setBusy(false)
    }
  }

  const isConfirmed = suggested?.status === 'confirmed'
  const isRejected = suggested?.status === 'rejected'

  return (
    <div className={`border rounded-lg p-3 shadow-sm ${isConfirmed ? 'bg-green-50 border-green-200' : isRejected ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="text-sm font-semibold">{invoice.supplier_name}</div>
            <div className="text-xs text-gray-500">{invoice.invoice_number || ''}</div>
            {isConfirmed && <span className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs font-medium">✓ Confirmed</span>}
            {isRejected && <span className="px-2 py-1 bg-red-200 text-red-800 rounded text-xs font-medium">✗ Rejected</span>}
            <div className="ml-auto text-xs text-gray-500">{invoice.invoice_date} • R{invoice.total_amount.toFixed(2)}</div>
          </div>

          <div className="mt-2 text-sm text-gray-700">
            {suggested && suggested.transaction ? (
              <>
                <div className="text-sm font-medium">Suggested match:</div>
                <div className="text-xs text-gray-600">{suggested.transaction.date} • {suggested.transaction.description}</div>
                <div className="text-xs text-gray-600">Amount: R{suggested.transaction.amount.toFixed(2)}</div>
              </>
            ) : (
              <div className="text-sm text-gray-500">No suggested transaction</div>
            )}
          </div>

          {suggested && (
            <div className="mt-3 flex items-center gap-3">
              <ConfidenceBadge classification={suggested.classification || 'Low'} />
              <div className="text-xs text-gray-600">{suggested.explanation}</div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <button
            className={`px-3 py-1 rounded text-sm font-medium transition ${isConfirmed ? 'bg-green-600 text-white cursor-default' : 'bg-green-600 text-white hover:bg-green-700'}`}
            onClick={() => postConfirm(true)}
            disabled={busy || !suggested || !suggested.transaction || isConfirmed || isRejected}
            title={isConfirmed ? 'Already confirmed' : isRejected ? 'Cannot confirm rejected match' : ''}
          >
            ✔ {isConfirmed ? 'Confirmed' : 'Confirm'}
          </button>
          <button
            className={`px-3 py-1 rounded border text-sm font-medium transition ${isRejected ? 'bg-red-200 text-red-800 border-red-300 cursor-default' : 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100'}`}
            onClick={() => postConfirm(false)}
            disabled={busy || isConfirmed}
            title={isConfirmed ? 'Cannot reject confirmed match' : ''}
          >
            ✖ {isRejected ? 'Rejected' : 'Reject'}
          </button>
        </div>
      </div>
    </div>
  )
}
