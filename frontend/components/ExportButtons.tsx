'use client'

import { useState } from 'react'
import { Download, FileText } from 'lucide-react'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ExportButtonsProps {
  sessionId: string | null
  currentClient?: Client | null
}

export default function ExportButtons({ sessionId, currentClient }: ExportButtonsProps) {
  const [exporting, setExporting] = useState(false)
  const [exportType, setExportType] = useState<string | null>(null)

  const handleExport = async (type: 'transactions' | 'summary') => {
    setExporting(true)
    setExportType(type)

    try {
      const endpoint = `${API_BASE_URL}/export/${type}`
      // Use client_id if currentClient selected, otherwise use sessionId
      const params: any = {}
      if (sessionId) {
        params.session_id = sessionId
      } else if (currentClient?.id) {
        params.client_id = currentClient.id
      } else {
        alert('Please select a client or upload a statement')
        setExporting(false)
        return
      }

      const response = await axios.get(endpoint, {
        params,
        responseType: 'blob',
      })

      // Create download link
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `${type}_${sessionId?.substring(0, 8) || currentClient?.id || 'export'}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  const handleExportAccountant = async () => {
    setExporting(true)
    setExportType('accountant')
    try {
      const endpoint = `${API_BASE_URL}/export/accountant`
      const response = await axios.get(endpoint, {
        params: { session_id: sessionId },
        responseType: 'blob',
      })

      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `statement_report_${sessionId.substring(0, 8)}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  const handleExportCategories = async () => {
    setExporting(true)
    setExportType('categories')
    try {
      const endpoint = `${API_BASE_URL}/export/categories`
      const response = await axios.get(endpoint, {
        params: { session_id: sessionId },
        responseType: 'blob',
      })

      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `categories_${sessionId.substring(0, 8)}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-4">
        <Download className="w-5 h-5 text-neutral-700" />
        <h3 className="font-bold text-neutral-900">Export Data</h3>
      </div>

      <p className="text-sm text-neutral-600 mb-4">
        Download your analyzed data in Excel format. Files are formatted for accounting software and spreadsheets.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          onClick={() => handleExport('transactions')}
          disabled={exporting && exportType === 'transactions'}
          className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <FileText className="w-4 h-4" />
          {exporting && exportType === 'transactions' ? 'Exporting...' : 'Export Transactions'}
        </button>

        <button
          onClick={() => handleExport('summary')}
          disabled={exporting && exportType === 'summary'}
          className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <FileText className="w-4 h-4" />
          {exporting && exportType === 'summary' ? 'Exporting...' : 'Export Summary'}
        </button>

        <button
          onClick={handleExportCategories}
          disabled={exporting && exportType === 'categories'}
          className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <FileText className="w-4 h-4" />
          {exporting && exportType === 'categories' ? 'Exporting...' : 'Export Categories'}
        </button>

        <button
          onClick={handleExportAccountant}
          disabled={exporting && exportType === 'accountant'}
          className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50 bg-green-600 hover:bg-green-700"
        >
          <FileText className="w-4 h-4" />
          {exporting && exportType === 'accountant' ? 'Exporting...' : 'For Accountant'}
        </button>
      </div>

      <div className="mt-4 p-3 bg-neutral-50 rounded-md text-xs text-neutral-600">
        <p className="font-medium mb-1">What you get:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Transactions:</strong> All transactions with dates, descriptions, amounts, and categories</li>
          <li><strong>Summary:</strong> Monthly totals and category breakdown across all months</li>
          <li><strong>Categories:</strong> One sheet per category with monthly sections, opening balances and running balances</li>
          <li><strong>For Accountant:</strong> Executive summary, merchant analysis, and detailed transactions with merchant data</li>
        </ul>
      </div>
    </div>
  )
}
