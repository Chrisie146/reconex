'use client'

import { useState, useEffect } from 'react'
import axios from '@/lib/axiosClient'
import { ChevronDown, ChevronUp, Settings } from 'lucide-react'
import Link from 'next/link'
import { useClient } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface StatementSelectorProps {
  selectedStatement: string
  onStatementChange: (statementId: string) => void
  isCollapsed: boolean
}

interface Statement {
  session_id: string
  friendly_name: string
  transaction_count: number
}

export default function StatementSelector({ selectedStatement, onStatementChange, isCollapsed }: StatementSelectorProps) {
  const [statements, setStatements] = useState<Statement[]>([])
  const [loadingStatements, setLoadingStatements] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const { currentClient } = useClient()

  // Fetch statements when client changes
  useEffect(() => {
    const fetchStatements = async () => {
      if (!currentClient?.id) {
        console.log('[StatementSelector] No client, clearing statements')
        setStatements([])
        onStatementChange('')
        return
      }

      console.log('[StatementSelector] Fetching statements for client:', currentClient.id)
      setLoadingStatements(true)
      try {
        const response = await axios.get(`${API_BASE_URL}/sessions`, {
          params: { client_id: currentClient.id }
        })
        console.log('[StatementSelector] Fetched statements:', response.data.sessions)
        setStatements(response.data.sessions || [])
      } catch (error) {
        console.error('[StatementSelector] Failed to fetch statements:', error)
        setStatements([])
      } finally {
        setLoadingStatements(false)
      }
    }

    fetchStatements()
  }, [currentClient?.id, onStatementChange])

  if (!currentClient?.id) {
    return null
  }

  const getDisplayName = (statement: Statement) => {
    return `${statement.friendly_name} (${statement.transaction_count} txns)`
  }

  const selectedStatementObj = statements.find(s => s.session_id === selectedStatement)
  const displayText = selectedStatement 
    ? getDisplayName(selectedStatementObj || statements[0])
    : `All Statements (${statements.reduce((sum, s) => sum + s.transaction_count, 0)} txns)`

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-semibold text-gray-400">STATEMENTS</span>
        <Link
          href="/sessions"
          className="p-1 rounded hover:bg-gray-700 transition-colors"
          title="Manage statements"
        >
          <Settings size={14} className="text-gray-400 hover:text-white" />
        </Link>
      </div>

      <div className="px-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          disabled={loadingStatements || statements.length <= 1}
          className={`w-full text-sm px-3 py-2 border border-gray-700 rounded-md bg-gray-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
            loadingStatements || statements.length <= 1
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:bg-gray-700 cursor-pointer'
          }`}
        >
          <div className="flex items-center justify-between">
            {!isCollapsed ? (
              <span className="truncate text-left">{displayText}</span>
            ) : (
              <span className="text-xs">📄</span>
            )}
            {!isCollapsed && !loadingStatements && statements.length > 1 && (
              isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
            )}
          </div>
        </button>

        {isExpanded && statements.length > 1 && (
          <div className="mt-1 bg-gray-800 border border-gray-700 rounded-md shadow-lg">
            <button
              onClick={() => {
                onStatementChange('')
                setIsExpanded(false)
              }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors first:rounded-t-md ${
                !selectedStatement ? 'bg-blue-600' : ''
              }`}
            >
              All Statements ({statements.reduce((sum, s) => sum + s.transaction_count, 0)} txns)
            </button>
            {statements.map((stmt) => (
              <button
                key={stmt.session_id}
                onClick={() => {
                  onStatementChange(stmt.session_id)
                  setIsExpanded(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 transition-colors ${
                  selectedStatement === stmt.session_id ? 'bg-blue-600' : ''
                }`}
              >
                {getDisplayName(stmt)}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
