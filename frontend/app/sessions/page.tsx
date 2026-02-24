"use client"

import React from 'react'
import Sidebar from '@/components/Sidebar'
import { Trash2, FileText, CheckCircle, AlertCircle, Loader2, Lock, Unlock, Eye, X, AlertTriangle } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'
import { useClient } from '@/lib/clientContext'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Page() {
  const [sessions, setSessions] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [deleteConfirm, setDeleteConfirm] = React.useState<{ sessionIds: string[]; count: number } | null>(null)
  const [deleting, setDeleting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState<string | null>(null)
  const [selectedSessions, setSelectedSessions] = React.useState<Set<string>>(new Set())
  const { currentClient } = useClient()

  React.useEffect(() => {
    loadSessions()
  }, [currentClient])

  async function loadSessions() {
    setLoading(true)
    try {
      let url = `${API_BASE}/sessions`
      if (currentClient?.id) {
        url += `?client_id=${currentClient.id}`
      }
      const data = await apiFetch(url)
      setSessions(data.sessions || [])
    } catch (e) {
      console.error('Failed to load sessions:', e)
      setSessions([])
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete() {
    if (!deleteConfirm) return

    setDeleting(true)
    setError(null)

    try {
      if (deleteConfirm.sessionIds.length === 1) {
        await apiFetch(`${API_BASE}/sessions/${deleteConfirm.sessionIds[0]}`, {
          method: 'DELETE',
        })
      } else {
        await apiFetch(`${API_BASE}/sessions/bulk-delete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_ids: deleteConfirm.sessionIds }),
        })
      }

      const count = deleteConfirm.sessionIds.length
      setSuccess(`${count} statement${count > 1 ? 's' : ''} deleted successfully`)
      setDeleteConfirm(null)
      setSelectedSessions(new Set())

      setTimeout(() => {
        loadSessions()
        setSuccess(null)
      }, 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete session(s)')
    } finally {
      setDeleting(false)
    }
  }

  function toggleSessionSelect(sessionId: string) {
    const newSelected = new Set(selectedSessions)
    if (newSelected.has(sessionId)) {
      newSelected.delete(sessionId)
    } else {
      newSelected.add(sessionId)
    }
    setSelectedSessions(newSelected)
  }

  function toggleSelectAll() {
    if (selectedSessions.size === sessions.length) {
      setSelectedSessions(new Set())
    } else {
      setSelectedSessions(new Set(sessions.map(s => s.session_id)))
    }
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <Sidebar sessionId={null} />

      <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
        <div className="mx-auto max-w-5xl px-6 py-8">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-neutral-400 mb-1">
                History
              </p>
              <h1 className="text-2xl font-semibold text-neutral-900">Previous Statements</h1>
            </div>
            {selectedSessions.size > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-neutral-600">
                  {selectedSessions.size} selected
                </span>
                <button
                  onClick={() => setDeleteConfirm({ sessionIds: Array.from(selectedSessions), count: selectedSessions.size })}
                  className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete {selectedSessions.size}
                </button>
              </div>
            )}
          </div>

          {/* Success Banner */}
          {success && (
            <div className="mb-5 flex items-start gap-3 rounded-xl bg-emerald-50 ring-1 ring-emerald-200 px-4 py-3">
              <CheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-emerald-800">{success}</p>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="mb-5 flex items-start gap-3 rounded-xl bg-red-50 ring-1 ring-red-200 px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="ml-3 text-sm text-neutral-500">Loading statements...</span>
            </div>
          ) : !currentClient ? (
            <div className="rounded-2xl bg-white ring-1 ring-neutral-200 shadow-sm p-12 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-100">
                <FileText className="w-6 h-6 text-neutral-400" />
              </div>
              <p className="text-sm text-neutral-500">Select a client in the sidebar to view their previous statements.</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="rounded-2xl bg-white dark:bg-neutral-900 ring-1 ring-neutral-200 dark:ring-neutral-700 shadow-sm p-12 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-100">
                <FileText className="w-6 h-6 text-neutral-400" />
              </div>
              <p className="text-sm font-medium text-neutral-700 mb-1">No statements found</p>
              <p className="text-sm text-neutral-500">No previous statements found for {currentClient.name}.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Select All Bar */}
              <div className="flex items-center gap-3 rounded-xl bg-white dark:bg-neutral-900 px-4 py-3 ring-1 ring-neutral-200 dark:ring-neutral-700 shadow-sm">
                <input
                  type="checkbox"
                  checked={selectedSessions.size === sessions.length && sessions.length > 0}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <span className="text-sm font-medium text-neutral-600">
                  Select all ({sessions.length})
                </span>
              </div>

              {/* Session Cards */}
              {sessions.map(s => (
                <div
                  key={s.session_id}
                  className={`
                    flex items-center gap-4 rounded-xl bg-white dark:bg-neutral-900 px-4 py-4 ring-1 shadow-sm transition-all
                    ${selectedSessions.has(s.session_id)
                      ? 'ring-blue-300 bg-blue-50/40 dark:bg-blue-950/40'
                      : 'ring-neutral-200 dark:ring-neutral-700 hover:ring-neutral-300 dark:hover:ring-neutral-600'}
                  `}
                >
                  <input
                    type="checkbox"
                    checked={selectedSessions.has(s.session_id)}
                    onChange={() => toggleSessionSelect(s.session_id)}
                    className="h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500 cursor-pointer flex-shrink-0"
                  />

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-neutral-900 truncate">{s.friendly_name}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {s.transaction_count} transactions &middot; {s.date_from || 'n/a'} &rarr; {s.date_to || 'n/a'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {s.locked ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700 ring-1 ring-red-200">
                        <Lock className="w-3 h-3" />
                        Locked
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
                        <Unlock className="w-3 h-3" />
                        Open
                      </span>
                    )}

                    <a
                      href={`/dashboard?session_id=${encodeURIComponent(s.session_id)}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      View
                    </a>

                    <button
                      onClick={() => setDeleteConfirm({ sessionIds: [s.session_id], count: 1 })}
                      className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 ring-1 ring-red-200 transition-colors hover:bg-red-50"
                      title="Delete this statement"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl bg-white dark:bg-neutral-900 p-6 shadow-2xl ring-1 ring-neutral-200 dark:ring-neutral-700">
            <button
              onClick={() => setDeleteConfirm(null)}
              disabled={deleting}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-lg bg-red-50 p-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <h2 className="text-lg font-semibold text-neutral-900">
                Delete {deleteConfirm.count === 1 ? 'Statement' : `${deleteConfirm.count} Statements`}?
              </h2>
            </div>

            <p className="text-sm text-neutral-600 mb-2">
              Are you sure you want to delete {deleteConfirm.count === 1 ? 'this' : `these ${deleteConfirm.count}`} statement{deleteConfirm.count === 1 ? '' : 's'}? This action cannot be undone.
            </p>
            <p className="text-xs text-neutral-500 mb-6">
              All transactions, invoices, and categorizations will be permanently deleted.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deleting}
                className="flex-1 rounded-lg px-4 py-2.5 text-sm font-medium text-neutral-700 ring-1 ring-neutral-200 transition-colors hover:bg-neutral-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
