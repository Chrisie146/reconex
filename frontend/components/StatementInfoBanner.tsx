'use client'

import { useEffect, useState } from 'react'
import axios from '@/lib/axiosClient'

import { API_BASE_URL } from '@/lib/apiBase'

interface StatementInfoBannerProps {
  selectedStatement: string
  sessionId?: string | null
}

interface Statement {
  session_id: string
  friendly_name: string
  transaction_count: number
  date_from?: string
  date_to?: string
}

const BANK_CONFIG: Record<string, { name: string }> = {
  capitec: { name: 'Capitec Bank' },
  absa: { name: 'ABSA' },
  fnb: { name: 'FNB' },
  standard_bank: { name: 'Standard Bank' },
  default: { name: 'Bank' },
}

function extractBankFromFriendlyName(friendlyName: string): string {
  const lowercase = friendlyName.toLowerCase()
  if (lowercase.includes('capitec')) return 'capitec'
  if (lowercase.includes('absa')) return 'absa'
  if (lowercase.includes('fnb')) return 'fnb'
  if (lowercase.includes('standard bank')) return 'standard_bank'
  return 'default'
}

function formatDateRange(dateFrom?: string, dateTo?: string): string {
  if (!dateFrom || !dateTo) return ''
  
  try {
    const from = new Date(dateFrom)
    const to = new Date(dateTo)
    
    const fromStr = from.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const toStr = to.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    
    return `${fromStr} - ${toStr}`
  } catch {
    return ''
  }
}

export default function StatementInfoBanner({ selectedStatement, sessionId }: StatementInfoBannerProps) {
  const [statement, setStatement] = useState<Statement | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchStatement = async () => {
      // Only fetch if we have a selectedStatement ID
      if (!selectedStatement) {
        setStatement(null)
        return
      }

      setLoading(true)
      try {
        // Fetch all sessions and find the one matching selectedStatement
        const response = await axios.get(`${API_BASE_URL}/sessions`)
        const sessions = response.data.sessions || []
        const found = sessions.find((s: Statement) => s.session_id === selectedStatement)
        
        if (found) {
          setStatement(found)
        }
      } catch (error) {
        console.error('[StatementInfoBanner] Failed to fetch statement:', error)
        setStatement(null)
      } finally {
        setLoading(false)
      }
    }

    fetchStatement()
  }, [selectedStatement])

  if (!statement) {
    return null
  }

  const bankType = extractBankFromFriendlyName(statement.friendly_name)
  const config = BANK_CONFIG[bankType] || BANK_CONFIG.default
  const dateRange = formatDateRange(statement.date_from, statement.date_to)

  return (
    <div className="mb-2 border-b border-neutral-200 bg-white px-1 py-2 dark:border-neutral-800 dark:bg-neutral-950">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <h2 className="text-base font-semibold text-neutral-950 dark:text-neutral-50">
          {statement.friendly_name}
        </h2>
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {config.name}
        </span>
        {dateRange && (
          <span className="text-neutral-600 dark:text-neutral-400">
            Period <span className="font-medium text-neutral-800 dark:text-neutral-200">{dateRange}</span>
          </span>
        )}
        <span className="text-neutral-600 dark:text-neutral-400">
          Transactions <span className="font-medium text-neutral-800 dark:text-neutral-200">{statement.transaction_count}</span>
        </span>
      </div>
    </div>
  )
}
