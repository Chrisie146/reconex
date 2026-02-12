'use client'

import { useEffect, useState } from 'react'
import axios from '@/lib/axiosClient'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Props {
  sessionId: string
}

export default function MonthlyCategoryComparison({ sessionId }: Props) {
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [series, setSeries] = useState<{ month: string; amount: number }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const resp = await axios.get(`${API_BASE_URL}/category-summary`, { params: { session_id: sessionId } })
        const cats = Object.keys(resp.data.categories || {})
        setCategories(cats)
        if (cats.length > 0) setSelectedCategory(cats[0])
      } catch (e) {
        console.error('Failed to load categories', e)
      }
    }
    fetchCategories()
  }, [sessionId])

  useEffect(() => {
    const fetchSeries = async () => {
      if (!selectedCategory) return
      setLoading(true)
      try {
        const resp = await axios.get(`${API_BASE_URL}/category-monthly`, { params: { session_id: sessionId, category: selectedCategory } })
        setSeries(resp.data.series || [])
      } catch (e) {
        console.error('Failed to fetch category series', e)
      } finally {
        setLoading(false)
      }
    }
    fetchSeries()
  }, [selectedCategory, sessionId])

  if (!selectedCategory) {
    return <div className="card p-4">No categories available</div>
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50 flex items-center justify-between">
        <h3 className="font-bold text-neutral-900">Month-to-Month: {selectedCategory}</h3>
        <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="px-2 py-1 border rounded">
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left px-6 py-3 font-medium text-neutral-700">Month</th>
              <th className="text-right px-6 py-3 font-medium text-neutral-700">Amount</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="px-6 py-4" colSpan={2}>Loading...</td></tr>
            ) : series.length === 0 ? (
              <tr><td className="px-6 py-4" colSpan={2}>No data</td></tr>
            ) : (
              series.map((s) => (
                <tr key={s.month} className="border-b border-neutral-100 hover:bg-neutral-50">
                  <td className="px-6 py-3 text-neutral-900">{s.month}</td>
                  <td className="text-right px-6 py-3 text-neutral-900">R{s.amount.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
