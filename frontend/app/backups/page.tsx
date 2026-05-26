'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Download, HardDrive, CheckCircle2, XCircle, Clock, Upload, AlertTriangle } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

import { API_BASE_URL } from '@/lib/apiBase'

interface BackupRecord {
  id: number
  label: string
  status: 'completed' | 'failed'
  file_size_bytes: number | null
  error_message: string | null
  created_at: string
}

const fmtBytes = (b: number | null) => {
  if (b == null) return '-'
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

  // Restore state
  const [restoreFile, setRestoreFile]       = useState<File | null>(null)
  const [showConfirm, setShowConfirm]       = useState(false)
  const [restoring, setRestoring]           = useState(false)
  const fileInputRef                        = useRef<HTMLInputElement>(null)

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
      const filename = match?.[1] ?? `reconex_backup_${Date.now()}.gz`

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

  const handleRestoreConfirm = async () => {
    if (!restoreFile) return
    setShowConfirm(false)
    setRestoring(true)
    try {
      const token = typeof window !== 'undefined'
        ? localStorage.getItem('statement_analyzer_auth_token') : null

      const form = new FormData()
      form.append('file', restoreFile)

      const response = await fetch(
        `${API_BASE_URL}/backups/restore?confirm=true`,
        { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form }
      )

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Restore failed')
      }

      toast.success('Database restored. Refresh the page to see your data.')
      setRestoreFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err: any) {
      toast.error(err.message || 'Restore failed.')
    } finally {
      setRestoring(false)
    }
  }

  return (
    <main className="bg-white min-h-screen">
      <Sidebar sessionId={null} />

      <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
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
                Exports the complete database in compressed format (<code className="bg-white px-1 rounded text-xs">.bak.gz</code> for PostgreSQL,{' '}
                <code className="bg-white px-1 rounded text-xs">.db.gz</code> for SQLite).
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

          {/* Restore card */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-10">
            <div className="flex items-start gap-3 mb-4">
              <Upload className="text-amber-600 mt-0.5 shrink-0" size={22} />
              <div>
                <h2 className="text-lg font-semibold text-neutral-900 mb-1">Restore from Backup</h2>
                <p className="text-sm text-neutral-600">
                  Upload a <code className="bg-white px-1 rounded text-xs">.bak.gz</code> (PostgreSQL) or{' '}
                  <code className="bg-white px-1 rounded text-xs">.db.gz</code> (SQLite) backup file to restore
                  the database to that point in time.
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm text-amber-800 font-medium">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>This will permanently overwrite all current data.</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                ref={fileInputRef}
                type="file"
                accept=".gz"
                onChange={e => setRestoreFile(e.target.files?.[0] ?? null)}
                className="text-sm text-neutral-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:text-sm file:font-medium file:bg-white file:text-neutral-700 file:border file:border-neutral-300 hover:file:bg-neutral-50 cursor-pointer"
              />
              <button
                onClick={() => restoreFile && setShowConfirm(true)}
                disabled={!restoreFile || restoring}
                className="flex items-center gap-2 px-5 py-2.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium text-sm shadow-sm"
              >
                <Upload size={16} />
                {restoring ? 'Restoring…' : 'Restore'}
              </button>
              {restoreFile && (
                <span className="text-sm text-neutral-500 truncate max-w-xs">{restoreFile.name}</span>
              )}
            </div>
          </div>

          {/* Confirmation modal */}
          {showConfirm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
              <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
                <div className="flex items-center gap-3 mb-4">
                  <AlertTriangle className="text-red-500 shrink-0" size={28} />
                  <h3 className="text-xl font-bold text-neutral-900">Confirm Restore</h3>
                </div>
                <p className="text-neutral-700 mb-2">
                  You are about to restore from:
                </p>
                <p className="font-mono text-sm bg-neutral-100 rounded-lg px-4 py-2 mb-4 break-all text-neutral-800">
                  {restoreFile?.name}
                </p>
                <p className="text-red-600 font-semibold mb-6">
                  All current clients, transactions, sessions, rules, and settings will be permanently replaced.
                  This cannot be undone.
                </p>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowConfirm(false)}
                    className="px-5 py-2.5 rounded-lg border border-neutral-300 text-neutral-700 hover:bg-neutral-50 font-medium text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRestoreConfirm}
                    className="px-5 py-2.5 rounded-lg bg-red-600 text-white hover:bg-red-700 font-medium text-sm"
                  >
                    Yes, restore database
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* History */}
          <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">            <div className="px-6 py-4 border-b border-neutral-100">
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
