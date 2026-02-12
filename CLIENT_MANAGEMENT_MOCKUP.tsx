'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, Edit2, Search, Clock, FileText, MoreVertical } from 'lucide-react'
import axios from 'axios'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ClientWithStats {
  id: number
  name: string
  created_at: string
  last_statement_date?: string
  statement_count: number
  transaction_count: number
}

export default function ClientManagementPage() {
  const [clients, setClients] = useState<ClientWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newClientName, setNewClientName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [selectedClient, setSelectedClient] = useState<ClientWithStats | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  useEffect(() => {
    fetchClients()
  }, [])

  const fetchClients = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/clients`)
      setClients(res.data.clients || [])
    } catch (error) {
      console.error('Failed to fetch clients:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newClientName.trim()) return

    setIsCreating(true)
    try {
      const res = await axios.post(`${API_BASE_URL}/clients`, { name: newClientName.trim() })
      setClients([...clients, res.data.client])
      setNewClientName('')
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create client:', error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteClient = async () => {
    if (!selectedClient) return

    try {
      await axios.delete(`${API_BASE_URL}/clients/${selectedClient.id}`)
      setClients(clients.filter(c => c.id !== selectedClient.id))
      setShowDeleteConfirm(false)
      setSelectedClient(null)
    } catch (error) {
      console.error('Failed to delete client:', error)
    }
  }

  const filteredClients = clients.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <main className="bg-white">
      <Sidebar sessionId={null} />
      
      <div className="ml-64 transition-all duration-300">
        <Header />
        
        <div className="max-w-6xl mx-auto px-4 py-12">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Clients</h1>
              <p className="text-neutral-500 mt-1">Manage your banking clients and their statements</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={20} />
              New Client
            </button>
          </div>

          {/* Search Bar */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-3 text-neutral-400" size={18} />
              <input
                type="text"
                placeholder="Search clients..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Clients Table */}
          <div className="card bg-white border border-neutral-200 rounded-lg overflow-hidden">
            {loading ? (
              <div className="px-6 py-12 text-center text-neutral-500">Loading clients...</div>
            ) : filteredClients.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <p className="text-neutral-500 mb-4">
                  {clients.length === 0 ? 'No clients yet. Create one to get started.' : 'No clients match your search.'}
                </p>
                {clients.length === 0 && (
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Plus size={18} />
                    Create First Client
                  </button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 border-b border-neutral-200">
                    <tr className="text-left text-xs font-semibold text-neutral-600">
                      <th className="px-6 py-3">Client Name</th>
                      <th className="px-6 py-3">Statements</th>
                      <th className="px-6 py-3">Transactions</th>
                      <th className="px-6 py-3">Last Statement</th>
                      <th className="px-6 py-3">Created</th>
                      <th className="px-6 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredClients.map((client) => (
                      <tr
                        key={client.id}
                        className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center font-medium">
                              {client.name.charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-neutral-900">{client.name}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2 text-neutral-700">
                            <FileText size={16} />
                            {client.statement_count}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-neutral-700">
                          {client.transaction_count.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-neutral-600">
                          {client.last_statement_date ? (
                            <div className="flex items-center gap-2">
                              <Clock size={16} />
                              {new Date(client.last_statement_date).toLocaleDateString('en-ZA')}
                            </div>
                          ) : (
                            <span className="text-neutral-400 italic">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-neutral-600">
                          {new Date(client.created_at).toLocaleDateString('en-ZA')}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              className="p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
                              title="View details"
                            >
                              <Edit2 size={16} />
                            </button>
                            <button
                              onClick={() => {
                                setSelectedClient(client)
                                setShowDeleteConfirm(true)
                              }}
                              className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                              title="Delete client"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Footer with totals */}
            {filteredClients.length > 0 && (
              <div className="px-6 py-4 bg-neutral-50 border-t border-neutral-200 text-sm text-neutral-600">
                <p>
                  Showing {filteredClients.length} of {clients.length} clients •{' '}
                  {filteredClients.reduce((sum, c) => sum + c.statement_count, 0)} total statements
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Client Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-96">
            <h2 className="text-xl font-bold text-neutral-900 mb-4">Create New Client</h2>
            <form onSubmit={handleCreateClient}>
              <input
                type="text"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                placeholder="Client name..."
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={!newClientName.trim() || isCreating}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isCreating ? 'Creating...' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewClientName('')
                  }}
                  className="flex-1 px-4 py-2 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && selectedClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-96">
            <h2 className="text-xl font-bold text-neutral-900 mb-2">Delete Client?</h2>
            <p className="text-neutral-600 mb-6">
              Are you sure you want to delete <strong>{selectedClient.name}</strong>? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteClient}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setSelectedClient(null)
                }}
                className="flex-1 px-4 py-2 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
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
