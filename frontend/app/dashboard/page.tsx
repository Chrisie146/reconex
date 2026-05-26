'use client'

import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'

import { API_BASE_URL } from '@/lib/apiBase'
import Header from '@/components/Header'
import UploadSection from '@/components/UploadSection'
import TransactionsTable from '@/components/TransactionsTable'
import MonthlySummary from '@/components/MonthlySummary'
import CategoryBreakdown from '@/components/CategoryBreakdown'
import ExportButtons from '@/components/ExportButtons'
import CashFlowChart from '@/components/CashFlowChart'
import IncomeExpenseTrend from '@/components/IncomeExpenseTrend'
import MerchantAnalytics from '@/components/MerchantAnalytics'
import RecurringTransactions from '@/components/RecurringTransactions'
import BulkCategoryModal from '@/components/BulkCategoryModal'
import Sidebar from '@/components/Sidebar'
import StatementInfoBanner from '@/components/StatementInfoBanner'
import OnboardingWizard from '@/components/OnboardingWizard'
import AnimatedSection from '@/components/AnimatedSection'
import { useClient } from '@/lib/clientContext'
import { getAuthUser } from '@/lib/auth'

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
  const [isClient, setIsClient] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const { currentClient } = useClient()

  useEffect(() => {
    setIsClient(true)
    setIsHydrated(true)

    // Check if user should see onboarding
    if (typeof window !== 'undefined') {
      const flag = localStorage.getItem('reconex_onboarding')
      if (flag === 'pending') {
        setShowOnboarding(true)
      }
    }
  }, [])

  useEffect(() => {
    if (!isClient) return

    const params = new URLSearchParams(window.location.search)
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
  }, [isClient])

  // If page loaded with an existing session_id in the URL, fetch categories
  useEffect(() => {
    if (!sessionId) return
    axios.get(`${API_BASE_URL}/categories`, { params: { session_id: sessionId, ...(currentClient?.id ? { client_id: currentClient.id } : {}) } })
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
  }, [sessionId, currentClient?.id, selectedStatement])

  // Also refresh categories when switching statements via sidebar
  useEffect(() => {
    if (!selectedStatement) return
    const params: any = { session_id: selectedStatement }
    if (currentClient?.id) params.client_id = currentClient.id
    axios.get(`${API_BASE_URL}/categories`, { params })
      .then(res => {
        const categoryNames = (res.data.categories || []).map((cat: any) => 
          typeof cat === 'string' ? cat : cat.name
        )
        setUploadedCategories(categoryNames)
      })
      .catch(() => {})
  }, [selectedStatement])

  const handleUploadSuccess = (newSessionId: string, count: number, categories: string[]) => {
    setSessionId(newSessionId)
    setSelectedStatement(newSessionId)  // Sync sidebar selection to the newly uploaded statement
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
    setSelectedStatement('')  // Clear sidebar selection
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
    <main className="bg-white dark:bg-neutral-950 min-h-screen">
      <Sidebar 
        sessionId={sessionId}
        selectedStatement={selectedStatement}
        onStatementChange={setSelectedStatement}
      />
      
      <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
        <Header />
        
        <div className="max-w-6xl mx-auto px-4 py-12" suppressHydrationWarning>
          {!isHydrated ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-500">Loading...</div>
            </div>
          ) : showUploadView ? (
            <UploadSection onUploadSuccess={handleUploadSuccess} />
          ) : (
            <div className="space-y-8">
              {/* Statement Info Banner */}
              {selectedStatement && (
                <AnimatedSection delay="0ms">
                  <StatementInfoBanner selectedStatement={selectedStatement} sessionId={sessionId} />
                </AnimatedSection>
              )}

              {/* Summary Cards */}
              <AnimatedSection delay="60ms">
                <MonthlySummary sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Cash Flow Chart */}
              <AnimatedSection delay="120ms">
                <CashFlowChart sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Income / Expense Trend */}
              <AnimatedSection delay="0ms">
                <IncomeExpenseTrend sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Category Breakdown */}
              <AnimatedSection delay="0ms">
                <CategoryBreakdown sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Merchant Analytics */}
              <AnimatedSection delay="0ms">
                <MerchantAnalytics sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Recurring Transactions */}
              <AnimatedSection delay="0ms">
                <RecurringTransactions sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Transactions Preview (5 rows) */}
              <AnimatedSection delay="0ms">
              <div className="card bg-white border border-neutral-200">
                <div className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-neutral-900">Recent transactions</h3>
                    <p className="text-sm text-neutral-500">Most recent 5 transactions</p>
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
                        {previewTxns.map((t: any, idx: number) => (
                          <tr
                            key={t.id}
                            className="row-enter border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer"
                            style={{ animationDelay: `${idx * 60}ms` }}
                            onClick={() => { handleTransactionSelect(t) }}
                          >
                            <td className="px-4 py-3 text-neutral-600">{new Date(t.date).toLocaleDateString('en-ZA')}</td>
                            <td className="px-4 py-3 text-neutral-900 truncate max-w-[40ch]">{t.description || <span className="text-neutral-400 italic">[No description]</span>}</td>
                            <td className="px-4 py-3 text-neutral-700">{t.category || <span className="text-neutral-400 italic">Uncategorized</span>}</td>
                            <td className={`px-4 py-3 text-right font-medium ${t.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>{t.amount >= 0 ? '+' : ''}R{Math.abs(t.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
              </AnimatedSection>

              {/* Export Options */}
              <AnimatedSection delay="0ms">
                <ExportButtons sessionId={sessionId} currentClient={currentClient} />
              </AnimatedSection>

              {/* Categories & Rules Button */}
              <div className="flex justify-center gap-4 py-4">
                <a
                  href={`/rules?session_id=${sessionId}`}
                  className="btn-primary"
                >
                  Categories & Rules
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

      {/* Onboarding Wizard for new users */}
      {showOnboarding && (
        <OnboardingWizard
          userName={getAuthUser()?.full_name}
          onComplete={() => {
            setShowOnboarding(false)
            if (typeof window !== 'undefined') {
              localStorage.removeItem('reconex_onboarding')
            }
          }}
        />
      )}

      <footer className="border-t border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 mt-16">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-neutral-600">
          <p>Reconex | © {new Date().getFullYear()} All Rights Reserved</p>
        </div>
      </footer>
    </main>
  )
}
