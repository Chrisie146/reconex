"use client"

import React, { useState } from "react"
import { apiFetch } from "@/lib/apiFetch"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function UploadInvoiceForm({ sessionId, onUploaded }: { sessionId: string | null, onUploaded?: () => void }) {
  const [fileObj, setFileObj] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [showReview, setShowReview] = useState(false)
  const [extractedMeta, setExtractedMeta] = useState<ExtractedMeta | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!sessionId) {
      alert('session_id is required in URL')
      return
    }
    if (!fileObj) {
      alert('Please select an invoice PDF to upload')
      return
    }

    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', fileObj)

      const j = await apiFetch(`${API_BASE}/invoice/upload_file_auto?session_id=${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        body: fd
      })
      if (j.success) {
        // show extracted metadata for review/edit
        if (j.extracted_meta) {
          setExtractedMeta({
            supplier_name: j.extracted_meta.supplier_name || '',
            invoice_date: j.extracted_meta.invoice_date ? String(j.extracted_meta.invoice_date) : '',
            invoice_number: j.extracted_meta.invoice_number || '',
            total_amount: j.extracted_meta.total_amount != null ? String(j.extracted_meta.total_amount) : '',
            vat_amount: j.extracted_meta.vat_amount != null ? String(j.extracted_meta.vat_amount) : '',
            file_reference: j.invoice?.file_reference || ''
          })
          setShowReview(true)
        } else {
          setFileObj(null)
          if (onUploaded) onUploaded()
        }
      }
    } catch (e) {
      console.error('Upload failed', e)
      alert('Upload failed: ' + String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
    <form className="bg-white p-4 rounded shadow-sm border border-blue-200" onSubmit={submit}>
      <div className="mb-2">
        <label className="block text-sm font-semibold mb-2">Upload Invoice PDF</label>
        <label className="block border-2 border-dashed border-gray-300 rounded p-6 text-center cursor-pointer hover:border-blue-400 transition">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFileObj(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
            className="hidden"
          />
          {fileObj ? (
            <div className="text-sm">
              <div className="text-lg">📄</div>
              <div className="font-medium">{fileObj.name}</div>
              <div className="text-xs text-gray-500">Ready to extract and match</div>
            </div>
          ) : (
            <div className="text-sm text-gray-600">
              <div className="text-lg mb-2">📥</div>
              <div className="font-medium">Drag and drop your invoice PDF here</div>
              <div className="text-xs text-gray-500 mt-1">or click to select a file</div>
            </div>
          )}
        </label>
      </div>
      <button
        className="w-full px-4 py-2 bg-blue-600 text-white rounded font-medium"
        type="submit"
        disabled={busy || !fileObj}
      >
        {busy ? 'Extracting and matching...' : 'Upload'}
      </button>
      <div className="mt-3 text-xs text-gray-600 bg-blue-50 p-2 rounded">
        ✨ Automatically extracts supplier, date, amount and matches to your transactions
      </div>
    </form>

    {/* Review / edit extracted metadata modal */}
    {showReview && extractedMeta && (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white p-4 rounded w-96">
          <h3 className="font-semibold mb-2">Review extracted invoice</h3>
          <div className="space-y-2 text-sm">
            <div>
              <label className="block text-xs">Supplier</label>
              <input className="w-full border p-1 rounded" value={extractedMeta.supplier_name} onChange={e => setExtractedMeta({...extractedMeta, supplier_name: e.target.value})} />
            </div>
            <div>
              <label className="block text-xs">Invoice date</label>
              <input className="w-full border p-1 rounded" value={extractedMeta.invoice_date} onChange={e => setExtractedMeta({...extractedMeta, invoice_date: e.target.value})} />
            </div>
            <div>
              <label className="block text-xs">Invoice number</label>
              <input className="w-full border p-1 rounded" value={extractedMeta.invoice_number} onChange={e => setExtractedMeta({...extractedMeta, invoice_number: e.target.value})} />
            </div>
            <div>
              <label className="block text-xs">Total amount</label>
              <input className="w-full border p-1 rounded" value={extractedMeta.total_amount} onChange={e => setExtractedMeta({...extractedMeta, total_amount: e.target.value})} />
            </div>
            <div>
              <label className="block text-xs">VAT amount</label>
              <input className="w-full border p-1 rounded" value={extractedMeta.vat_amount} onChange={e => setExtractedMeta({...extractedMeta, vat_amount: e.target.value})} />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={async () => {
              // POST corrected metadata to create/save invoice via API
              setBusy(true)
              try {
                const body = {
                  supplier_name: extractedMeta.supplier_name,
                  invoice_date: extractedMeta.invoice_date,
                  invoice_number: extractedMeta.invoice_number || undefined,
                  total_amount: extractedMeta.total_amount ? parseFloat(extractedMeta.total_amount) : undefined,
                  vat_amount: extractedMeta.vat_amount ? parseFloat(extractedMeta.vat_amount) : undefined,
                  file_reference: extractedMeta.file_reference || undefined
                }
                const j = await apiFetch(`${API_BASE}/invoice/upload?session_id=${encodeURIComponent(sessionId || '')}`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body)
                })
                if (j.success) {
                  setShowReview(false)
                  setFileObj(null)
                  if (onUploaded) onUploaded()
                }
              } catch (err) {
                alert('Save failed: ' + String(err))
              } finally {
                setBusy(false)
              }
            }}>Save</button>
            <button className="px-3 py-1 bg-gray-100 rounded border" onClick={() => { setShowReview(false); setFileObj(null) }}>Cancel</button>
          </div>
        </div>
      </div>
    )}
    </>
  )
}

type ExtractedMeta = { supplier_name: string, invoice_date: string, invoice_number: string, total_amount: string, vat_amount: string, file_reference?: string }
