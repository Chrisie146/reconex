'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiFetch } from './apiFetch'
import { isAuthenticated } from './auth'

export interface Client {
  id: number
  name: string
  created_at: string
}

interface ClientContextType {
  clients: Client[]
  currentClient: Client | null
  isLoading: boolean
  error: string | null
  setCurrentClient: (client: Client | null) => void
  refreshClients: () => Promise<void>
  createClient: (name: string) => Promise<Client>
  updateClient: (id: number, name: string) => Promise<Client>
  deleteClient: (id: number) => Promise<void>
}

const ClientContext = createContext<ClientContextType | undefined>(undefined)

export function ClientProvider({ children }: { children: ReactNode }) {
  const [clients, setClients] = useState<Client[]>([])
  const [currentClient, setCurrentClient] = useState<Client | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Load clients on mount only if authenticated
  useEffect(() => {
    if (isAuthenticated()) {
      refreshClients()
    }
  }, [])

  // Load saved current client from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return
    const saved = localStorage.getItem('selected_client')
    if (saved) {
      try {
        setCurrentClient(JSON.parse(saved))
      } catch (e) {
        // Invalid JSON, ignore
      }
    }
  }, [])

  // Save current client to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (currentClient) {
      localStorage.setItem('selected_client', JSON.stringify(currentClient))
    } else {
      localStorage.removeItem('selected_client')
    }
  }, [currentClient])

  const refreshClients = async () => {
    setIsLoading(true)
    setError(null)
    try {
      console.log('[ClientContext] Fetching clients')
      const data = await apiFetch('/clients')
      console.log('[ClientContext] Clients loaded:', data)
      setClients(data.clients || [])
      // If we had a current client but it's no longer in the list, clear it
      if (currentClient && !data.clients.find((c: Client) => c.id === currentClient.id)) {
        setCurrentClient(null)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch clients'
      console.error('[ClientContext] Error:', message)
      setError(message)
      // Don't block UI on error - allow user to still create clients
    } finally {
      setIsLoading(false)
    }
  }

  const createClient = async (name: string): Promise<Client> => {
    if (!isAuthenticated()) {
      throw new Error('You must be logged in to create a client')
    }
    setIsLoading(true)
    try {
      const newClient = await apiFetch(`/clients?name=${encodeURIComponent(name)}`, {
        method: 'POST'
      })
      console.log('[ClientContext] New client created:', newClient)
      // Refresh the full client list to ensure consistency and prevent data loss
      await refreshClients()
      return newClient
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create client'
      console.error('[ClientContext] Error creating client:', message)
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const updateClient = async (id: number, name: string): Promise<Client> => {
    setIsLoading(true)
    try {
      const updated = await apiFetch(
        `/clients/${id}?name=${encodeURIComponent(name)}`,
        { method: 'PUT' }
      )
      setClients(clients.map(c => c.id === id ? updated : c))
      if (currentClient?.id === id) {
        setCurrentClient(updated)
      }
      return updated
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update client'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const deleteClient = async (id: number): Promise<void> => {
    setIsLoading(true)
    try {
      await apiFetch(
        `/clients/${id}`,
        { method: 'DELETE' }
      )
      setClients(clients.filter(c => c.id !== id))
      if (currentClient?.id === id) {
        setCurrentClient(null)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete client'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <ClientContext.Provider
      value={{
        clients,
        currentClient,
        isLoading,
        error,
        setCurrentClient,
        refreshClients,
        createClient,
        updateClient,
        deleteClient
      }}
    >
      {children}
    </ClientContext.Provider>
  )
}

export function useClient() {
  const context = useContext(ClientContext)
  if (context === undefined) {
    throw new Error('useClient must be used within ClientProvider')
  }
  return context
}
