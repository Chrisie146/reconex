'use client'

import { useEffect, useRef, useState } from 'react'

const transactions = [
  { date: '2026-01-15', desc: 'WOOLWORTHS FOOD', amount: -892.50, category: 'Groceries', catColor: 'bg-emerald-100 text-emerald-700' },
  { date: '2026-01-15', desc: 'SALARY DEPOSIT', amount: 35000.00, category: 'Salary', catColor: 'bg-blue-100 text-blue-700' },
  { date: '2026-01-14', desc: 'ENGEN GARAGE', amount: -650.00, category: 'Fuel', catColor: 'bg-amber-100 text-amber-700' },
  { date: '2026-01-14', desc: 'CITY OF CPT ELECTRICITY', amount: -1245.80, category: 'Utilities', catColor: 'bg-purple-100 text-purple-700' },
  { date: '2026-01-13', desc: 'VODACOM AIRTIME', amount: -199.00, category: 'Telecom', catColor: 'bg-pink-100 text-pink-700' },
]

const categories = [
  { name: 'Groceries', amount: 8640, pct: 72, color: 'bg-emerald-500' },
  { name: 'Fuel', amount: 3200, pct: 27, color: 'bg-amber-500' },
  { name: 'Utilities', amount: 4890, pct: 41, color: 'bg-purple-500' },
  { name: 'Insurance', amount: 2100, pct: 18, color: 'bg-blue-500' },
  { name: 'Bank Fees', amount: 450, pct: 4, color: 'bg-neutral-500' },
]

export default function Screenshots() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.08 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <section className="py-28 bg-white relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-blue-100/30 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-100 mb-5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-emerald-600">
              Preview
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-neutral-900 mb-4 tracking-tight">
            What you&apos;ll actually see
          </h2>
          <p className="text-base sm:text-lg text-neutral-500 max-w-xl mx-auto leading-relaxed">
            A clean dashboard built for speed and clarity. No clutter.
          </p>
        </div>

        {/* Browser frame with glow */}
        <div
          ref={ref}
          className={`relative rounded-2xl overflow-hidden transition-all duration-1000 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
          }`}
        >
          {/* Glow behind the frame */}
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/20 via-indigo-500/20 to-purple-500/20 rounded-3xl blur-2xl opacity-60" />

          <div className="relative rounded-2xl ring-1 ring-neutral-200/80 shadow-2xl shadow-neutral-300/40 overflow-hidden">
            {/* Title bar */}
            <div className="bg-neutral-900 px-4 py-3 flex items-center">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <div className="mx-auto flex items-center gap-2">
                <div className="flex items-center gap-1.5 px-4 py-1 rounded-md bg-neutral-800/80 border border-neutral-700/50">
                  <div className="w-3 h-3 rounded-full bg-emerald-500/40 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  </div>
                  <span className="text-neutral-400 text-xs font-mono">app.reconex.co.za/dashboard</span>
                </div>
              </div>
            </div>

            {/* Dashboard content */}
            <div className="bg-gradient-to-br from-neutral-50 to-white p-5 sm:p-8">
              {/* Summary row */}
              <div className="grid grid-cols-3 gap-4 mb-5">
                {[
                  { label: 'Total Income', value: 'R 45,230.00', color: 'text-emerald-600', bg: 'bg-gradient-to-br from-emerald-50 to-emerald-100/50', ring: 'ring-emerald-200/60', icon: '↑' },
                  { label: 'Total Expenses', value: 'R 32,150.30', color: 'text-red-600', bg: 'bg-gradient-to-br from-red-50 to-red-100/50', ring: 'ring-red-200/60', icon: '↓' },
                  { label: 'Net Balance', value: 'R 13,079.70', color: 'text-blue-600', bg: 'bg-gradient-to-br from-blue-50 to-blue-100/50', ring: 'ring-blue-200/60', icon: '=' },
                ].map((card, i) => (
                  <div
                    key={card.label}
                    className={`rounded-xl ring-1 ${card.ring} p-4 ${card.bg} transition-all duration-700 ${
                      visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
                    }`}
                    style={{ transitionDelay: `${300 + i * 100}ms` }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] text-neutral-500 uppercase tracking-wider">{card.label}</span>
                    </div>
                    <div className={`text-lg sm:text-xl font-bold ${card.color}`}>{card.value}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
                {/* Transactions table */}
                <div className="lg:col-span-3 bg-white rounded-xl ring-1 ring-neutral-200/80 overflow-hidden shadow-sm">
                  <div className="px-5 py-3.5 border-b border-neutral-100 flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-widest text-neutral-400">Recent Transactions</span>
                    <div className="flex gap-1">
                      <div className="w-6 h-6 rounded bg-neutral-100 flex items-center justify-center text-neutral-400 text-[10px]">⋮</div>
                    </div>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[11px] uppercase tracking-wider text-neutral-400 border-b border-neutral-100 bg-neutral-50/50">
                        <th className="px-5 py-2.5 font-medium">Date</th>
                        <th className="px-5 py-2.5 font-medium">Description</th>
                        <th className="px-5 py-2.5 font-medium text-right">Amount</th>
                        <th className="px-5 py-2.5 font-medium">Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx, i) => (
                        <tr
                          key={i}
                          className={`border-b border-neutral-50 hover:bg-blue-50/30 transition-all duration-500 ${
                            visible ? 'opacity-100' : 'opacity-0'
                          }`}
                          style={{ transitionDelay: `${600 + i * 100}ms` }}
                        >
                          <td className="px-5 py-3 text-neutral-400 font-mono text-xs">{tx.date}</td>
                          <td className="px-5 py-3 text-neutral-700 font-medium text-[13px]">{tx.desc}</td>
                          <td className={`px-5 py-3 text-right font-mono text-xs font-semibold ${tx.amount >= 0 ? 'text-emerald-600' : 'text-neutral-700'}`}>
                            {tx.amount >= 0 ? '+' : '-'} R {Math.abs(tx.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="px-5 py-3">
                            <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${tx.catColor}`}>
                              {tx.category}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Category breakdown */}
                <div className="lg:col-span-2 bg-white rounded-xl ring-1 ring-neutral-200/80 p-5 shadow-sm">
                  <div className="mb-5">
                    <span className="text-[11px] font-bold uppercase tracking-widest text-neutral-400">Expense Categories</span>
                  </div>
                  <div className="space-y-4">
                    {categories.map((cat, i) => (
                      <div
                        key={cat.name}
                        className={`transition-all duration-700 ${
                          visible ? 'opacity-100' : 'opacity-0'
                        }`}
                        style={{ transitionDelay: `${800 + i * 80}ms` }}
                      >
                        <div className="flex justify-between text-xs mb-1.5">
                          <span className="text-neutral-600 font-medium">{cat.name}</span>
                          <span className="text-neutral-400 font-mono font-semibold">R {cat.amount.toLocaleString()}</span>
                        </div>
                        <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${cat.color} rounded-full transition-all duration-1000 ease-out`}
                            style={{
                              width: visible ? `${cat.pct}%` : '0%',
                              transitionDelay: `${900 + i * 80}ms`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
