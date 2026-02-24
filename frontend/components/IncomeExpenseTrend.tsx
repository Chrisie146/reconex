'use client'

import { useEffect, useState } from 'react'
import { TrendingUp } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from 'recharts'
import axios from '@/lib/axiosClient'
import type { Client } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface IncomeExpenseTrendProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface MonthTrend {
  month: string
  income: number
  expenses: number
  net: number
}

const fmtCurrency = (v: number) =>
  `R ${Math.abs(v).toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-neutral-700 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
          {p.name}: {fmtCurrency(p.value)}
        </p>
      ))}
    </div>
  )
}

export default function IncomeExpenseTrend({ sessionId, currentClient }: IncomeExpenseTrendProps) {
  const [data, setData] = useState<MonthTrend[]>([])
  const [loading, setLoading] = useState(true)
  const [showIncome, setShowIncome] = useState(true)
  const [showExpenses, setShowExpenses] = useState(true)
  const [showNet, setShowNet] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: any = {}
        if (currentClient?.id) params.client_id = currentClient.id
        else if (sessionId) params.session_id = sessionId
        else { setLoading(false); return }

        const res = await axios.get(`${API_BASE_URL}/summary`, { params })
        const months = res.data.months || []
        const trend: MonthTrend[] = months.map((m: any) => ({
          month: m.month,
          income: m.total_income,
          expenses: m.total_expenses,
          net: m.net_balance,
        }))
        setData(trend)
      } catch (e) {
        console.error('Failed to fetch trend data:', e)
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

  if (data.length < 2) return null // Need at least 2 months for a trend

  return (
    <div className="rounded-xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100">
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Income & Expense Trend</h3>
            <p className="text-[11px] text-neutral-500">Month-over-month trend lines</p>
          </div>
        </div>

        {/* Toggle pills */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowIncome(!showIncome)}
            className={`flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium transition-colors ${
              showIncome ? 'bg-emerald-100 text-emerald-700' : 'bg-neutral-50 text-neutral-400'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Income
          </button>
          <button
            onClick={() => setShowExpenses(!showExpenses)}
            className={`flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium transition-colors ${
              showExpenses ? 'bg-red-100 text-red-700' : 'bg-neutral-50 text-neutral-400'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Expenses
          </button>
          <button
            onClick={() => setShowNet(!showNet)}
            className={`flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium transition-colors ${
              showNet ? 'bg-blue-100 text-blue-700' : 'bg-neutral-50 text-neutral-400'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            Net
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="px-4 py-4">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: '#9CA3AF' }}
              tickLine={false}
              axisLine={{ stroke: '#E5E7EB' }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#9CA3AF' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `R${(v / 1000).toFixed(0)}k`}
              width={55}
            />
            <Tooltip content={<CustomTooltip />} />
            {showIncome && (
              <Line
                type="monotone"
                dataKey="income"
                name="Income"
                stroke="#10B981"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#10B981', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#10B981', stroke: '#fff', strokeWidth: 2 }}
              />
            )}
            {showExpenses && (
              <Line
                type="monotone"
                dataKey="expenses"
                name="Expenses"
                stroke="#EF4444"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#EF4444', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#EF4444', stroke: '#fff', strokeWidth: 2 }}
              />
            )}
            {showNet && (
              <Line
                type="monotone"
                dataKey="net"
                name="Net Balance"
                stroke="#4F46E5"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={{ r: 3, fill: '#4F46E5', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 5, fill: '#4F46E5', stroke: '#fff', strokeWidth: 2 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
