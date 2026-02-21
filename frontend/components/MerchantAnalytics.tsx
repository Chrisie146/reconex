'use client'

import { useEffect, useState } from 'react'
import { Store, ChevronDown, ChevronUp, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface MerchantAnalyticsProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface MerchantData {
  merchant: string
  count: number
  total: number
  average: number
  category: string
  last_seen: string
  trend: { month: string; amount: number }[]
}

const fmtCurrency = (v: number) =>
  `R ${v.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const BAR_COLORS = [
  '#4F46E5', '#7C3AED', '#2563EB', '#0891B2', '#059669',
  '#D97706', '#DC2626', '#9333EA', '#0D9488', '#6366F1',
]

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-neutral-700 truncate max-w-[200px]">{d.merchant}</p>
      <p className="text-indigo-600 font-bold">{fmtCurrency(d.total)}</p>
      <p className="text-neutral-500">{d.count} transactions  ·  Avg {fmtCurrency(d.average)}</p>
    </div>
  )
}

export default function MerchantAnalytics({ sessionId, currentClient }: MerchantAnalyticsProps) {
  const [merchants, setMerchants] = useState<MerchantData[]>([])
  const [totalMerchants, setTotalMerchants] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [selectedMerchant, setSelectedMerchant] = useState<MerchantData | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: any = { top_n: 20 }
        if (currentClient?.id) params.client_id = currentClient.id
        else if (sessionId) params.session_id = sessionId
        else { setLoading(false); return }

        const res = await axios.get(`${API_BASE_URL}/analytics/merchants`, { params })
        setMerchants(res.data.merchants || [])
        setTotalMerchants(res.data.total_merchants || 0)
      } catch (e) {
        console.error('Failed to fetch merchant analytics:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [sessionId, currentClient?.id])

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-5 w-48 bg-neutral-200 rounded" />
          <div className="h-48 bg-neutral-100 rounded" />
        </div>
      </div>
    )
  }

  if (merchants.length === 0) return null

  const top10 = merchants.slice(0, 10)
  const chartData = top10.map((m) => ({
    ...m,
    merchant: m.merchant.length > 18 ? m.merchant.slice(0, 16) + '…' : m.merchant,
    fullName: m.merchant,
  }))

  const visibleMerchants = expanded ? merchants : merchants.slice(0, 10)

  return (
    <div className="rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-100">
            <Store className="w-4 h-4 text-violet-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Merchant Analytics</h3>
            <p className="text-[11px] text-neutral-500">
              Top spending by merchant  ·  {totalMerchants} unique merchants
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-neutral-100">
        {/* Bar Chart */}
        <div className="p-4">
          <p className="text-xs font-medium text-neutral-500 mb-3">Top 10 Merchants by Spend</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
              <XAxis
                type="number"
                tick={{ fontSize: 9, fill: '#9CA3AF' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `R${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                type="category"
                dataKey="merchant"
                tick={{ fontSize: 9, fill: '#6B7280' }}
                tickLine={false}
                axisLine={false}
                width={120}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="total" radius={[0, 4, 4, 0]} barSize={20}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Table */}
        <div className="p-4">
          <p className="text-xs font-medium text-neutral-500 mb-3">Merchant Details</p>
          <div className="overflow-y-auto max-h-[320px]">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[10px] text-neutral-400 uppercase tracking-wider border-b border-neutral-100">
                  <th className="pb-2 pr-2">Merchant</th>
                  <th className="pb-2 pr-2 text-right">Total</th>
                  <th className="pb-2 pr-2 text-right">Count</th>
                  <th className="pb-2 text-right">Avg</th>
                </tr>
              </thead>
              <tbody>
                {visibleMerchants.map((m, i) => (
                  <tr
                    key={i}
                    className={`border-b border-neutral-50 hover:bg-indigo-50 cursor-pointer transition-colors ${
                      selectedMerchant?.merchant === m.merchant ? 'bg-indigo-50' : ''
                    }`}
                    onClick={() => setSelectedMerchant(selectedMerchant?.merchant === m.merchant ? null : m)}
                  >
                    <td className="py-2 pr-2">
                      <p className="font-medium text-neutral-800 truncate max-w-[130px]">{m.merchant}</p>
                      <p className="text-[10px] text-neutral-400">{m.category}</p>
                    </td>
                    <td className="py-2 pr-2 text-right font-semibold text-neutral-700">
                      {fmtCurrency(m.total)}
                    </td>
                    <td className="py-2 pr-2 text-right text-neutral-500">{m.count}</td>
                    <td className="py-2 text-right text-neutral-500">{fmtCurrency(m.average)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {merchants.length > 10 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? 'Show less' : `Show all ${merchants.length} merchants`}
            </button>
          )}
        </div>
      </div>

      {/* Selected Merchant Detail (Monthly Trend) */}
      {selectedMerchant && selectedMerchant.trend.length > 1 && (
        <div className="border-t border-neutral-100 px-5 py-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-3.5 h-3.5 text-indigo-500" />
            <p className="text-xs font-medium text-neutral-700">
              Monthly trend for <span className="font-bold">{selectedMerchant.merchant}</span>
            </p>
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={selectedMerchant.trend} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="month"
                tick={{ fontSize: 9, fill: '#9CA3AF' }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 9, fill: '#9CA3AF' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `R${(v / 1000).toFixed(0)}k`}
                width={50}
              />
              <Tooltip
                formatter={(v: number) => [fmtCurrency(v), 'Amount']}
                contentStyle={{ fontSize: 11, borderRadius: 8 }}
              />
              <Bar dataKey="amount" fill="#4F46E5" radius={[4, 4, 0, 0]} barSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
