'use client'

import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
import Header from '@/components/Header'
import UploadSection from '@/components/UploadSection'
import TransactionsTable from '@/components/TransactionsTable'
import MonthlySummary from '@/components/MonthlySummary'
import CategoryBreakdown from '@/components/CategoryBreakdown'
import ExportButtons from '@/components/ExportButtons'
import BulkCategoryModal from '@/components/BulkCategoryModal'
import Sidebar from '@/components/Sidebar'
import StatementInfoBanner from '@/components/StatementInfoBanner'
import { useClient } from '@/lib/clientContext'

interface SelectedTransaction {
  id: number
  description: string
  category: string
}

export default function Dashboard() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedStatement, setSelectedStatement] = useState<string>('')
  const [highlightTxnId, setHighlightTxnId] = useState<number | null>(null)
  const [transactionCount, setTransactionCount] = useState(0)
  const [uploadedCategories, setUploadedCategories] = useState<string[]>([])
  const [selectedTransaction, setSelectedTransaction] = useState<SelectedTransaction | null>(null)
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [showUploadView, setShowUploadView] = useState(true)
  const { currentClient } = useClient()

  useEffect(() => {
    const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
    const sid = params.get('session_id')
    const highlightId = params.get('highlight_txn')
    if (sid) {
      setSessionId(sid)
      setShowUploadView(false)  // If loading with session, show transactions
    }
    if (highlightId) {
      setHighlightTxnId(parseInt(highlightId, 10))
      // Clear highlight after 5 seconds
      setTimeout(() => setHighlightTxnId(null), 5000)
    }
  }, [])

  // If page loaded with an existing session_id in the URL, fetch categories
  useEffect(() => {
    if (!sessionId) return
    axios.get(`${API_BASE_URL}/categories`, { params: { session_id: sessionId } })
      .then(res => {
        // Extract just the names from the category objects
        const categoryNames = (res.data.categories || []).map((cat: any) => 
          typeof cat === 'string' ? cat : cat.name
        )
        setUploadedCategories(categoryNames)
      })
      .catch(() => {
        // ignore errors silently; UI will still function without preloaded categories
      })
  }, [sessionId])

  const handleUploadSuccess = (newSessionId: string, count: number, categories: string[]) => {
    setSessionId(newSessionId)
    setTransactionCount(count)
    setUploadedCategories(categories)
    setShowUploadView(false)  // Switch to transactions view after successful upload
  }

  const handleTransactionSelect = (transaction: any) => {
    setSelectedTransaction({
      id: transaction.id,
      description: transaction.description,
      category: transaction.category,
    })
    setIsBulkModalOpen(true)
  }

  const handleBulkSuccess = (message: string, updatedCount: number) => {
    setSuccessMessage(message)
    setIsBulkModalOpen(false)
    setRefreshTrigger(prev => prev + 1)  // Trigger refresh
    setTimeout(() => setSuccessMessage(''), 4000)
  }

  const handleCategoryCreated = (newCategories: string[]) => {
    setUploadedCategories(newCategories)
  }

  const handleReset = () => {
    setSessionId(null)
    setTransactionCount(0)
    setUploadedCategories([])
    setSelectedTransaction(null)
    setShowUploadView(true)  // Show upload section
  }

  // Lightweight 5-row preview state
  const [previewTxns, setPreviewTxns] = useState<any[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)

  useEffect(() => {
    const fetchPreview = async () => {
      if (!sessionId && !currentClient?.id) {
        setPreviewTxns([])
        return
      }

      setLoadingPreview(true)
      try {
        const params: any = { _t: Date.now(), limit: 5 }
        if (currentClient?.id) params.client_id = currentClient.id
        else if (sessionId) params.session_id = sessionId

        const res = await axios.get(`${API_BASE_URL}/transactions`, { params })
        setPreviewTxns(res.data.transactions?.slice(0, 5) || [])
      } catch (e) {
        setPreviewTxns([])
      } finally {
        setLoadingPreview(false)
      }
    }

    fetchPreview()
  }, [sessionId, currentClient?.id, refreshTrigger])

  return (
    <main className="bg-white">
      <Sidebar 
        sessionId={sessionId}
        selectedStatement={selectedStatement}
        onStatementChange={setSelectedStatement}
      />
      
      <div className="ml-64 transition-all duration-300">
        <Header />
        
        <div className="max-w-6xl mx-auto px-4 py-12">
          {showUploadView ? (
            <UploadSection onUploadSuccess={handleUploadSuccess} />
          ) : (
            <div className="space-y-12">
              {/* Statement Info Banner */}
              {selectedStatement && (
                <StatementInfoBanner selectedStatement={selectedStatement} sessionId={sessionId} />
              )}

              {/* Summary Cards */}
              <MonthlySummary sessionId={sessionId} currentClient={currentClient} />

              {/* Category Breakdown */}
              <CategoryBreakdown sessionId={sessionId} currentClient={currentClient} />

              {/* Transactions Preview (5 rows) */}
              <div className="card bg-white border border-neutral-200">
                <div className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-neutral-900">Recent transactions</h3>
                    <p className="text-sm text-neutral-500">Quick preview — most recent 5 transactions</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={sessionId ? `/transactions?session_id=${sessionId}` : '/transactions'}
                      className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                      View all transactions
                    </a>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  {loadingPreview ? (
                    <div className="px-6 py-8 text-center text-neutral-500">Loading preview...</div>
                  ) : previewTxns.length === 0 ? (
                    <div className="px-6 py-8 text-center text-neutral-500">No recent transactions</div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-neutral-500 border-b border-neutral-100">
                          <th className="px-4 py-3">Date</th>
                          <th className="px-4 py-3">Description</th>
                          <th className="px-4 py-3">Category</th>
                          <th className="px-4 py-3 text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewTxns.map((t: any) => (
                          <tr key={t.id} className="border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer" onClick={() => {
                            handleTransactionSelect(t)
                            // deep-link into Transactions page if user wants full view
                            // (clicking row opens bulk modal here for quick edit)
                          }}>
                            <td className="px-4 py-3 text-neutral-600">{new Date(t.date).toLocaleDateString('en-ZA')}</td>
                            <td className="px-4 py-3 text-neutral-900 truncate max-w-[40ch]">{t.description || <span className="text-neutral-400 italic">[No description]</span>}</td>
                            <td className="px-4 py-3 text-neutral-700">{t.category || <span className="text-neutral-400 italic">Uncategorized</span>}</td>
                            <td className="px-4 py-3 text-right font-medium {t.amount>=0? 'text-green-600' : 'text-red-600'}">{t.amount >= 0 ? '+' : ''}R{Math.abs(t.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Export Options */}
              <ExportButtons sessionId={sessionId} currentClient={currentClient} />

              {/* Categories & Rules Button */}
              <div className="flex justify-center gap-4 py-4">
                <a
                  href={`/rules?session_id=${sessionId}`}
                  className="btn-primary"
                >
                  📋 Categories & Rules
                </a>
                <button
                  onClick={handleReset}
                  className="btn-secondary"
                >
                  Upload New Statement
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bulk Category Modal */}
      <BulkCategoryModal
        isOpen={isBulkModalOpen}
        onClose={() => setIsBulkModalOpen(false)}
        selectedTransaction={selectedTransaction}
        sessionId={sessionId || ''}
        categories={uploadedCategories}
        onSuccess={handleBulkSuccess}
        onCategoryCreated={handleCategoryCreated}
      />

      <footer className="border-t border-neutral-200 bg-neutral-50 mt-16">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-neutral-600">
          <p>Bank Statement Analyzer v1.0 | © 2024 All Rights Reserved</p>
        </div>
      </footer>
    </main>
  )
}
