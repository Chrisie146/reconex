"use client"

import React, { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import TransactionsTable from '@/components/TransactionsTable'
import StatementInfoBanner from '@/components/StatementInfoBanner'
import axios from '@/lib/axiosClient'
import { useClient } from '@/lib/clientContext'

import { API_BASE_URL } from '@/lib/apiBase'

export default function Page() {
  // Keep server and initial client render identical (no session id),
  // then read the actual `session_id` on mount to avoid hydration mismatches.
  const [clientSessionId, setClientSessionId] = React.useState<string | null>(null)
  const [uploadedCategories, setUploadedCategories] = useState<string[]>([])
  const [selectedStatement, setSelectedStatement] = useState<string>('')
  const { currentClient } = useClient()

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setClientSessionId(params.get('session_id'))
  }, [])

  // Load categories for this session/statement so modals have data
  useEffect(() => {
    const effectiveSessionId = clientSessionId || selectedStatement || null
    if (!effectiveSessionId && !currentClient?.id) return
    const params: any = { ...(currentClient?.id ? { client_id: currentClient.id } : {}) }
    if (effectiveSessionId) params.session_id = effectiveSessionId
    axios.get(`${API_BASE_URL}/categories`, { params })
      .then(res => {
        // Extract just the names from the category objects
        const categoryNames = (res.data.categories || []).map((cat: any) => 
          typeof cat === 'string' ? cat : cat.name
        )
        setUploadedCategories(categoryNames)
      })
      .catch(() => {})
  }, [clientSessionId, selectedStatement, currentClient?.id])

  return (
    <>
      <div className="bg-white dark:bg-neutral-950 min-h-screen">
        <Sidebar 
          sessionId={clientSessionId}
          selectedStatement={selectedStatement}
          onStatementChange={setSelectedStatement}
        />

        <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
          <div className="w-full px-3 py-2">
            {selectedStatement && (
              <StatementInfoBanner selectedStatement={selectedStatement} sessionId={clientSessionId} />
            )}

            {!clientSessionId && !currentClient ? (
              <div className="text-center py-8 text-neutral-600">
                Select a client in the left sidebar to view transactions.
              </div>
            ) : (
              <TransactionsTable
                sessionId={clientSessionId}
                selectedStatement={selectedStatement}
                onStatementChange={setSelectedStatement}
                categories={uploadedCategories}
                refreshTrigger={0}
              />
            )}
          </div>
        </div>
      </div>
    </>
  )
}
