'use client'

import { useState, useRef } from 'react'
import { FileUp, AlertCircle, CheckCircle } from 'lucide-react'
import axios from '@/lib/axiosClient'
import UploadPreviewModal from './UploadPreviewModal'
import { useClient } from '@/lib/clientContext'
import LoadingButton from './LoadingButton'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

  const { currentClient } = useClient()

  const handleFileSelect = async (file: File) => {
    if (!file) return

    // Accept CSV or PDF
    const isCSV = file.name.toLowerCase().endsWith('.csv')
    const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    if (!isCSV && !isPDF) {
      setError('Please upload a CSV or PDF bank statement')
      return
    }

    // Validate file size (5MB for CSV, 10MB for PDF)
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

      // Build params with client_id if available
      let params = 'preview=true'
      if (currentClient?.id) {
        params += `&client_id=${currentClient.id}`
      }
      
      const endpoint = isPDF ? `${API_BASE_URL}/upload_pdf?${params}` : `${API_BASE_URL}/upload?${params}`
      // Request preview first
      const response = await axios.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      const data = response.data
      if (data && data.preview && Array.isArray(data.transactions)) {
        setPreviewRows(data.transactions)
        setIsPdfSelected(isPDF)
        setPreviewOpen(true)
      } else {
        // fallback: proceed with direct upload
        const finalParams = currentClient?.id ? `client_id=${currentClient.id}` : ''
        const saveEndpoint = isPDF ? `${API_BASE_URL}/upload_pdf?${finalParams}` : `${API_BASE_URL}/upload?${finalParams}`
        const resp2 = await axios.post(saveEndpoint, formData)
        const { session_id, transaction_count, categories, warnings } = resp2.data
        if (warnings) console.warn('Upload warnings:', warnings)
        onUploadSuccess(session_id, transaction_count, categories)
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed'
      setError(errorMessage)
      setFileName('')
    } finally {
      setLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  return (
    <div className="max-w-2xl mx-auto">
      {!currentClient && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-sm">
          ⚠️ Please select or create a client before uploading statements.
        </div>
      )}
      
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-neutral-300 rounded-lg p-12 text-center bg-neutral-50 hover:bg-neutral-100 transition-colors"
      >
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-white rounded-lg border border-neutral-200">
            <FileUp className="w-8 h-8 text-neutral-900" />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-neutral-900 mb-2">Upload Bank Statement</h2>
        <p className="text-neutral-600 mb-6">
          Drag and drop your CSV or PDF bank statement here or click to select
        </p>

        <div className="flex justify-center">
          <LoadingButton
            onClick={() => fileInputRef.current?.click()}
            loading={loading}
            loadingText="Processing..."
            variant="primary"
            disabled={loading || !currentClient}
          >
            Select File
          </LoadingButton>
        </div>

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

        <div className="mt-6 text-sm text-neutral-600">
          <p className="font-medium mb-2">Required columns (for CSV):</p>
          <ul className="list-disc list-inside space-y-1">
            <li><strong>Date</strong> - Transaction date (any common format)</li>
            <li><strong>Description</strong> - Transaction description</li>
            <li><strong>Amount/Debit/Credit</strong> - Transaction amount</li>
          </ul>
        </div>

        <div className="mt-6 text-xs text-neutral-500 flex justify-center items-center gap-1">
          📄 Max file size: CSV 5MB, PDF 10MB
        </div>
      </div>

      <UploadPreviewModal
        isOpen={previewOpen}
        parsed={previewRows || []}
        isPdf={isPdfSelected}
        file={selectedFile}
        onClose={() => setPreviewOpen(false)}
        onSaved={(sessionId, count, categories) => {
          setPreviewOpen(false)
          onUploadSuccess(sessionId, count, categories)
          setFileName('')
        }}
      />

      {/* Status Messages */}
      {fileName && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
          <FileUp className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            Selected: <strong>{fileName}</strong>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-red-900">
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}
    </div>
  )
}
