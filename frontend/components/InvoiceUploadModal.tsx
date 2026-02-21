'use client'

import { useState, useRef } from 'react'
import { X, Upload, AlertCircle, CheckCircle, FileUp, Loader2, Calendar, Receipt } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface InvoiceUploadModalProps {
  isOpen: boolean
  onClose: () => void
  transaction: { id: number; date: string; description: string; amount: number; session_id?: string } | null
  sessionId: string
  onUploadSuccess: (message: string, invoice: any) => void
}

export default function InvoiceUploadModal({ isOpen, onClose, transaction, sessionId, onUploadSuccess }: InvoiceUploadModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [fileName, setFileName] = useState('')
  const [progress, setProgress] = useState(0)
  const [dragOver, setDragOver] = useState(false)

  if (!isOpen || !transaction) return null

  const handleFileSelect = async (file: File) => {
    if (!file) return
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file'); return
    }
    if (file.size > 20 * 1024 * 1024) {
      setError('File is too large. Maximum size: 20 MB'); return
    }

    setLoading(true); setError(''); setFileName(file.name); setProgress(0); setSuccess(false)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await axios.post(
        `${API_BASE_URL}/invoice/upload_file_direct`,
        formData,
        {
          params: { session_id: transaction.session_id || sessionId, transaction_id: transaction.id },
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: p => setProgress(Math.round((p.loaded * 100) / (p.total || 1))),
        }
      )
      if (response.data.success) {
        setSuccess(true)
        onUploadSuccess('Invoice uploaded and linked to transaction', response.data.invoice)
        setTimeout(() => { onClose(); setFileName(''); setProgress(0); setSuccess(false) }, 2000)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload invoice.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl ring-1 ring-neutral-200 overflow-hidden" onClick={e => e.stopPropagation()}>

        {/* ── Header ───────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-100">
              <Upload className="w-4 h-4 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-neutral-900">Upload Invoice</h2>
              <p className="text-[11px] text-neutral-500 truncate max-w-[240px]">{transaction.description}</p>
            </div>
          </div>
          <button onClick={onClose} disabled={loading}
            className="rounded-lg p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Body ─────────────────────────────────────────────── */}
        <div className="px-6 py-5 space-y-4">
          {/* Transaction details */}
          <div className="rounded-xl bg-neutral-50 border border-neutral-100 px-4 py-3 grid grid-cols-2 gap-2">
            <div>
              <p className="text-[11px] text-neutral-400 mb-0.5 flex items-center gap-1"><Calendar className="w-3 h-3" /> Date</p>
              <p className="text-sm font-medium text-neutral-700">{new Date(transaction.date).toLocaleDateString('en-ZA')}</p>
            </div>
            <div className="text-right">
              <p className="text-[11px] text-neutral-400 mb-0.5 flex items-center justify-end gap-1"><Receipt className="w-3 h-3" /> Amount</p>
              <p className="text-sm font-bold text-neutral-800">R {Math.abs(transaction.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</p>
            </div>
          </div>

          {/* Upload / Success */}
          {!success ? (
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]) }}
              onClick={() => !loading && fileInputRef.current?.click()}
              className={`rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
                loading ? 'border-neutral-200 bg-neutral-50 cursor-wait'
                : dragOver ? 'border-indigo-400 bg-indigo-50/50'
                : fileName ? 'border-emerald-300 bg-emerald-50/30'
                : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50/50'
              }`}
            >
              <div className={`mx-auto mb-3 flex items-center justify-center w-10 h-10 rounded-xl ${
                fileName ? 'bg-emerald-100' : 'bg-indigo-50'
              }`}>
                {loading ? <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
                  : fileName ? <FileUp className="w-5 h-5 text-emerald-600" />
                  : <Upload className="w-5 h-5 text-indigo-500" />}
              </div>
              <p className="text-sm font-medium text-neutral-700">
                {fileName || 'Drop PDF here or click to select'}
              </p>
              <p className="text-[11px] text-neutral-400 mt-0.5">PDF only, up to 20 MB</p>

              {loading && progress > 0 && (
                <div className="mt-4 h-1.5 w-full rounded-full bg-neutral-200 overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${progress}%` }} />
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                disabled={loading}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFileSelect(f) }}
              />
            </div>
          ) : (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 py-6 text-center">
              <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-sm font-semibold text-emerald-700">Invoice uploaded successfully</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-medium text-red-700">Upload failed</p>
                <p className="text-[11px] text-red-600 mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ───────────────────────────────────────────── */}
        <div className="flex justify-end px-6 py-4 border-t border-neutral-100 bg-neutral-50/50">
          <button onClick={onClose} disabled={loading}
            className="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-40">
            {success ? 'Done' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  )
}
