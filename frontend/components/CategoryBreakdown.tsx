'use client'

import { useEffect, useState } from 'react'
import { BarChart3, TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import axios from '@/lib/axiosClient'
import CategoryTransactionsModal from './CategoryTransactionsModal'
import MonthlyTransactionsModal from './MonthlyTransactionsModal'
import type { Client } from '@/lib/clientContext'

import { API_BASE_URL } from '@/lib/apiBase'

interface CategoryBreakdownProps {
  sessionId: string | null
  currentClient?: Client | null
}

interface MonthData {
  month: string
  total_income: number
  total_expenses: number
  net_balance: number
  categories: Record<string, number>
}

export default function CategoryBreakdown({ sessionId, currentClient }: CategoryBreakdownProps) {
  const [categories, setCategories] = useState<Record<string, number>>({})
  const [months, setMonths] = useState<MonthData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [showIncome, setShowIncome] = useState(true)
  const [showExpenses, setShowExpenses] = useState(true)
  const [isMonthModalOpen, setIsMonthModalOpen] = useState(false)
  const [selectedMonthData, setSelectedMonthData] = useState<{ month: string; data: MonthData } | null>(null)

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        // Priority: if currentClient selected, use client_id; otherwise use sessionId
        const params: any = {}
        if (currentClient?.id) {
          params.client_id = currentClient.id
        } else if (sessionId) {
          params.session_id = sessionId
        } else {
          setLoading(false)
          return
        }

        // Fetch transactions and monthly summary to properly categorize income vs expenses
        const [transactionsResponse, summaryResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/transactions`, { params }),
          axios.get(`${API_BASE_URL}/summary`, { params })
        ])
        
        // Calculate category totals from transactions, preserving sign
        const categoryTotals: Record<string, number> = {}
        const transactions = transactionsResponse.data.transactions || []
        
        transactions.forEach((txn: any) => {
          if (!categoryTotals[txn.category]) {
            categoryTotals[txn.category] = 0
          }
          categoryTotals[txn.category] += txn.amount
        })
        
        setCategories(categoryTotals)
        setMonths(summaryResponse.data.months || [])
      } catch (error) {
        console.error('Failed to fetch categories:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchCategories()
  }, [sessionId, currentClient?.id])

  if (loading) {
    return <div className="text-center py-8 text-neutral-600">Loading categories...</div>
  }

  // Separate income and expenses
  const incomeCategories: [string, number][] = []
  const expenseCategories: [string, number][] = []
  
  Object.entries(categories).forEach(([category, amount]) => {
    if (amount > 0) {
      incomeCategories.push([category, amount])
    } else if (amount < 0) {
      expenseCategories.push([category, Math.abs(amount)])
    }
  })

  // Sort by amount (descending)
  incomeCategories.sort((a, b) => b[1] - a[1])
  expenseCategories.sort((a, b) => b[1] - a[1])

  const totalIncome = incomeCategories.reduce((sum, [_, amount]) => sum + amount, 0)
  const totalExpenses = expenseCategories.reduce((sum, [_, amount]) => sum + amount, 0)

  // Get last two months for comparison
  const sortedMonths = [...months].sort((a, b) => b.month.localeCompare(a.month))
  const currentMonth = sortedMonths[0]
  const previousMonth = sortedMonths[1]

  // Helper to calculate month-over-month change
  const getMonthOverMonthChange = (category: string): { amount: number; percentage: number } | null => {
    if (!currentMonth || !previousMonth) return null
    
    const currentAmount = currentMonth.categories?.[category] || 0
    const previousAmount = previousMonth.categories?.[category] || 0
    
    if (previousAmount === 0) return null
    
    const change = currentAmount - previousAmount
    const percentage = (change / Math.abs(previousAmount)) * 100
    
    return { amount: change, percentage }
  }

  const colors = [
    'bg-blue-500',
    'bg-blue-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-rose-500',
    'bg-orange-500',
    'bg-amber-500',
  ]

  const CHART_COLORS = ['#3b82f6', '#6366f1', '#a855f7', '#ec4899', '#f43f5e', '#f97316', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6']

  // Prepare data for donut chart (top 7 expense categories + "Other")
  const donutData = (() => {
    const top = expenseCategories.slice(0, 7)
    const otherTotal = expenseCategories.slice(7).reduce((sum, [_, amt]) => sum + amt, 0)
    const data = top.map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
    if (otherTotal > 0) data.push({ name: 'Other', value: Math.round(otherTotal * 100) / 100 })
    return data
  })()

  // Prepare data for monthly bar chart - use pre-computed totals from backend
  const barData = [...months]
    .sort((a, b) => a.month.localeCompare(b.month))
    .map(m => ({
      month: m.month,
      Income: Math.round(m.total_income || 0),
      Expenses: Math.round(m.total_expenses || 0)
    }))

  const openCategory = (category: string) => {
    setSelectedCategory(category)
    setIsModalOpen(true)
  }

  const openMonth = (monthKey: string) => {
    const monthInfo = months.find(m => m.month === monthKey)
    if (monthInfo) {
      setSelectedMonthData({ month: monthKey, data: monthInfo })
      setIsMonthModalOpen(true)
    }
  }

  const renderCategoryRow = (category: string, amount: number, total: number, index: number, isIncome: boolean) => {
    const percentage = total > 0 ? (amount / total) * 100 : 0
    const momChange = getMonthOverMonthChange(category)
    
    return (
      <tr
        key={category}
        className="border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer group"
        onClick={() => openCategory(category)}
      >
        <td className="px-6 py-3">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${colors[index % colors.length]}`} />
            <span className="text-neutral-900 font-medium">{category}</span>
          </div>
        </td>
        <td className="text-right px-6 py-3">
          <div className={`font-semibold ${isIncome ? 'text-green-600' : 'text-neutral-900'}`}>
            R{amount.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
          </div>
        </td>
        <td className="px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-neutral-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full ${colors[index % colors.length]}`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
            <span className="text-neutral-600 text-sm font-medium min-w-[3rem] text-right">
              {percentage.toFixed(1)}%
            </span>
          </div>
        </td>
        <td className="text-right px-6 py-3">
          {momChange ? (
            <div className="flex items-center justify-end gap-1">
              {momChange.amount > 0 ? (
                <>
                  <TrendingUp className="w-4 h-4 text-red-500" />
                  <span className="text-red-600 text-sm font-medium">
                    +{Math.abs(momChange.percentage).toFixed(0)}%
                  </span>
                </>
              ) : (
                <>
                  <TrendingDown className="w-4 h-4 text-green-500" />
                  <span className="text-green-600 text-sm font-medium">
                    -{Math.abs(momChange.percentage).toFixed(0)}%
                  </span>
                </>
              )}
            </div>
          ) : (
            <span className="text-neutral-400 text-sm">-</span>
          )}
        </td>
      </tr>
    )
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-neutral-700" />
            <h3 className="font-bold text-neutral-900">Category Breakdown</h3>
          </div>
          {currentMonth && previousMonth && (
            <div className="text-xs text-neutral-600">
              Comparing {currentMonth.month} vs {previousMonth.month}
            </div>
          )}
        </div>
      </div>

      {/* Charts Section */}
      {(barData.length > 0 || donutData.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 border-b border-neutral-200">
          {/* Monthly Income vs Expenses Bar Chart */}
          {barData.length > 0 && (
            <div className="p-6 border-r border-neutral-200">
              <h4 className="text-sm font-semibold text-neutral-700 mb-3">Income vs Expenses by Month</h4>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `R${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => `R${Number(value).toLocaleString('en-ZA')}`} />
                  <Bar dataKey="Income" fill="#22c55e" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(data: any) => { if (data?.month) openMonth(data.month) }} />
                  <Bar dataKey="Expenses" fill="#ef4444" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(data: any) => { if (data?.month) openMonth(data.month) }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Expense Category Donut Chart */}
          {donutData.length > 0 && (
            <div className="p-6">
              <h4 className="text-sm font-semibold text-neutral-700 mb-3">Expense Distribution</h4>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                    dataKey="value"
                    onClick={(data: any) => {
                      if (data && data.name) {
                        openCategory(data.name)
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    {donutData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `R${Number(value).toLocaleString('en-ZA')}`} />
                  <Legend
                    layout="vertical"
                    verticalAlign="middle"
                    align="right"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => <span className="text-xs text-neutral-700">{String(value)}</span>}
                    onClick={(data: any) => {
                      if (data && data.value) {
                        openCategory(String(data.value))
                      }
                    }}
                    wrapperStyle={{ cursor: 'pointer' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        {/* Income Section */}
        {incomeCategories.length > 0 && (
          <div>
            <div
              className="px-6 py-3 bg-green-50 border-b border-green-100 flex items-center justify-between cursor-pointer hover:bg-green-100 transition-colors"
              onClick={() => setShowIncome(!showIncome)}
            >
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-600" />
                <h4 className="font-semibold text-green-900">Income</h4>
                <span className="text-sm text-green-700">
                  ({incomeCategories.length} {incomeCategories.length === 1 ? 'category' : 'categories'})
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-green-900">
                  R{totalIncome.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </span>
                {showIncome ? (
                  <ChevronUp className="w-4 h-4 text-green-600" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-green-600" />
                )}
              </div>
            </div>

            {showIncome && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 bg-neutral-50">
                    <th className="text-left px-6 py-3 font-medium text-neutral-700">Category</th>
                    <th className="text-right px-6 py-3 font-medium text-neutral-700">Amount</th>
                    <th className="text-left px-6 py-3 font-medium text-neutral-700">Share</th>
                    <th className="text-right px-6 py-3 font-medium text-neutral-700">vs Last Month</th>
                  </tr>
                </thead>
                <tbody>
                  {incomeCategories.map(([category, amount], index) => 
                    renderCategoryRow(category, amount, totalIncome, index, true)
                  )}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Expenses Section */}
        {expenseCategories.length > 0 && (
          <div>
            <div
              className="px-6 py-3 bg-red-50 border-b border-red-100 flex items-center justify-between cursor-pointer hover:bg-red-100 transition-colors"
              onClick={() => setShowExpenses(!showExpenses)}
            >
              <div className="flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-red-600" />
                <h4 className="font-semibold text-red-900">Expenses</h4>
                <span className="text-sm text-red-700">
                  ({expenseCategories.length} {expenseCategories.length === 1 ? 'category' : 'categories'})
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-red-900">
                  R{totalExpenses.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                </span>
                {showExpenses ? (
                  <ChevronUp className="w-4 h-4 text-red-600" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-red-600" />
                )}
              </div>
            </div>

            {showExpenses && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 bg-neutral-50">
                    <th className="text-left px-6 py-3 font-medium text-neutral-700">Category</th>
                    <th className="text-right px-6 py-3 font-medium text-neutral-700">Amount</th>
                    <th className="text-left px-6 py-3 font-medium text-neutral-700">Share</th>
                    <th className="text-right px-6 py-3 font-medium text-neutral-700">vs Last Month</th>
                  </tr>
                </thead>
                <tbody>
                  {expenseCategories.map(([category, amount], index) => 
                    renderCategoryRow(category, amount, totalExpenses, index, false)
                  )}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {incomeCategories.length === 0 && expenseCategories.length === 0 && (
        <div className="px-6 py-8 text-center text-neutral-600">
          No categories found
        </div>
      )}

      {selectedCategory && (sessionId || currentClient?.id) && (
        <CategoryTransactionsModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          sessionId={sessionId}
          currentClient={currentClient}
          category={selectedCategory}
        />
      )}

      {selectedMonthData && (
        <MonthlyTransactionsModal
          isOpen={isMonthModalOpen}
          onClose={() => setIsMonthModalOpen(false)}
          sessionId={sessionId}
          currentClient={currentClient}
          month={selectedMonthData.month}
          monthData={selectedMonthData.data}
        />
      )}
    </div>
  )
}
