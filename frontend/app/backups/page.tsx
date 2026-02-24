'use client'

import React, { useState, useEffect } from 'react'
import { Download, HardDrive, CheckCircle2, XCircle, Clock } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface BackupRecord {
  id: number
  label: string
  status: 'completed' | 'failed'
  file_size_bytes: number | null
  error_message: string | null
  created_at: string
}

const fmtBytes = (b: number | null) => {
  if (b == null) return '—'
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const fmtDate = (d: string) =>
  new Date(d).toLocaleString('en-ZA', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })

export default function BackupsPage() {
  const [history, setHistory]         = useState<BackupRecord[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const res = await axios.get(`${API_BASE_URL}/backups/history`)
      setHistory(res.data.backups || [])
    } catch {
      toast.error('Failed to load backup history.')
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const token = typeof window !== 'undefined'
        ? localStorage.getItem('statement_analyzer_auth_token') : null

      const response = await fetch(`${API_BASE_URL}/backups/download`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Backup failed')
      }

      // Extract filename from Content-Disposition header or build one
      const disposition = response.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="?([^"]+)"?/)
      const filename = match?.[1] ?? `reconex_backup_${Date.now()}.sql.gz`

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)

      toast.success('Backup downloaded successfully.')
      fetchHistory() // Refresh history to show new entry
    } catch (err: any) {
      toast.error(err.message || 'Backup download failed.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <main className="bg-white min-h-screen">
      <Sidebar sessionId={null} />

      <div className="ml-64 transition-all duration-300">
        <Header />

        <div className="max-w-4xl mx-auto px-6 py-12">
          {/* Page header */}
          <div className="flex items-center gap-3 mb-2">
            <HardDrive className="text-blue-600" size={32} />
            <h1 className="text-3xl font-bold text-neutral-900">Backups</h1>
          </div>
          <p className="text-neutral-500 mb-10">
            Download a full database backup at any time. The backup is streamed directly to your browser — no file is stored on the server.
          </p>

          {/* Download card */}
          <div className="bg-gradient-to-br from-blue-50 to-blue-50 border border-blue-200 rounded-xl p-6 mb-10 flex items-start justify-between gap-6">
            <div>
              <h2 className="text-lg font-semibold text-neutral-900 mb-1">Full Database Backup</h2>
              <p className="text-sm text-neutral-600 mb-1">
                Exports the complete database in compressed SQL format (<code className="bg-white px-1 rounded text-xs">.sql.gz</code>).
              </p>
              <p className="text-sm text-neutral-500">
                Includes all clients, transactions, sessions, invoices, categories, rules, and reconciliation records.
              </p>
            </div>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="shrink-0 flex items-center gap-2 px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm font-medium"
            >
              <Download size={18} />
              {downloading ? 'Preparing...' : 'Download Backup'}
            </button>
          </div>

          {/* History */}
          <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-neutral-100">
              <h3 className="font-semibold text-neutral-900">Download History</h3>
            </div>

            {loadingHistory ? (
              <div className="text-center py-10 text-neutral-500">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-3" />
                Loading history...
              </div>
            ) : history.length === 0 ? (
              <div className="text-center py-10">
                <Clock size={36} className="mx-auto mb-3 text-neutral-300" />
                <p className="text-neutral-500">No backups downloaded yet.</p>
                <p className="text-neutral-400 text-sm mt-1">Each download will be recorded here.</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 border-b border-neutral-100">
                  <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                    <th className="px-6 py-3">Label</th>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Size</th>
                    <th className="px-6 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {history.map(rec => (
                    <tr key={rec.id} className="hover:bg-neutral-50">
                      <td className="px-6 py-3 text-neutral-900 font-medium">{rec.label}</td>
                      <td className="px-6 py-3 text-neutral-600">{fmtDate(rec.created_at)}</td>
                      <td className="px-6 py-3 text-neutral-500">{fmtBytes(rec.file_size_bytes)}</td>
                      <td className="px-6 py-3">
                        {rec.status === 'completed' ? (
                          <span className="inline-flex items-center gap-1.5 text-emerald-600">
                            <CheckCircle2 size={14} />
                            Completed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-red-500" title={rec.error_message ?? undefined}>
                            <XCircle size={14} />
                            Failed
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Notes */}
          <div className="mt-6 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
            <p className="text-xs text-neutral-500 leading-relaxed">
              <strong className="text-neutral-700">Note:</strong> Backups are streamed directly to your browser and not stored on the server.
              Store the downloaded file in a secure location. For automated offsite backups, use the CLI scripts at{' '}
              <code className="bg-white px-1 rounded text-[11px]">backup_database.py</code> which support S3, Azure Blob Storage, and Google Cloud Storage.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
