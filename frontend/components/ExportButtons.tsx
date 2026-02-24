'use client'

import { useState } from 'react'
import { Download, FileText, BarChart3, FolderOpen, Briefcase, Loader2, Info, FileDown, FileSpreadsheet } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ExportButtonsProps {
  sessionId: string | null
  currentClient?: Client | null
}

type FormatType = 'excel' | 'pdf' | 'csv'

const EXPORTS = [
  { key: 'transactions', label: 'Transactions', desc: 'All transactions with dates, descriptions, amounts and categories', icon: FileText, accent: 'indigo', formats: ['excel', 'pdf', 'csv'] as FormatType[] },
  { key: 'summary',      label: 'Summary',      desc: 'Monthly totals and category breakdown across all months',              icon: BarChart3, accent: 'violet', formats: ['excel', 'pdf', 'csv'] as FormatType[] },
  { key: 'categories',   label: 'Categories',    desc: 'One sheet per category with monthly sections and running balances',    icon: FolderOpen, accent: 'sky', formats: ['excel', 'pdf'] as FormatType[] },
  { key: 'accountant',   label: 'For Accountant', desc: 'Executive summary, merchant analysis and detailed transactions',      icon: Briefcase, accent: 'emerald', formats: ['excel'] as FormatType[] },
] as const

type ExportKey = typeof EXPORTS[number]['key']

const ACCENT: Record<string, { bg: string; text: string; ring: string; btn: string; btnHover: string }> = {
  indigo:  { bg: 'bg-blue-50',  text: 'text-blue-600',  ring: 'ring-blue-200',  btn: 'bg-blue-600',  btnHover: 'hover:bg-blue-700' },
  violet:  { bg: 'bg-violet-50',  text: 'text-violet-600',  ring: 'ring-violet-200',  btn: 'bg-violet-600',  btnHover: 'hover:bg-violet-700' },
  sky:     { bg: 'bg-sky-50',     text: 'text-sky-600',     ring: 'ring-sky-200',     btn: 'bg-sky-600',     btnHover: 'hover:bg-sky-700' },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600', ring: 'ring-emerald-200', btn: 'bg-emerald-600', btnHover: 'hover:bg-emerald-700' },
}

const FORMAT_META: Record<FormatType, { label: string; ext: string; mime: string; icon: typeof FileText }> = {
  excel: { label: 'Excel', ext: 'xlsx', mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', icon: FileSpreadsheet },
  pdf:   { label: 'PDF',   ext: 'pdf',  mime: 'application/pdf', icon: FileDown },
  csv:   { label: 'CSV',   ext: 'csv',  mime: 'text/csv', icon: FileText },
}

export default function ExportButtons({ sessionId, currentClient }: ExportButtonsProps) {
  const [activeKey, setActiveKey] = useState<string | null>(null)
  const [includeVAT, setIncludeVAT] = useState(true)

  /* ── generic blob download ─────────────────────────────────── */
  const download = async (key: ExportKey, format: FormatType = 'excel') => {
    const loadingKey = `${key}-${format}`
    setActiveKey(loadingKey)
    try {
      const params: any = {}
      if (currentClient?.id) { params.client_id = currentClient.id }
      else if (sessionId) { params.session_id = sessionId }
      else { toast.error('Please select a client or upload a statement'); return }

      // Add VAT flag for applicable exports
      if (includeVAT && ['transactions', 'summary', 'accountant', 'categories'].includes(key)) {
        params.include_vat = true
      }

      // Build the endpoint URL based on format
      let url: string
      if (format === 'pdf') {
        url = `${API_BASE_URL}/export/pdf/${key === 'accountant' ? 'summary' : key}`
      } else if (format === 'csv') {
        url = `${API_BASE_URL}/export/csv/${key}`
      } else {
        url = `${API_BASE_URL}/export/${key}`
      }

      const res = await axios.get(url, { params, responseType: 'blob' })
      const prefix = key === 'accountant' ? 'statement_report' : key
      const ext = FORMAT_META[format].ext
      const fn = `${prefix}_${sessionId?.substring(0, 8) || currentClient?.id || 'export'}.${ext}`
      const blobUrl = window.URL.createObjectURL(res.data)
      const a = document.createElement('a'); a.href = blobUrl; a.download = fn
      document.body.appendChild(a); a.click(); document.body.removeChild(a); window.URL.revokeObjectURL(blobUrl)
      toast.success(`${FORMAT_META[format].label} exported successfully`)
    } catch { toast.error('Export failed. Please try again.') }
    finally { setActiveKey(null) }
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-neutral-100">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100">
          <Download className="w-4 h-4 text-blue-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-neutral-900">Export Data</h3>
          <p className="text-[11px] text-neutral-500">Download analysed data in Excel, PDF or CSV format</p>
        </div>
        {/* VAT Toggle */}
        <label className="flex items-center gap-2 cursor-pointer select-none" title="Include VAT Amount and Excl. VAT columns in exports">
          <span className="text-[11px] font-medium text-neutral-600">Include VAT</span>
          <button
            type="button"
            role="switch"
            aria-checked={includeVAT}
            onClick={() => setIncludeVAT(!includeVAT)}
            className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
              includeVAT ? 'bg-blue-600' : 'bg-neutral-200'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm ring-0 transition-transform ${
                includeVAT ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </button>
        </label>
      </div>

      {/* Export cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-5">
        {EXPORTS.map(exp => {
          const Icon = exp.icon
          const a = ACCENT[exp.accent]
          return (
            <div key={exp.key}
              className="group relative flex flex-col items-start gap-2 rounded-xl border border-neutral-200 p-4 text-left transition-all hover:shadow-md hover:border-neutral-300">
              <div className={`flex items-center justify-center w-9 h-9 rounded-lg ${a.bg}`}>
                <Icon className={`w-4.5 h-4.5 ${a.text}`} />
              </div>
              <div>
                <p className="text-sm font-semibold text-neutral-800">{exp.label}</p>
                <p className="text-[11px] text-neutral-500 leading-relaxed mt-0.5">{exp.desc}</p>
              </div>
              {/* Format buttons */}
              <div className="flex items-center gap-1.5 mt-1">
                {exp.formats.map((fmt) => {
                  const loadingKey = `${exp.key}-${fmt}`
                  const busy = activeKey === loadingKey
                  const FmtIcon = FORMAT_META[fmt].icon
                  return (
                    <button
                      key={fmt}
                      onClick={() => download(exp.key, fmt)}
                      disabled={!!activeKey}
                      className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                        fmt === 'excel'
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                          : fmt === 'pdf'
                          ? 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100'
                          : 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100'
                      }`}
                    >
                      {busy ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <FmtIcon className="w-3 h-3" />
                      )}
                      {FORMAT_META[fmt].label}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Hint */}
      <div className="mx-5 mb-5 flex gap-2 rounded-lg bg-neutral-50 border border-neutral-100 px-3.5 py-2.5">
        <Info className="w-3.5 h-3.5 text-neutral-400 mt-0.5 shrink-0" />
        <p className="text-[11px] text-neutral-500 leading-relaxed">
          <span className="font-medium text-neutral-600">Excel</span> files are formatted for accounting software.{' '}
          <span className="font-medium text-neutral-600">PDF</span> reports are print-ready with branding.{' '}
          <span className="font-medium text-neutral-600">CSV</span> files are compatible with any spreadsheet tool.{' '}
          {includeVAT && <span className="font-medium text-blue-600">VAT columns will be included in exports.</span>}
        </p>
      </div>
    </div>
  )
}
