'use client'

import { useEffect, useState } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

// Bank icons and display names
const BANK_CONFIG: Record<string, { name: string; emoji: string; color: string }> = {
  capitec: { name: 'Capitec Bank', emoji: '🏦', color: 'from-red-50 to-red-100 border-red-200' },
  absa: { name: 'ABSA', emoji: '🏛️', color: 'from-blue-50 to-blue-100 border-blue-200' },
  fnb: { name: 'FNB', emoji: '🏦', color: 'from-green-50 to-green-100 border-green-200' },
  standard_bank: { name: 'Standard Bank', emoji: '🏦', color: 'from-yellow-50 to-yellow-100 border-yellow-200' },
  default: { name: 'Bank', emoji: '🏦', color: 'from-gray-50 to-gray-100 border-gray-200' },
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
    
    return `${fromStr} – ${toStr}`
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
    <div className={`bg-gradient-to-r ${config.color} border rounded-lg p-4 mb-6`}>
      <div className="flex items-start gap-4">
        {/* Bank Icon */}
        <div className="text-4xl flex-shrink-0 mt-1">
          {config.emoji}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-gray-900">
              {statement.friendly_name}
            </h2>
          </div>
          
          <div className="mt-2 flex items-center gap-4 flex-wrap text-sm text-gray-700">
            {dateRange && (
              <div className="flex items-center gap-1">
                <span className="font-semibold">Period:</span>
                <span>{dateRange}</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <span className="font-semibold">Transactions:</span>
              <span className="bg-white px-2 py-0.5 rounded-full font-medium">
                {statement.transaction_count}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
