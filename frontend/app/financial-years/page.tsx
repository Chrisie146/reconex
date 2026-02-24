'use client'

import React, { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, Archive, RotateCcw, CalendarRange, Eye } from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'
import { useClient } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FinancialYear {
  id: number
  client_id: number
  label: string
  year_start: string
  year_end: string
  status: 'open' | 'archived'
  archived_at: string | null
  created_at: string
}

const STATUS_BADGE: Record<string, string> = {
  open:     'bg-emerald-100 text-emerald-700 border border-emerald-200',
  archived: 'bg-neutral-100 text-neutral-500 border border-neutral-200',
}

export default function FinancialYearsPage() {
  const router = useRouter()
  const { currentClient } = useClient()

  const [years, setYears]           = useState<FinancialYear[]>([])
  const [loading, setLoading]       = useState(false)
  const [selected, setSelected]     = useState<FinancialYear | null>(null)

  // Create modal
  const [showCreate, setShowCreate]       = useState(false)
  const [createLabel, setCreateLabel]     = useState('')
  const [createStart, setCreateStart]     = useState('')
  const [createEnd, setCreateEnd]         = useState('')
  const [isCreating, setIsCreating]       = useState(false)

  // Edit modal
  const [showEdit, setShowEdit]         = useState(false)
  const [editLabel, setEditLabel]       = useState('')
  const [editStart, setEditStart]       = useState('')
  const [editEnd, setEditEnd]           = useState('')
  const [isEditing, setIsEditing]       = useState(false)

  // Delete / Archive confirms
  const [showDeleteConfirm, setShowDeleteConfirm]   = useState(false)
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false)
  const [isArchiving, setIsArchiving]               = useState(false)
  const [showUnarchiveConfirm, setShowUnarchiveConfirm] = useState(false)

  useEffect(() => {
    if (currentClient?.id) fetchYears(currentClient.id)
    else setYears([])
  }, [currentClient?.id])

  const fetchYears = async (clientId: number) => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_BASE_URL}/financial-years`, { params: { client_id: clientId } })
      setYears(res.data.financial_years || [])
    } catch {
      toast.error('Failed to load financial years.')
    } finally {
      setLoading(false)
    }
  }

  // ── Create ─────────────────────────────────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentClient?.id || !createLabel.trim() || !createStart || !createEnd) return
    setIsCreating(true)
    try {
      const res = await axios.post(`${API_BASE_URL}/financial-years`, {
        client_id: currentClient.id,
        label: createLabel.trim(),
        year_start: createStart,
        year_end: createEnd,
      })
      setYears([res.data, ...years])
      setShowCreate(false)
      setCreateLabel(''); setCreateStart(''); setCreateEnd('')
      toast.success('Financial year created.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to create financial year.')
    } finally {
      setIsCreating(false)
    }
  }

  // ── Edit ───────────────────────────────────────────────────────────────────
  const openEdit = (fy: FinancialYear) => {
    setSelected(fy)
    setEditLabel(fy.label)
    setEditStart(fy.year_start)
    setEditEnd(fy.year_end)
    setShowEdit(true)
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected) return
    setIsEditing(true)
    try {
      const res = await axios.put(`${API_BASE_URL}/financial-years/${selected.id}`, {
        label: editLabel.trim() || undefined,
        year_start: editStart || undefined,
        year_end: editEnd || undefined,
      })
      setYears(years.map(y => y.id === selected.id ? res.data : y))
      setShowEdit(false)
      setSelected(null)
      toast.success('Financial year updated.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to update financial year.')
    } finally {
      setIsEditing(false)
    }
  }

  // ── Delete ─────────────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!selected) return
    try {
      await axios.delete(`${API_BASE_URL}/financial-years/${selected.id}`)
      setYears(years.filter(y => y.id !== selected.id))
      setShowDeleteConfirm(false)
      setSelected(null)
      toast.success('Financial year deleted.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete financial year.')
    }
  }

  // ── Archive ────────────────────────────────────────────────────────────────
  const handleArchive = async () => {
    if (!selected) return
    setIsArchiving(true)
    try {
      const res = await axios.post(`${API_BASE_URL}/financial-years/${selected.id}/archive`)
      setYears(years.map(y => y.id === selected.id ? { ...y, status: 'archived', archived_at: new Date().toISOString() } : y))
      setShowArchiveConfirm(false)
      setSelected(null)
      toast.success(res.data.message || 'Year archived successfully.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Archive failed.')
    } finally {
      setIsArchiving(false)
    }
  }

  // ── Unarchive ──────────────────────────────────────────────────────────────
  const handleUnarchive = async () => {
    if (!selected) return
    try {
      await axios.post(`${API_BASE_URL}/financial-years/${selected.id}/unarchive`)
      setYears(years.map(y => y.id === selected.id ? { ...y, status: 'open', archived_at: null } : y))
      setShowUnarchiveConfirm(false)
      setSelected(null)
      toast.success('Year restored to active.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Unarchive failed.')
    }
  }

  return (
    <main className="bg-white min-h-screen">
      <Sidebar sessionId={null} />

      <div className="ml-64 transition-all duration-300">
        <Header />

        <div className="max-w-7xl mx-auto px-6 py-12">
          {/* Page header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <CalendarRange className="text-blue-600" size={32} />
                <h1 className="text-3xl font-bold text-neutral-900">Financial Years</h1>
              </div>
              <p className="text-neutral-500">
                {currentClient
                  ? `Managing years for ${currentClient.name}`
                  : 'Select a client from the sidebar to manage their financial years'}
              </p>
            </div>
            {currentClient && (
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                <Plus size={20} />
                New Year
              </button>
            )}
          </div>

          {/* Content */}
          {!currentClient ? (
            <div className="text-center py-20 text-neutral-400">
              <CalendarRange size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-lg">No client selected</p>
              <p className="text-sm mt-1">Choose a client from the sidebar to view their financial years.</p>
            </div>
          ) : loading ? (
            <div className="text-center py-20 text-neutral-500">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4" />
              Loading financial years...
            </div>
          ) : (
            <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
              {years.length === 0 ? (
                <div className="text-center py-20">
                  <CalendarRange size={48} className="mx-auto mb-4 text-neutral-300" />
                  <p className="text-neutral-500 mb-2 text-lg font-medium">No financial years defined</p>
                  <p className="text-neutral-400 mb-6 text-sm">Define a financial year to organise and archive statement data by period.</p>
                  <button
                    onClick={() => setShowCreate(true)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Plus size={18} />
                    Create First Year
                  </button>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 border-b border-neutral-200">
                    <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                      <th className="px-6 py-4">Label</th>
                      <th className="px-6 py-4">Start Date</th>
                      <th className="px-6 py-4">End Date</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4">Archived</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {years.map(fy => (
                      <tr key={fy.id} className="hover:bg-neutral-50 transition-colors">
                        <td className="px-6 py-4 font-medium text-neutral-900">{fy.label}</td>
                        <td className="px-6 py-4 text-neutral-600">
                          {new Date(fy.year_start).toLocaleDateString('en-ZA')}
                        </td>
                        <td className="px-6 py-4 text-neutral-600">
                          {new Date(fy.year_end).toLocaleDateString('en-ZA')}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[fy.status]}`}>
                            {fy.status === 'open' ? 'Open' : 'Archived'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-neutral-500 text-sm">
                          {fy.archived_at
                            ? new Date(fy.archived_at).toLocaleDateString('en-ZA')
                            : <span className="text-neutral-300 italic">—</span>}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-1">
                            {fy.status === 'archived' && (
                              <button
                                onClick={() => router.push(`/financial-years/${fy.id}`)}
                                className="p-2 text-neutral-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                title="View archived data"
                              >
                                <Eye size={16} />
                              </button>
                            )}
                            {fy.status === 'open' && (
                              <>
                                <button
                                  onClick={() => openEdit(fy)}
                                  className="p-2 text-neutral-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                  title="Edit"
                                >
                                  <Edit2 size={16} />
                                </button>
                                <button
                                  onClick={() => { setSelected(fy); setShowArchiveConfirm(true) }}
                                  className="p-2 text-neutral-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors"
                                  title="Archive this year"
                                >
                                  <Archive size={16} />
                                </button>
                                <button
                                  onClick={() => { setSelected(fy); setShowDeleteConfirm(true) }}
                                  className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 size={16} />
                                </button>
                              </>
                            )}
                            {fy.status === 'archived' && (
                              <button
                                onClick={() => { setSelected(fy); setShowUnarchiveConfirm(true) }}
                                className="p-2 text-neutral-400 hover:text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
                                title="Restore to active"
                              >
                                <RotateCcw size={16} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Create Modal ────────────────────────────────────────────────── */}
      {showCreate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-4">New Financial Year</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Label</label>
                <input
                  type="text"
                  value={createLabel}
                  onChange={e => setCreateLabel(e.target.value)}
                  placeholder="e.g. 2024/2025"
                  className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={createStart}
                    onChange={e => setCreateStart(e.target.value)}
                    className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={createEnd}
                    onChange={e => setCreateEnd(e.target.value)}
                    className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={!createLabel.trim() || !createStart || !createEnd || isCreating}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isCreating ? 'Creating...' : 'Create Year'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setCreateLabel(''); setCreateStart(''); setCreateEnd('') }}
                  className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Edit Modal ──────────────────────────────────────────────────── */}
      {showEdit && selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-4">Edit Financial Year</h2>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Label</label>
                <input
                  type="text"
                  value={editLabel}
                  onChange={e => setEditLabel(e.target.value)}
                  className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={editStart}
                    onChange={e => setEditStart(e.target.value)}
                    className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={editEnd}
                    onChange={e => setEditEnd(e.target.value)}
                    className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={!editLabel.trim() || isEditing}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isEditing ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowEdit(false); setSelected(null) }}
                  className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Archive Confirm ─────────────────────────────────────────────── */}
      {showArchiveConfirm && selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-2">Archive {selected.label}?</h2>
            <p className="text-neutral-600 mb-2">
              All transactions, sessions, reconciliation records and invoices within this period will be
              moved to archive storage.
            </p>
            <p className="text-neutral-600 mb-6">
              The data will remain accessible in read-only mode. You can restore it at any time.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleArchive}
                disabled={isArchiving}
                className="flex-1 px-4 py-2.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors"
              >
                {isArchiving ? 'Archiving...' : 'Archive Year'}
              </button>
              <button
                onClick={() => { setShowArchiveConfirm(false); setSelected(null) }}
                className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Unarchive Confirm ───────────────────────────────────────────── */}
      {showUnarchiveConfirm && selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-2">Restore {selected.label}?</h2>
            <p className="text-neutral-600 mb-6">
              All data for this year will be moved back to the live tables and become fully editable again.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleUnarchive}
                className="flex-1 px-4 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                Restore Year
              </button>
              <button
                onClick={() => { setShowUnarchiveConfirm(false); setSelected(null) }}
                className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirm ──────────────────────────────────────────────── */}
      {showDeleteConfirm && selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-2">Delete {selected.label}?</h2>
            <p className="text-neutral-600 mb-6">
              This only deletes the year definition — no transaction data will be affected.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
              <button
                onClick={() => { setShowDeleteConfirm(false); setSelected(null) }}
                className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
