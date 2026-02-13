'use client'

import { useEffect, useState } from 'react'
import { X, FileSpreadsheet, AlertCircle } from 'lucide-react'
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface VATExportModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
}

export default function VATExportModal({
  isOpen,
  onClose,
  sessionId
}: VATExportModalProps) {
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [useFullPeriod, setUseFullPeriod] = useState<boolean>(true)
  const [exportType, setExportType] = useState<'both' | 'input_only' | 'output_only'>('both')
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  
  // Transaction date range from session
  const [sessionDateFrom, setSessionDateFrom] = useState<string | null>(null)
  const [sessionDateTo, setSessionDateTo] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !sessionId) return

    const fetchSessionInfo = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/sessions`)
        const sessions = response.data.sessions || []
        const currentSession = sessions.find((s: any) => s.session_id === sessionId)
        
        if (currentSession) {
          setSessionDateFrom(currentSession.date_from)
          setSessionDateTo(currentSession.date_to)
          setDateFrom(currentSession.date_from || '')
          setDateTo(currentSession.date_to || '')
        }
      } catch (error) {
        console.error('Failed to fetch session info:', error)
      }
    }

    fetchSessionInfo()
  }, [isOpen, sessionId])

  useEffect(() => {
    // Reset to full period when checkbox is toggled
    if (useFullPeriod && sessionDateFrom && sessionDateTo) {
      setDateFrom(sessionDateFrom)
      setDateTo(sessionDateTo)
      setWarning(null)
    }
  }, [useFullPeriod, sessionDateFrom, sessionDateTo])

  useEffect(() => {
    // Validate date range when dates change
    if (!dateFrom || !dateTo || !sessionDateFrom || !sessionDateTo) {
      setWarning(null)
      return
    }

    const fromDate = new Date(dateFrom)
    const toDate = new Date(dateTo)
    const sessionFromDate = new Date(sessionDateFrom)
    const sessionToDate = new Date(sessionDateTo)

    if (fromDate < sessionFromDate || toDate > sessionToDate) {
      const actualFrom = fromDate < sessionFromDate ? sessionDateFrom : dateFrom
      const actualTo = toDate > sessionToDate ? sessionDateTo : dateTo
      setWarning(
        `Selected range extends beyond transaction dates. Export will include data from ${actualFrom} to ${actualTo}.`
      )
    } else {
      setWarning(null)
    }
  }, [dateFrom, dateTo, sessionDateFrom, sessionDateTo])

  const handleExport = async () => {
    if (!sessionId) return

    setExporting(true)
    setError(null)

    try {
      const params: any = {
        session_id: sessionId,
        format: 'excel',
        export_type: exportType
      }

      // Add date range if not using full period
      if (!useFullPeriod && dateFrom && dateTo) {
        params.date_from = dateFrom
        params.date_to = dateTo
      }

      const response = await axios.get(`${API_BASE_URL}/vat/export`, {
        params,
        responseType: 'blob',
      })

      // Generate filename based on export type and date range
      const dateRangeStr = dateFrom && dateTo ? `${dateFrom}_to_${dateTo}` : (sessionId?.substring(0, 8) || 'export')
      const typeStr = exportType === 'both' ? 'report' : exportType.replace('_', '_')
      const filename = `vat_${typeStr}_${dateRangeStr}.xlsx`

      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      onClose()
    } catch (error: any) {
      console.error('VAT export failed:', error)
      setError(error.response?.data?.detail || 'Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            <h2 className="text-xl font-bold text-neutral-900">Export VAT Report</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-neutral-600" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-5">
          {/* Date Range Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">📅</span>
              <h3 className="font-semibold text-neutral-900">Date Range</h3>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useFullPeriod}
                onChange={(e) => setUseFullPeriod(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-neutral-700">Use full statement period</span>
            </label>

            {!useFullPeriod && (
              <div className="grid grid-cols-2 gap-3 pl-6">
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-full text-sm px-3 py-2 border border-neutral-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {warning && (
              <div className="flex gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <AlertCircle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-yellow-800">{warning}</p>
              </div>
            )}
          </div>

          {/* Export Type Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">📊</span>
              <h3 className="font-semibold text-neutral-900">Export Type</h3>
            </div>

            <div className="space-y-2">
              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-neutral-50 transition-colors">
                <input
                  type="radio"
                  name="exportType"
                  value="both"
                  checked={exportType === 'both'}
                  onChange={(e) => setExportType('both')}
                  className="w-4 h-4 text-blue-600 mt-0.5 focus:ring-2 focus:ring-blue-500"
                />
                <div>
                  <div className="text-sm font-medium text-neutral-900">Both Input & Output</div>
                  <div className="text-xs text-neutral-600">Full report with Net VAT calculation</div>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-neutral-50 transition-colors">
                <input
                  type="radio"
                  name="exportType"
                  value="input_only"
                  checked={exportType === 'input_only'}
                  onChange={(e) => setExportType('input_only')}
                  className="w-4 h-4 text-blue-600 mt-0.5 focus:ring-2 focus:ring-blue-500"
                />
                <div>
                  <div className="text-sm font-medium text-neutral-900">VAT Input Only</div>
                  <div className="text-xs text-neutral-600">Expenses and claimable VAT</div>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-neutral-50 transition-colors">
                <input
                  type="radio"
                  name="exportType"
                  value="output_only"
                  checked={exportType === 'output_only'}
                  onChange={(e) => setExportType('output_only')}
                  className="w-4 h-4 text-blue-600 mt-0.5 focus:ring-2 focus:ring-blue-500"
                />
                <div>
                  <div className="text-sm font-medium text-neutral-900">VAT Output Only</div>
                  <div className="text-xs text-neutral-600">Sales/Income and payable VAT</div>
                </div>
              </label>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={exporting}
            className="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={exporting || !dateFrom || !dateTo}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {exporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <FileSpreadsheet className="w-4 h-4" />
                Export Report
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
