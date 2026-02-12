"use client"

import React, { useEffect, useState } from "react"
import { apiFetch } from "@/lib/apiFetch"
import InvoiceMatchCard from "./InvoiceMatchCard"
import UploadInvoiceForm from "./UploadInvoiceForm"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

type Invoice = {
  id: number
  supplier_name: string
  invoice_date: string
  invoice_number?: string
  total_amount: number
  file_reference?: string | null
}

export default function InvoiceReviewList({ sessionId }: { sessionId: string | null }) {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [matches, setMatches] = useState<Record<number, any>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    loadAll()
  }, [sessionId])

  async function runMatch() {
    if (!sessionId) return
    setLoading(true)
    try {
      await apiFetch(`${API_BASE}/invoice/match?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' })
      await loadMatches()
    } catch (e) {
      console.error('Match failed', e)
      alert('Match failed: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  async function loadInvoices() {
    if (!sessionId) return
    try {
      const j = await apiFetch(`${API_BASE}/invoices?session_id=${encodeURIComponent(sessionId)}`)
      setInvoices(j.invoices || [])
    } catch (e) {
      console.error('invoices fetch failed:', e)
      setInvoices([])
    }
  }

  async function loadMatches() {
    if (!sessionId) return
    try {
      const j = await apiFetch(`${API_BASE}/invoice/matches?session_id=${encodeURIComponent(sessionId)}`)
      const map: Record<number, any> = {}
      const arr = Array.isArray(j.matches) ? j.matches : []
      arr.forEach((m: any) => {
        map[m.invoice_id] = m
      })
      setMatches(map)
    } catch (e) {
      console.error('matches fetch failed:', e)
      setMatches({})
    }
  }

  async function loadAll() {
    setLoading(true)
    try {
      await loadInvoices()
      await loadMatches()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-1">
          <h2 className="text-lg font-semibold">Invoice Review</h2>
          <div className="text-xs text-gray-500">Upload invoices and review suggested matches. Matches are suggestions only.</div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 bg-indigo-600 text-white rounded" onClick={runMatch} disabled={loading || !sessionId}>Run matching</button>
          <button className="px-3 py-1 bg-gray-100 rounded border" onClick={loadAll} disabled={loading || !sessionId}>Refresh</button>
        </div>
      </div>

      <div className="mb-4">
        <UploadInvoiceForm sessionId={sessionId} onUploaded={loadAll} />
      </div>

      {/* Uploaded invoices list with download links */}
      {invoices.length > 0 && (
        <div className="mb-4 bg-white p-3 rounded border">
          <div className="text-sm font-semibold mb-2">Uploaded Invoices</div>
          <div className="space-y-2">
            {invoices.map(inv => (
              <div key={inv.id} className="flex items-center justify-between text-sm">
                <div className="text-sm">
                  <div className="font-medium">{inv.supplier_name}</div>
                  <div className="text-xs text-gray-500">{inv.invoice_date} • R{inv.total_amount.toFixed(2)}</div>
                </div>
                <div className="flex items-center gap-2">
                  {inv.file_reference ? (
                    <a className="px-2 py-1 bg-gray-100 rounded border text-xs" href={`${API_BASE}/invoice/download?session_id=${encodeURIComponent(sessionId || '')}&invoice_id=${inv.id}`} target="_blank" rel="noreferrer">Download PDF</a>
                  ) : (
                    <div className="text-xs text-gray-400">No file</div>
                  )}
                  <button className="px-2 py-1 bg-white border rounded text-xs" onClick={async () => { window.location.hash = `invoice-${inv.id}` }}>View</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && <div>Loading...</div>}

      {!loading && invoices.length === 0 && (
        <div className="text-sm text-gray-500">No invoices uploaded for this session.</div>
      )}

      <div className="grid grid-cols-1 gap-3">
        {invoices.map(inv => (
          <InvoiceMatchCard
            key={inv.id}
            invoice={inv}
            suggested={matches[inv.id] ? {
              transaction: matches[inv.id].transaction,
              confidence: matches[inv.id].confidence,
              classification: matches[inv.id].match_status === 'confirmed' ? 'High' : (matches[inv.id].confidence >= 80 ? 'High' : matches[inv.id].confidence >= 50 ? 'Medium' : 'Low'),
              explanation: matches[inv.id].explanation,
              status: matches[inv.id].match_status
            } : undefined}
            sessionId={sessionId}
            onUpdate={loadAll}
          />
        ))}
      </div>
    </div>
  )
}
