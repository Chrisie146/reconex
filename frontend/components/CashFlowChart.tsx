'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, ArrowDown, ArrowUp, Activity } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

import { API_BASE_URL } from '@/lib/apiBase'

interface CashFlowChartProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface CashFlowPoint {
  date: string
  balance: number
  daily_income: number
  daily_expenses: number
}

const fmtCurrency = (v: number) => {
  const sign = v < 0 ? '-' : ''
  return `${sign}R ${Math.abs(v).toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload as CashFlowPoint
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-neutral-700 mb-1">{d.date}</p>
      <p className={`font-bold ${d.balance >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
        Balance: {fmtCurrency(d.balance)}
      </p>
      {d.daily_income > 0 && (
        <p className="text-emerald-500">+ Income: {fmtCurrency(d.daily_income)}</p>
      )}
      {d.daily_expenses > 0 && (
        <p className="text-red-500">- Expenses: {fmtCurrency(d.daily_expenses)}</p>
      )}
    </div>
  )
}

export default function CashFlowChart({ sessionId, currentClient }: CashFlowChartProps) {
  const [data, setData] = useState<CashFlowPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [minBal, setMinBal] = useState(0)
  const [maxBal, setMaxBal] = useState(0)
  const [openingBal, setOpeningBal] = useState(0)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: any = {}
        if (currentClient?.id) params.client_id = currentClient.id
        else if (sessionId) params.session_id = sessionId
        else { setLoading(false); return }

        const res = await axios.get(`${API_BASE_URL}/analytics/cashflow`, { params })
        setData(res.data.series || [])
        setMinBal(res.data.min_balance || 0)
        setMaxBal(res.data.max_balance || 0)
        setOpeningBal(res.data.opening_balance || 0)
      } catch (e) {
        console.error('Failed to fetch cash flow:', e)
        setData([])
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

  if (data.length === 0) return null

  const lastBalance = data[data.length - 1]?.balance ?? 0
  const balChange = lastBalance - openingBal

  return (
    <div className="rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-100">
            <Activity className="w-4 h-4 text-cyan-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Cash Flow</h3>
            <p className="text-[11px] text-neutral-500">Daily running balance over time</p>
          </div>
        </div>

        {/* KPI chips */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[10px] text-neutral-400 uppercase tracking-wide">Current</p>
            <p className={`text-sm font-bold ${lastBalance >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {fmtCurrency(lastBalance)}
            </p>
          </div>
          <div className="h-8 w-px bg-neutral-200" />
          <div className="text-right">
            <p className="text-[10px] text-neutral-400 uppercase tracking-wide">Min</p>
            <p className={`text-xs font-semibold ${minBal >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {fmtCurrency(minBal)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-neutral-400 uppercase tracking-wide">Max</p>
            <p className="text-xs font-semibold text-emerald-600">{fmtCurrency(maxBal)}</p>
          </div>
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
            balChange >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
          }`}>
            {balChange >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
            {fmtCurrency(Math.abs(balChange))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="px-4 py-4">
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="cashFlowGradientPos" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="cashFlowGradientNeg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#EF4444" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#9CA3AF' }}
              tickLine={false}
              axisLine={{ stroke: '#E5E7EB' }}
              tickFormatter={(v) => {
                const d = new Date(v)
                return `${d.getDate()}/${d.getMonth() + 1}`
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#9CA3AF' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `R${(v / 1000).toFixed(0)}k`}
              width={55}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="#D1D5DB" strokeDasharray="4 4" />
            <Area
              type="monotone"
              dataKey="balance"
              stroke="#4F46E5"
              strokeWidth={2}
              fill="url(#cashFlowGradientPos)"
              dot={false}
              activeDot={{ r: 4, fill: '#4F46E5', stroke: '#fff', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
