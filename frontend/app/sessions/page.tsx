"use client"

import React from 'react'
import Sidebar from '@/components/Sidebar'
import { Trash2 } from 'lucide-react'
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
      // apiFetch already returns parsed JSON and throws on error
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
      // Use bulk endpoint if multiple sessions, otherwise use single delete
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
      
      // Refresh list
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
    <div className="bg-white">
      <Sidebar sessionId={null} />

      <div className="ml-64 transition-all duration-300">
        <div className="container mx-auto p-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-semibold">Previous Statements</h1>
            {selectedSessions.size > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-neutral-700">
                  {selectedSessions.size} selected
                </span>
                <button
                  onClick={() => setDeleteConfirm({ sessionIds: Array.from(selectedSessions), count: selectedSessions.size })}
                  className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Delete {selectedSessions.size}
                </button>
              </div>
            )}
          </div>

          {success && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded text-green-700">
              ✓ {success}
            </div>
          )}

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">
              ✗ {error}
            </div>
          )}

          {loading ? (
            <div className="text-neutral-600">Loading...</div>
          ) : !currentClient ? (
            <div className="text-neutral-600">Select a client in the left sidebar to view their previous statements.</div>
          ) : sessions.length === 0 ? (
            <div className="text-neutral-600">No previous statements found for {currentClient.name}.</div>
          ) : (
            <div className="space-y-3">
              {/* Select All Checkbox */}
              {sessions.length > 0 && (
                <div className="p-4 border rounded bg-neutral-50 flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selectedSessions.size === sessions.length && sessions.length > 0}
                    onChange={toggleSelectAll}
                    className="w-5 h-5 cursor-pointer"
                  />
                  <label className="text-sm font-medium text-neutral-700 cursor-pointer flex-1">
                    Select all ({sessions.length})
                  </label>
                </div>
              )}

              {/* Session List */}
              {sessions.map(s => (
                <div key={s.session_id} className={`p-4 border rounded flex items-center gap-4 transition ${selectedSessions.has(s.session_id) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'}`}>
                  <input
                    type="checkbox"
                    checked={selectedSessions.has(s.session_id)}
                    onChange={() => toggleSessionSelect(s.session_id)}
                    className="w-5 h-5 cursor-pointer"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-lg">{s.friendly_name}</div>
                    <div className="text-sm text-neutral-600">{s.transaction_count} transactions • {s.date_from || 'n/a'} → {s.date_to || 'n/a'}</div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {s.locked ? (
                      <span className="px-2 py-1 text-sm bg-red-100 text-red-700 rounded">Locked</span>
                    ) : (
                      <span className="px-2 py-1 text-sm bg-green-100 text-green-700 rounded">Open</span>
                    )}

                    <a href={`/dashboard?session_id=${encodeURIComponent(s.session_id)}`} className="px-3 py-1 text-sm text-white bg-blue-600 rounded hover:bg-blue-700">View</a>
                    
                    <button
                      onClick={() => setDeleteConfirm({ sessionIds: [s.session_id], count: 1 })}
                      className="px-3 py-1 text-sm text-white bg-red-600 rounded hover:bg-red-700 flex items-center gap-1"
                      title="Delete this statement"
                    >
                      <Trash2 size={16} />
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
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-2xl max-w-md p-6">
            <h2 className="text-xl font-bold text-red-600 mb-2">
              Delete {deleteConfirm.count === 1 ? 'Statement' : `${deleteConfirm.count} Statements`}?
            </h2>
            <p className="text-neutral-700 mb-4">
              Are you sure you want to delete {deleteConfirm.count === 1 ? 'this' : `these ${deleteConfirm.count}`} statement{deleteConfirm.count === 1 ? '' : 's'}? This action cannot be undone.
            </p>
            <p className="text-sm text-neutral-600 mb-6">
              All transactions, invoices, and categorizations will be permanently deleted.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-neutral-100 text-neutral-700 rounded hover:bg-neutral-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 font-medium"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
