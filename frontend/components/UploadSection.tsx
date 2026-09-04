'use client'

import { useState, useRef } from 'react'
import { FileUp, AlertCircle, Upload, FileText, Shield, Loader2 } from 'lucide-react'
import axios from '@/lib/axiosClient'
import UploadPreviewModal from './UploadPreviewModal'
import { posthog } from '@/lib/posthog'
import ColumnMappingModal from './ColumnMappingModal'
import { useClient } from '@/lib/clientContext'

import { API_BASE_URL } from '@/lib/apiBase'

interface UploadSectionProps {
  onUploadSuccess: (sessionId: string, count: number, categories: string[]) => void
}

export default function UploadSection({ onUploadSuccess }: UploadSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [fileName, setFileName] = useState<string>('')
  const [previewRows, setPreviewRows] = useState<any[] | null>(null)
  const [isPdfSelected, setIsPdfSelected] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [columnMappingOpen, setColumnMappingOpen] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const { currentClient } = useClient()

  const getUploadErrorHint = (errorMsg: string): string | null => {
    const e = errorMsg.toLowerCase()
    // Don't add a hint if the message already contains a suggestion
    if (e.includes('export') || e.includes('csv') || e.includes('online portal')) return null
    const isPdf = selectedFile?.name.toLowerCase().endsWith('.pdf') ?? false
    if (isPdf) return "Try exporting your statement as a CSV file from your bank's online portal instead."
    return null
  }

  const handleFileSelect = async (file: File) => {
    if (!file) return

    const isCSV = file.name.toLowerCase().endsWith('.csv')
    const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    if (!isCSV && !isPDF) {
      setError('Please upload a CSV or PDF bank statement')
      return
    }

    const maxSize = isPDF ? 10 * 1024 * 1024 : 5 * 1024 * 1024
    if (file.size > maxSize) {
      setError(`File is too large. Maximum size: ${isPDF ? '10MB' : '5MB'}`)
      return
    }

    setLoading(true)
    setError('')
    setFileName(file.name)
    setSelectedFile(file)

    try {
      const formData = new FormData()
      formData.append('file', file)

      let params = 'preview=true'
      if (currentClient?.id) {
        params += `&client_id=${currentClient.id}`
      }

      const endpoint = isPDF ? `${API_BASE_URL}/upload_pdf?${params}` : `${API_BASE_URL}/upload?${params}`
      const response = await axios.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      const data = response.data
      if (data && data.preview && Array.isArray(data.transactions)) {
        setPreviewRows(data.transactions)
        setIsPdfSelected(isPDF)
        setPreviewOpen(true)
      } else {
        const finalParams = currentClient?.id ? `client_id=${currentClient.id}` : ''
        const saveEndpoint = isPDF ? `${API_BASE_URL}/upload_pdf?${finalParams}` : `${API_BASE_URL}/upload?${finalParams}`
        const resp2 = await axios.post(saveEndpoint, formData)
        const { session_id, transaction_count, categories, warnings } = resp2.data
        if (warnings) console.warn('Upload warnings:', warnings)
        posthog.capture('file_uploaded', {
          file_type: isPDF ? 'pdf' : 'csv',
          transaction_count,
        })
        onUploadSuccess(session_id, transaction_count, categories)
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed'
      const isCSV = file.name.toLowerCase().endsWith('.csv')
      const isDetectionFailure = errorMessage.toLowerCase().includes('column') ||
        errorMessage.toLowerCase().includes('no valid transactions') ||
        errorMessage.toLowerCase().includes('could not identify') ||
        errorMessage.toLowerCase().includes('invalid csv') ||
        errorMessage.toLowerCase().includes('unsupported bank') ||
        errorMessage.toLowerCase().includes('no transaction data') ||
        errorMessage.toLowerCase().includes('could not read this pdf') ||
        errorMessage.toLowerCase().includes('scanned image') ||
        errorMessage.toLowerCase().includes('no text could be extracted')
      if ((isCSV || isPDF) && isDetectionFailure) {
        setError('')
        setColumnMappingOpen(true)
      } else {
        posthog.capture('file_upload_failed', { file_type: isPDF ? 'pdf' : 'csv', error: errorMessage })
        setError(errorMessage)
        setFileName('')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const supportedBanks = [
    'Standard Bank', 'ABSA', 'FNB', 'Capitec',
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Client Warning */}
      {!currentClient && (
        <div className="flex items-start gap-3 rounded-xl bg-amber-50 ring-1 ring-amber-200 px-4 py-3">
          <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-amber-800">
            Please select or create a client before uploading statements.
          </p>
        </div>
      )}

      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-200
          ${dragActive
            ? 'border-blue-400 bg-blue-50/60 ring-4 ring-blue-100'
            : 'border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 hover:border-neutral-400 dark:hover:border-neutral-600 hover:bg-neutral-100/60 dark:hover:bg-neutral-800/60'}
        `}
      >
        {/* Icon */}
        <div className="flex justify-center mb-5">
          <div className={`
            rounded-xl p-3.5 transition-colors duration-200
            ${dragActive ? 'bg-blue-100' : 'bg-white dark:bg-neutral-800 ring-1 ring-neutral-200 dark:ring-neutral-600 shadow-sm'}
          `}>
            <Upload className={`w-7 h-7 ${dragActive ? 'text-blue-600' : 'text-neutral-700 dark:text-neutral-300'}`} />
          </div>
        </div>

        {/* Heading */}
        <p className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400 mb-2">
          Upload Statement
        </p>
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mb-1">
          {dragActive ? 'Drop your file here' : 'Upload Bank Statement'}
        </h2>
        <p className="text-sm text-neutral-500 mb-6">
          Drag and drop your CSV or PDF bank statement, or click to browse
        </p>

        {/* Upload Button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || !currentClient}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <FileUp className="w-4 h-4" />
              Select File
            </>
          )}
        </button>

        <input
          ref={fileInputRef}
          id="file-upload"
          name="file"
          type="file"
          accept=".csv,.pdf,application/pdf"
          onChange={(e) => handleFileSelect(e.target.files?.[0]!)}
          className="hidden"
          disabled={loading}
        />

        {/* Supported Banks */}
        <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400 mb-3">
            Supported Banks
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {supportedBanks.map((bank) => (
              <span
                key={bank}
                className="inline-flex items-center gap-1.5 rounded-full bg-white dark:bg-neutral-800 px-3 py-1 text-xs font-medium text-neutral-600 dark:text-neutral-300 ring-1 ring-neutral-200 dark:ring-neutral-600"
              >
                <Shield className="w-3 h-3 text-blue-500" />
                {bank}
              </span>
            ))}
          </div>

        </div>

        {/* File Size Note */}
        <div className="mt-4 flex items-center justify-center gap-1.5 text-xs text-neutral-400">
          <FileText className="w-3.5 h-3.5" />
          <span>Max file size: CSV 5MB, PDF 10MB</span>
        </div>
      </div>

      {/* Preview + Column Mapping Modals */}
      <UploadPreviewModal
        isOpen={previewOpen}
        parsed={previewRows || []}
        isPdf={isPdfSelected}
        file={selectedFile}
        onClose={() => setPreviewOpen(false)}
        onManualMapping={isPdfSelected ? () => {
          setPreviewOpen(false)
          setColumnMappingOpen(true)
        } : undefined}
        onSaved={(sessionId, count, categories) => {
          setPreviewOpen(false)
          onUploadSuccess(sessionId, count, categories)
          setFileName('')
        }}
      />

      <ColumnMappingModal
        isOpen={columnMappingOpen}
        file={selectedFile}
        onClose={() => {
          setColumnMappingOpen(false)
          setFileName('')
        }}
        onSaved={(sessionId, count, categories) => {
          setColumnMappingOpen(false)
          onUploadSuccess(sessionId, count, categories)
          setFileName('')
        }}
      />

      {/* Status: File Selected */}
      {fileName && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-blue-50 ring-1 ring-blue-200 px-4 py-3">
          <div className="flex items-start gap-3">
          <FileUp className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-blue-800">
            Selected: <span className="font-medium">{fileName}</span>
          </p>
          </div>
          {!loading && !previewOpen && !columnMappingOpen && selectedFile && (
            <button
              type="button"
              onClick={() => setColumnMappingOpen(true)}
              className="shrink-0 text-xs font-medium text-blue-700 underline underline-offset-2 hover:text-blue-900"
            >
              Map columns manually
            </button>
          )}
        </div>
      )}

      {/* Status: Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl bg-red-50 ring-1 ring-red-200 px-4 py-3">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-800">
              <span className="font-medium">Error:</span> {error}
            </p>
            {getUploadErrorHint(error) && (
              <p className="text-sm text-red-700 mt-1.5">
                <span className="font-medium">Tip:</span> {getUploadErrorHint(error)}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
