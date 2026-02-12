"use client"

import React, { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import TransactionsTable from '@/components/TransactionsTable'
import StatementInfoBanner from '@/components/StatementInfoBanner'
import BulkCategoryModal from '@/components/BulkCategoryModal'
import axios from '@/lib/axiosClient'
import { useClient } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Page() {
  // Keep server and initial client render identical (no session id),
  // then read the actual `session_id` on mount to avoid hydration mismatches.
  const [clientSessionId, setClientSessionId] = React.useState<string | null>(null)
  const [selectedTransaction, setSelectedTransaction] = useState<any | null>(null)
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)
  const [uploadedCategories, setUploadedCategories] = useState<string[]>([])
  const [selectedStatement, setSelectedStatement] = useState<string>('')
  const { currentClient } = useClient()

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setClientSessionId(params.get('session_id'))
  }, [])

  // Load categories for this session so modals have data
  useEffect(() => {
    if (!clientSessionId) return
    axios.get(`${API_BASE_URL}/categories`, { params: { session_id: clientSessionId } })
      .then(res => {
        // Extract just the names from the category objects
        const categoryNames = (res.data.categories || []).map((cat: any) => 
          typeof cat === 'string' ? cat : cat.name
        )
        setUploadedCategories(categoryNames)
      })
      .catch(() => {})
  }, [clientSessionId])

  return (
    <>
      <div className="bg-white">
        <Sidebar 
          sessionId={clientSessionId}
          selectedStatement={selectedStatement}
          onStatementChange={setSelectedStatement}
        />

        <div className="ml-64 transition-all duration-300">
          <div className="container mx-auto p-4">
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
                onTransactionSelect={(txn) => {
                  setSelectedTransaction({ id: txn.id, description: txn.description, category: txn.category })
                  setIsBulkModalOpen(true)
                }}
                categories={uploadedCategories}
                refreshTrigger={0}
              />
            )}
          </div>
        </div>
      </div>

      {/* Bulk Category Modal (same as dashboard) */}
      <BulkCategoryModal
        isOpen={isBulkModalOpen}
        onClose={() => setIsBulkModalOpen(false)}
        selectedTransaction={selectedTransaction}
        sessionId={clientSessionId || ''}
        categories={uploadedCategories}
        onSuccess={(message: string, updatedCount: number) => {
          setIsBulkModalOpen(false)
          // optionally trigger a refresh or show feedback
        }}
        onCategoryCreated={(newCategories: string[]) => setUploadedCategories(newCategories)}
      />
    </>
  )
}
