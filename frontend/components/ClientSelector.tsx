import React, { useState } from 'react'
import { useClient } from '@/lib/clientContext'
import type { Client } from '@/lib/clientContext'
import { ChevronDown, Plus } from 'lucide-react'
import LoadingButton from './LoadingButton'

interface ClientSelectorProps {
  onClientSelect?: (clientId: number) => void
  isDarkMode?: boolean
  isCollapsed?: boolean
}

export default function ClientSelector({ onClientSelect, isDarkMode = false, isCollapsed = false }: ClientSelectorProps) {
  const { clients, currentClient, setCurrentClient, isLoading, createClient } = useClient()
  const [showDropdown, setShowDropdown] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newClientName, setNewClientName] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newClientName.trim()) return

    setIsCreating(true)
    try {
      const newClient = await createClient(newClientName.trim())
      setCurrentClient(newClient)
      setNewClientName('')
      setShowCreateForm(false)
      setShowDropdown(false)
      onClientSelect?.(newClient.id)
    } catch (error) {
      console.error('Failed to create client:', error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleSelectClient = (client: Client) => {
    setCurrentClient(client)
    setShowDropdown(false)
    onClientSelect?.(client.id)
  }

  const buttonClasses = isDarkMode
    ? 'flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 border border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors w-full'
    : 'flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-neutral-200 hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors'

  const textClasses = isDarkMode
    ? 'text-sm font-medium text-white'
    : 'text-sm font-medium text-neutral-700'

  return (
    <div className="relative">
      {/* Client selector button */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={isLoading}
        className={buttonClasses}
        title={currentClient?.name || 'Select Client'}
      >
        {isCollapsed ? (
          <span className="text-lg">👤</span>
        ) : (
          <>
            <span className={textClasses}>
              {currentClient ? currentClient.name : 'Select Client'}
            </span>
            <ChevronDown size={16} className={isDarkMode ? 'text-gray-400' : 'text-neutral-500'} />
          </>
        )}
      </button>

      {/* Dropdown menu */}
      {showDropdown && (
        <div className={`absolute top-full left-0 right-0 mt-1 ${isDarkMode ? 'bg-gray-800 border-gray-600' : 'bg-white border-neutral-200'} border rounded-lg shadow-lg z-50`}>
          {/* Client list */}
          <div className="max-h-64 overflow-y-auto">
            {clients.length === 0 ? (
              <div className={`p-3 text-sm text-center ${isDarkMode ? 'text-gray-400' : 'text-neutral-500'}`}>No clients yet</div>
            ) : (
              clients.map((client) => (
                <button
                  key={client.id}
                  onClick={() => handleSelectClient(client)}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    currentClient?.id === client.id
                      ? isDarkMode
                        ? 'bg-blue-600 text-white'
                        : 'bg-blue-50 text-blue-700'
                      : isDarkMode
                        ? 'text-white hover:bg-gray-700'
                        : 'text-neutral-700 hover:bg-neutral-50'
                  }`}
                >
                  {client.name}
                </button>
              ))
            )}
          </div>

          {/* Divider */}
          <div className={`border-t ${isDarkMode ? 'border-gray-600' : 'border-neutral-200'}`} />

          {/* Create new client form or button */}
          {showCreateForm ? (
            <form onSubmit={handleCreateClient} className={`p-3 border-t ${isDarkMode ? 'border-gray-600' : 'border-neutral-200'}`}>
              <input
                type="text"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                placeholder="Client name..."
                className={`w-full px-2 py-1 text-sm border rounded mb-2 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                  isDarkMode
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                    : 'bg-white border-neutral-200 text-neutral-900'
                }`}
                autoFocus
              />
              <div className="flex gap-2">
                <LoadingButton
                  type="submit"
                  loading={isCreating}
                  loadingText="Creating..."
                  variant="primary"
                  className="flex-1 text-xs py-1"
                  disabled={!newClientName.trim()}
                >
                  Create
                </LoadingButton>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false)
                    setNewClientName('')
                  }}
                  className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                    isDarkMode
                      ? 'text-gray-300 hover:bg-gray-700'
                      : 'text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setShowCreateForm(true)}
              className={`w-full flex items-center justify-center gap-2 px-4 py-2 text-sm transition-colors ${
                isDarkMode
                  ? 'text-gray-300 hover:bg-gray-700'
                  : 'text-neutral-600 hover:bg-neutral-50'
              }`}
            >
              <Plus size={16} />
              New Client
            </button>
          )}
        </div>
      )}
    </div>
  )
}
