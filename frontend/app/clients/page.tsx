'use client'

import React, { useState, useEffect } from 'react'
import { Plus, Trash2, Edit2, Search, Clock, FileText, Users } from 'lucide-react'
import axios from '@/lib/axiosClient'
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

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newClientName, setNewClientName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [selectedClient, setSelectedClient] = useState<ClientWithStats | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editName, setEditName] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)

  useEffect(() => {
    fetchClients()
  }, [])

  useEffect(() => {
    fetchClients()
  }, [])

  const fetchClients = async () => {
    setLoading(true)
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
      const res = await axios.post(`${API_BASE_URL}/clients`, null, {
        params: { name: newClientName.trim() }
      })
      
      // Add new client to the list
      setClients([...clients, res.data.client])
      setNewClientName('')
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create client:', error)
      alert('Failed to create client. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleUpdateClient = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editName.trim() || !selectedClient) return

    setIsUpdating(true)
    try {
      await axios.put(`${API_BASE_URL}/clients/${selectedClient.id}`, null, {
        params: { name: editName.trim() }
      })
      
      // Update client in the list
      setClients(clients.map(c => 
        c.id === selectedClient.id ? { ...c, name: editName.trim() } : c
      ))
      setShowEditModal(false)
      setSelectedClient(null)
      setEditName('')
    } catch (error) {
      console.error('Failed to update client:', error)
      alert('Failed to update client. Please try again.')
    } finally {
      setIsUpdating(false)
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
      alert('Failed to delete client. Please try again.')
    }
  }

  const filteredClients = clients.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <main className="bg-white min-h-screen">
      <Sidebar sessionId={null} />
      
      <div className="ml-64 transition-all duration-300">
        <Header />
        
        <div className="max-w-7xl mx-auto px-6 py-12">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Users className="text-blue-600" size={32} />
                <h1 className="text-3xl font-bold text-neutral-900">Client Management</h1>
              </div>
              <p className="text-neutral-500">Manage your clients and view their statement activity</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              <Plus size={20} />
              New Client
            </button>
          </div>

          {/* Search Bar */}
          <div className="mb-6">
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-3 text-neutral-400" size={18} />
              <input
                type="text"
                placeholder="Search clients..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Clients Table */}
          <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden shadow-sm">
            {loading ? (
              <div className="px-6 py-16 text-center text-neutral-500">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                Loading clients...
              </div>
            ) : filteredClients.length === 0 ? (
              <div className="px-6 py-16 text-center">
                {clients.length === 0 ? (
                  <>
                    <Users className="mx-auto mb-4 text-neutral-300" size={48} />
                    <p className="text-neutral-500 mb-2 text-lg font-medium">No clients yet</p>
                    <p className="text-neutral-400 mb-6">Create your first client to get started</p>
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <Plus size={18} />
                      Create First Client
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-neutral-500">No clients match your search</p>
                    <button
                      onClick={() => setSearchQuery('')}
                      className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
                    >
                      Clear search
                    </button>
                  </>
                )}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-200">
                      <tr className="text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                        <th className="px-6 py-4">Client Name</th>
                        <th className="px-6 py-4">Statements</th>
                        <th className="px-6 py-4">Transactions</th>
                        <th className="px-6 py-4">Last Statement</th>
                        <th className="px-6 py-4">Created</th>
                        <th className="px-6 py-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {filteredClients.map((client) => (
                        <tr
                          key={client.id}
                          className="hover:bg-neutral-50 transition-colors"
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg flex items-center justify-center font-semibold text-base shadow-sm">
                                {client.name.charAt(0).toUpperCase()}
                              </div>
                              <span className="font-medium text-neutral-900">{client.name}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2 text-neutral-700">
                              <FileText size={16} className="text-neutral-400" />
                              <span className="font-medium">{client.statement_count}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-medium text-neutral-700">
                              {client.transaction_count.toLocaleString()}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-neutral-600">
                            {client.last_statement_date ? (
                              <div className="flex items-center gap-2">
                                <Clock size={16} className="text-neutral-400" />
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
                                onClick={() => {
                                  setSelectedClient(client)
                                  setEditName(client.name)
                                  setShowEditModal(true)
                                }}
                                className="p-2 text-neutral-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                title="Edit client"
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

                {/* Footer with totals */}
                <div className="px-6 py-4 bg-neutral-50 border-t border-neutral-200">
                  <div className="flex items-center justify-between text-sm">
                    <p className="text-neutral-600">
                      Showing <span className="font-medium text-neutral-900">{filteredClients.length}</span> of{' '}
                      <span className="font-medium text-neutral-900">{clients.length}</span> clients
                    </p>
                    <p className="text-neutral-600">
                      <span className="font-medium text-neutral-900">
                        {filteredClients.reduce((sum, c) => sum + c.statement_count, 0)}
                      </span>{' '}
                      total statements •{' '}
                      <span className="font-medium text-neutral-900">
                        {filteredClients.reduce((sum, c) => sum + c.transaction_count, 0).toLocaleString()}
                      </span>{' '}
                      total transactions
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Create Client Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-4">Create New Client</h2>
            <form onSubmit={handleCreateClient}>
              <input
                type="text"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                placeholder="Client name..."
                className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={!newClientName.trim() || isCreating}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isCreating ? 'Creating...' : 'Create Client'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewClientName('')
                  }}
                  className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Client Modal */}
      {showEditModal && selectedClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-4">Edit Client</h2>
            <form onSubmit={handleUpdateClient}>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Client name..."
                className="w-full px-3 py-2.5 border border-neutral-200 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={!editName.trim() || isUpdating}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isUpdating ? 'Updating...' : 'Update Client'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedClient(null)
                    setEditName('')
                  }}
                  className="flex-1 px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors"
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
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-neutral-900 mb-2">Delete Client?</h2>
            <p className="text-neutral-600 mb-6">
              Are you sure you want to delete <strong>{selectedClient.name}</strong>? 
              This will permanently delete all {selectedClient.statement_count} statement(s) and{' '}
              {selectedClient.transaction_count} transaction(s). This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteClient}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete Client
              </button>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setSelectedClient(null)
                }}
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
