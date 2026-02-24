"use client"

import React, { useState, useRef, useCallback } from "react"
import { apiFetch } from "@/lib/apiFetch"
import { toast } from 'sonner'
import {
  Upload, FileUp, X, Loader2, Sparkles, Building2, Calendar,
  Hash, DollarSign, Receipt, CheckCircle
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type ExtractedMeta = {
  supplier_name: string
  invoice_date: string
  invoice_number: string
  total_amount: string
  vat_amount: string
  file_reference?: string
}

export default function UploadInvoiceForm({ sessionId, onUploaded }: { sessionId: string | null; onUploaded?: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [fileObj, setFileObj] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showReview, setShowReview] = useState(false)
  const [extractedMeta, setExtractedMeta] = useState<ExtractedMeta | null>(null)

  /* ── helpers ───────────────────────────────────────────────────── */
  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return
    const file = files[0]
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      toast.error('Only PDF files are supported'); return
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error('File too large. Maximum 20 MB.'); return
    }
    setFileObj(file)
  }, [])

  const submit = async () => {
    if (!sessionId) { toast.error('No session selected'); return }
    if (!fileObj) { toast.error('Select an invoice PDF first'); return }
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', fileObj)
      const j = await apiFetch(
        `${API_BASE}/invoice/upload_file_auto?session_id=${encodeURIComponent(sessionId)}`,
        { method: 'POST', body: fd }
      )
      if (j.success && j.extracted_meta) {
        setExtractedMeta({
          supplier_name: j.extracted_meta.supplier_name || '',
          invoice_date: j.extracted_meta.invoice_date ? String(j.extracted_meta.invoice_date) : '',
          invoice_number: j.extracted_meta.invoice_number || '',
          total_amount: j.extracted_meta.total_amount != null ? String(j.extracted_meta.total_amount) : '',
          vat_amount: j.extracted_meta.vat_amount != null ? String(j.extracted_meta.vat_amount) : '',
          file_reference: j.invoice?.file_reference || '',
        })
        setShowReview(true)
      } else {
        toast.success('Invoice uploaded successfully')
        setFileObj(null)
        onUploaded?.()
      }
    } catch (e) {
      toast.error('Upload failed: ' + String(e))
    } finally {
      setBusy(false)
    }
  }

  const saveReview = async () => {
    if (!extractedMeta) return
    setBusy(true)
    try {
      const body = {
        supplier_name: extractedMeta.supplier_name,
        invoice_date: extractedMeta.invoice_date,
        invoice_number: extractedMeta.invoice_number || undefined,
        total_amount: extractedMeta.total_amount ? parseFloat(extractedMeta.total_amount) : undefined,
        vat_amount: extractedMeta.vat_amount ? parseFloat(extractedMeta.vat_amount) : undefined,
        file_reference: extractedMeta.file_reference || undefined,
      }
      const j = await apiFetch(
        `${API_BASE}/invoice/upload?session_id=${encodeURIComponent(sessionId || '')}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      )
      if (j.success) {
        toast.success('Invoice saved')
        setShowReview(false)
        setFileObj(null)
        onUploaded?.()
      }
    } catch (e) {
      toast.error('Save failed: ' + String(e))
    } finally {
      setBusy(false)
    }
  }

  /* ── review fields config ──────────────────────────────────────── */
  const FIELDS = [
    { key: 'supplier_name',  label: 'Supplier',       icon: Building2, type: 'text' },
    { key: 'invoice_date',   label: 'Invoice Date',   icon: Calendar,  type: 'date' },
    { key: 'invoice_number', label: 'Invoice Number',  icon: Hash,      type: 'text' },
    { key: 'total_amount',   label: 'Total Amount (R)', icon: DollarSign, type: 'text' },
    { key: 'vat_amount',     label: 'VAT Amount (R)',  icon: Receipt,   type: 'text' },
  ] as const

  /* ── render ────────────────────────────────────────────────────── */
  return (
    <>
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-3.5 border-b border-neutral-100">
          <Upload className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Upload Invoice</h3>
        </div>

        <div className="p-5">
          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
            onClick={() => !busy && fileInputRef.current?.click()}
            className={`relative rounded-xl border-2 border-dashed cursor-pointer transition-all ${
              dragOver ? 'border-blue-400 bg-blue-50/50'
              : fileObj ? 'border-emerald-300 bg-emerald-50/30'
              : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50/50'
            } px-6 py-8 text-center`}
          >
            {fileObj ? (
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-100">
                  <FileUp className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-neutral-800">{fileObj.name}</p>
                  <p className="text-[11px] text-neutral-400">{(fileObj.size / 1024).toFixed(0)} KB — Ready to extract</p>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); setFileObj(null) }}
                  className="mt-1 inline-flex items-center gap-1 text-[11px] text-neutral-400 hover:text-red-500 transition-colors">
                  <X className="w-3 h-3" /> Remove
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-50">
                  <Upload className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-700">Drop invoice PDF here or click to browse</p>
                  <p className="text-[11px] text-neutral-400 mt-0.5">PDF only, up to 20 MB</p>
                </div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={e => handleFiles(e.target.files)}
            />
          </div>

          {/* Upload button */}
          {fileObj && (
            <button
              onClick={submit}
              disabled={busy}
              className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {busy
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Extracting and matching...</>
                : <><Sparkles className="w-4 h-4" /> Upload and Auto-Extract</>}
            </button>
          )}

          <p className="mt-3 text-[11px] text-neutral-400 text-center">
            Automatically extracts supplier, date, amount and matches to your bank transactions
          </p>
        </div>
      </div>

      {/* ── Review extracted metadata modal ──────────────────────── */}
      {showReview && extractedMeta && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
          onClick={() => { setShowReview(false); setFileObj(null) }}>
          <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl ring-1 ring-neutral-200 overflow-hidden"
            onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-100">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-neutral-900">Review Extracted Data</h2>
                  <p className="text-[11px] text-neutral-500">Verify and correct before saving</p>
                </div>
              </div>
              <button
                onClick={() => { setShowReview(false); setFileObj(null) }}
                className="rounded-lg p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Fields */}
            <div className="px-6 py-5 space-y-3">
              {FIELDS.map(f => {
                const Icon = f.icon
                return (
                  <div key={f.key}>
                    <label className="flex items-center gap-1.5 text-[11px] font-semibold text-neutral-500 mb-1">
                      <Icon className="w-3 h-3" />
                      {f.label}
                    </label>
                    <input
                      type={f.type}
                      value={(extractedMeta as any)[f.key]}
                      onChange={e => setExtractedMeta({ ...extractedMeta, [f.key]: e.target.value })}
                      className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300"
                    />
                  </div>
                )
              })}
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2.5 px-6 py-4 border-t border-neutral-100 bg-neutral-50/50">
              <button
                onClick={() => { setShowReview(false); setFileObj(null) }}
                disabled={busy}
                className="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-40">
                Cancel
              </button>
              <button
                onClick={saveReview}
                disabled={busy}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-40 transition-colors">
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                {busy ? 'Saving...' : 'Save Invoice'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
