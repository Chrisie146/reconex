'use client'

import { useState, useRef } from 'react'
import { X, Upload, AlertCircle, CheckCircle } from 'lucide-react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface InvoiceUploadModalProps {
  isOpen: boolean
  onClose: () => void
  transaction: { id: number; date: string; description: string; amount: number } | null
  sessionId: string
  onUploadSuccess: (message: string, invoice: any) => void
}

export default function InvoiceUploadModal({
  isOpen,
  onClose,
  transaction,
  sessionId,
  onUploadSuccess,
}: InvoiceUploadModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState(false)
  const [fileName, setFileName] = useState<string>('')
  const [progress, setProgress] = useState(0)

  if (!isOpen || !transaction) return null

  const handleFileSelect = async (file: File) => {
    if (!file) return

    // Validate file type
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file')
      return
    }

    // Validate file size (max 20MB)
    if (file.size > 20 * 1024 * 1024) {
      setError('File is too large. Maximum size: 20MB')
      return
    }

    setLoading(true)
    setError('')
    setFileName(file.name)
    setProgress(0)
    setSuccess(false)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Upload invoice directly to this transaction
      const response = await axios.post(
        `${API_BASE_URL}/invoice/upload_file_direct`,
        formData,
        {
          params: { 
            session_id: sessionId,
            transaction_id: transaction.id
          },
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 1)
            )
            setProgress(percentCompleted)
          },
        }
      )

      if (response.data.success) {
        setSuccess(true)
        onUploadSuccess(`Invoice uploaded and linked to transaction`, response.data.invoice)
        setTimeout(() => {
          onClose()
          setFileName('')
          setProgress(0)
          setSuccess(false)
        }, 2000)
      }
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        'Failed to upload invoice. Please try again.'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-200">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Upload Invoice</h2>
            <p className="text-sm text-neutral-600 mt-1">
              Matched to: {transaction.description}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 rounded transition-colors"
            disabled={loading}
          >
            <X size={20} className="text-neutral-600" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Transaction Details */}
          <div className="bg-neutral-50 rounded-lg p-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-neutral-600">Transaction Date:</span>
              <span className="font-medium">
                {new Date(transaction.date).toLocaleDateString('en-ZA')}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-neutral-600">Amount:</span>
              <span className="font-medium">
                R{Math.abs(transaction.amount).toLocaleString('en-ZA', {
                  minimumFractionDigits: 2,
                })}
              </span>
            </div>
          </div>

          {/* Upload Area */}
          {!success ? (
            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                loading
                  ? 'border-neutral-300 bg-neutral-50'
                  : 'border-blue-300 bg-blue-50 hover:border-blue-400'
              }`}
            >
              <Upload className="mx-auto text-blue-600 mb-3" size={32} />
              <p className="text-sm font-medium text-neutral-900 mb-1">
                {fileName || 'Drop PDF here or click to select'}
              </p>
              <p className="text-xs text-neutral-600 mb-4">
                PDF files only, max 20MB
              </p>

              {/* Progress Bar */}
              {loading && progress > 0 && (
                <div className="w-full bg-neutral-200 rounded-full h-2 mb-4">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="inline-block px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:bg-neutral-400 transition-colors"
              >
                {loading ? 'Uploading...' : 'Select File'}
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    handleFileSelect(file)
                  }
                }}
                disabled={loading}
                className="hidden"
              />
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
              <CheckCircle className="mx-auto text-green-600 mb-2" size={32} />
              <p className="text-sm font-medium text-green-700">
                Invoice uploaded successfully!
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-3">
              <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={18} />
              <div>
                <p className="text-sm font-medium text-red-700">Upload failed</p>
                <p className="text-xs text-red-600 mt-1">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-neutral-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-neutral-700 bg-neutral-100 rounded hover:bg-neutral-200 disabled:bg-neutral-100 transition-colors text-sm font-medium"
          >
            {success ? 'Done' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  )
}
