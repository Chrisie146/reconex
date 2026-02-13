'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronLeft, ChevronRight, BarChart3, Upload, MapPin, List, Archive, Settings, Eye, Tag, Zap, Sparkles, Download, FileText, FileSpreadsheet, FolderOpen, ChevronDown, ChevronUp, Receipt, Users } from 'lucide-react'
import axios from '@/lib/axiosClient'
import ClientSelector from './ClientSelector'
import StatementSelector from './StatementSelector'
import VATExportModal from './VATExportModal'
import CategoriesExportModal from './CategoriesExportModal'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface SidebarProps {
  sessionId: string | null
  selectedStatement?: string
  onStatementChange?: (statementId: string) => void
}

export default function Sidebar({ sessionId, selectedStatement = '', onStatementChange }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isMounted, setIsMounted] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportsExpanded, setExportsExpanded] = useState(false)
  const [configExpanded, setConfigExpanded] = useState(false)
  const [generalExpanded, setGeneralExpanded] = useState(false)
  const [currentBankEmoji, setCurrentBankEmoji] = useState<string>('🏦')
  const [showVATModal, setShowVATModal] = useState(false)
  const [showCategoriesModal, setShowCategoriesModal] = useState(false)
  const pathname = usePathname()

  // Bank emoji mapping
  const getBankEmoji = (friendlyName: string): string => {
    const lower = friendlyName.toLowerCase()
    if (lower.includes('capitec')) return '🏦'
    if (lower.includes('absa')) return '🏛️'
    if (lower.includes('fnb')) return '🏦'
    if (lower.includes('standard bank')) return '🏦'
    return '🏦'
  }

  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Fetch and display current statement's bank emoji when selected
  useEffect(() => {
    const fetchStatementBank = async () => {
      if (!selectedStatement) {
        setCurrentBankEmoji('🏦')
        return
      }

      try {
        const response = await axios.get(`${API_BASE_URL}/sessions`)
        const sessions = response.data.sessions || []
        const found = sessions.find((s: any) => s.session_id === selectedStatement)
        
        if (found) {
          setCurrentBankEmoji(getBankEmoji(found.friendly_name))
        }
      } catch (error) {
        console.error('Failed to fetch statement for sidebar:', error)
        setCurrentBankEmoji('🏦')
      }
    }

    fetchStatementBank()
  }, [selectedStatement])

  const handleExport = async (type: 'transactions' | 'summary' | 'categories' | 'accountant' | 'vat') => {
    if (!sessionId) return
    
    // For VAT export, open modal instead
    if (type === 'vat') {
      setShowVATModal(true)
      return
    }
    
    // For categories export, open modal instead
    if (type === 'categories') {
      setShowCategoriesModal(true)
      return
    }
    
    setExporting(true)
    try {
      let endpoint: string
      let filename: string
      
      endpoint = `${API_BASE_URL}/export/${type}`
      filename = `${type}_${sessionId?.substring(0, 8) || 'export'}.xlsx`
      
      const response = await axios.get(endpoint, {
        params: { session_id: sessionId, format: 'excel' },
        responseType: 'blob',
      })

      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const isActive = (path: string) => {
    if (path === '/dashboard' && pathname === '/dashboard') return true
    if (path !== '/dashboard' && pathname.startsWith(path)) return true
    return false
  }

  const getLinkClass = (path: string) => {
    const baseClass = "flex items-center space-x-3 p-3 rounded transition-colors"
    const hoverClass = "hover:bg-gray-700"
    const activeClass = isActive(path) ? "bg-blue-600 hover:bg-blue-700" : hoverClass
    return `${baseClass} ${activeClass}`
  }

  const getExportButtonClass = () => {
    const baseClass = "flex items-center space-x-3 p-3 rounded transition-colors w-full text-left"
    const hoverClass = exporting ? "bg-gray-600 cursor-not-allowed" : "hover:bg-gray-700 cursor-pointer"
    return `${baseClass} ${hoverClass}`
  }

  return (
    <div className={`fixed left-0 top-0 h-full bg-gray-900 text-white transition-all duration-300 ${
      isCollapsed ? 'w-16' : 'w-64'
    } z-50 flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
        {!isCollapsed && (
          <h2 className="text-lg font-semibold">Navigation</h2>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded hover:bg-gray-700 transition-colors"
        >
          {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {/* Client & Statements Section - Sticky at top for quick access */}
      <div className={`sticky top-0 bg-gray-900 border-b border-gray-700 flex-shrink-0 z-40 transition-all duration-300 ${
        isCollapsed ? 'w-16' : 'w-full'
      }`}>
        <div className={`px-4 py-4 border-b border-gray-700 ${isCollapsed ? 'hidden' : ''}`}>
          <p className="text-xs font-semibold text-gray-400 mb-3">CLIENT</p>
          {isMounted && <ClientSelector isDarkMode={true} isCollapsed={isCollapsed} />}
        </div>

        {/* Statements Section - Show full selector when expanded, bank emoji when collapsed */}
        {isMounted && !isCollapsed && (
          <div className="px-0 py-2">
            <StatementSelector
              selectedStatement={selectedStatement}
              onStatementChange={onStatementChange || (() => {})}
              isCollapsed={isCollapsed}
            />
          </div>
        )}

        {/* Bank indicator when sidebar is collapsed */}
        {isMounted && isCollapsed && selectedStatement && (
          <div className="flex items-center justify-center py-3 border-b border-gray-700">
            <div title="Current bank" className="text-2xl cursor-help">
              {currentBankEmoji}
            </div>
          </div>
        )}
      </div>

      {/* Navigation Items - Scrollable */}
      <nav className={`p-4 space-y-2 overflow-y-auto flex-1 overflow-x-hidden ${isCollapsed ? 'px-2' : ''}`}>
        <Link
          href="/dashboard"
          className={getLinkClass("/dashboard")}
        >
          <Upload size={20} />
          {!isCollapsed && <span>Upload Statement</span>}
        </Link>

        {isMounted && sessionId && (
          <>
            <div className="pt-2 border-t border-gray-700">
              <p className="px-3 py-2 text-xs font-semibold text-gray-400">{isCollapsed ? '' : 'SESSION'}</p>
            </div>

            <Link
              href={`/dashboard?session_id=${sessionId}`}
              className={getLinkClass("/dashboard")}
            >
              <BarChart3 size={20} />
              {!isCollapsed && <span>Dashboard</span>}
            </Link>

            <Link
              href={`/transactions?session_id=${sessionId}`}
              className={getLinkClass("/transactions")}
            >
              <List size={20} />
              {!isCollapsed && <span>Transactions</span>}
            </Link>

            <Link
              href={`/invoices?session_id=${sessionId}`}
              className={getLinkClass("/invoices")}
            >
              <Eye size={20} />
              {!isCollapsed && <span>Invoices</span>}
            </Link>

            <Link
              href={`/mapping?session_id=${sessionId}`}
              className={getLinkClass("/mapping")}
            >
              <MapPin size={20} />
              {!isCollapsed && <span>Map Transactions</span>}
            </Link>

            {/* OCR Settings - Hidden for now, will be corrected later
            <Link
              href={`/ocr?session_id=${sessionId}`}
              className={getLinkClass("/ocr")}
            >
              <Settings size={20} />
              {!isCollapsed && <span>OCR Settings</span>}
            </Link>
            */}

            <div className="pt-2 border-t border-gray-700">
              <button
                onClick={() => setExportsExpanded(!exportsExpanded)}
                className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-gray-400 hover:text-white transition-colors cursor-pointer"
              >
                <span>{isCollapsed ? '' : 'EXPORTS'}</span>
                {!isCollapsed && (
                  exportsExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                )}
              </button>
            </div>

            {exportsExpanded && (
              <>
                <button
                  onClick={() => handleExport('accountant')}
                  disabled={exporting}
                  className={getExportButtonClass()}
                  title="Comprehensive report for accountants"
                >
                  <FileSpreadsheet size={20} className={exporting ? 'opacity-50' : ''} />
                  {!isCollapsed && <span className={exporting ? 'opacity-50' : ''}>For Accountant</span>}
                </button>

                <button
                  onClick={() => handleExport('transactions')}
                  disabled={exporting}
                  className={getExportButtonClass()}
                  title="All transactions"
                >
                  <FileText size={20} className={exporting ? 'opacity-50' : ''} />
                  {!isCollapsed && <span className={exporting ? 'opacity-50' : ''}>Transactions</span>}
                </button>

                <button
                  onClick={() => handleExport('summary')}
                  disabled={exporting}
                  className={getExportButtonClass()}
                  title="Monthly summary"
                >
                  <BarChart3 size={20} className={exporting ? 'opacity-50' : ''} />
                  {!isCollapsed && <span className={exporting ? 'opacity-50' : ''}>Summary</span>}
                </button>

                <button
                  onClick={() => handleExport('categories')}
                  disabled={exporting}
                  className={getExportButtonClass()}
                  title="By category"
                >
                  <FolderOpen size={20} className={exporting ? 'opacity-50' : ''} />
                  {!isCollapsed && <span className={exporting ? 'opacity-50' : ''}>Categories</span>}
                </button>

                <button
                  onClick={() => handleExport('vat')}
                  disabled={exporting}
                  className={getExportButtonClass()}
                  title="VAT report with calculations"
                >
                  <Receipt size={20} className={exporting ? 'opacity-50' : ''} />
                  {!isCollapsed && <span className={exporting ? 'opacity-50' : ''}>VAT Report</span>}
                </button>
              </>
            )}

            <div className="pt-2 border-t border-gray-700">
              <button
                onClick={() => setConfigExpanded(!configExpanded)}
                className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-gray-400 hover:text-white transition-colors cursor-pointer"
              >
                <span>{isCollapsed ? '' : 'CONFIGURATION'}</span>
                {!isCollapsed && (
                  configExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                )}
              </button>
            </div>

            {configExpanded && (
              <>
                <Link
                  href={`/rules?session_id=${sessionId}`}
                  className={getLinkClass("/rules")}
                >
                  <Tag size={20} />
                  {!isCollapsed && <span>Categories</span>}
                </Link>

                <Link
                  href={`/rules?session_id=${sessionId}&tab=rules`}
                  className={getLinkClass("/rules")}
                >
                  <Zap size={20} />
                  {!isCollapsed && <span>Manual Rules</span>}
                </Link>

                <Link
                  href={`/rules?session_id=${sessionId}&tab=learned`}
                  className={getLinkClass("/rules")}
                >
                  <Sparkles size={20} />
                  {!isCollapsed && <span>Learned Patterns</span>}
                </Link>
              </>
            )}
          </>
        )}

        <div className="pt-2 border-t border-gray-700">
          <button
            onClick={() => setGeneralExpanded(!generalExpanded)}
            className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            <span>{isCollapsed ? '' : 'MORE'}</span>
            {!isCollapsed && (
              generalExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
            )}
          </button>
        </div>

        {generalExpanded && (
          <>
            <Link
              href="/clients"
              className={getLinkClass("/clients")}
            >
              <Users size={20} />
              {!isCollapsed && <span>Clients</span>}
            </Link>
            <Link
              href="/sessions"
              className={getLinkClass("/sessions")}
            >
              <Archive size={20} />
              {!isCollapsed && <span>All Statements</span>}
            </Link>
          </>
        )}
      </nav>

      {/* VAT Export Modal */}
      <VATExportModal
        isOpen={showVATModal}
        onClose={() => setShowVATModal(false)}
        sessionId={sessionId}
      />

      {/* Categories Export Modal */}
      <CategoriesExportModal
        isOpen={showCategoriesModal}
        onClose={() => setShowCategoriesModal(false)}
        sessionId={sessionId}
      />
    </div>
  )
}