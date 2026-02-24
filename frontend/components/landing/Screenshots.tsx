'use client'

import { useEffect, useRef, useState } from 'react'

const transactions = [
  { date: '2026-01-15', desc: 'WOOLWORTHS FOOD', amount: -892.50, category: 'Groceries' },
  { date: '2026-01-15', desc: 'SALARY DEPOSIT', amount: 35000.00, category: 'Salary' },
  { date: '2026-01-14', desc: 'ENGEN GARAGE', amount: -650.00, category: 'Fuel' },
  { date: '2026-01-14', desc: 'CITY OF CPT ELECTRICITY', amount: -1245.80, category: 'Utilities' },
  { date: '2026-01-13', desc: 'VODACOM AIRTIME', amount: -199.00, category: 'Utilities' },
]

const categories = [
  { name: 'Groceries', amount: 8640, pct: 72 },
  { name: 'Fuel', amount: 3200, pct: 27 },
  { name: 'Utilities', amount: 4890, pct: 41 },
  { name: 'Insurance', amount: 2100, pct: 18 },
  { name: 'Bank Fees', amount: 450, pct: 4 },
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
      { threshold: 0.1 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-3">
            Preview
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            What you will actually see
          </h2>
          <p className="text-base text-neutral-500 max-w-xl mx-auto">
            A clean dashboard built for speed and clarity. No clutter.
          </p>
        </div>

        {/* Browser frame */}
        <div
          ref={ref}
          className={`rounded-2xl overflow-hidden ring-1 ring-neutral-200 shadow-2xl shadow-neutral-200/50 transition-all duration-1000 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
          }`}
        >
          {/* Title bar */}
          <div className="bg-neutral-900 px-4 py-3 flex items-center">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
              <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
              <div className="w-2.5 h-2.5 rounded-full bg-neutral-700" />
            </div>
            <div className="mx-auto text-neutral-500 text-xs font-mono">app.reconex.co.za/dashboard</div>
          </div>

          {/* Dashboard content */}
          <div className="bg-neutral-50 p-5 sm:p-8">
            {/* Summary row */}
            <div className="grid grid-cols-3 gap-4 mb-5">
              {[
                { label: 'Total Income', value: 'R 45,230.00', color: 'text-emerald-600', bg: 'bg-emerald-50 ring-emerald-100' },
                { label: 'Total Expenses', value: 'R 32,150.30', color: 'text-red-600', bg: 'bg-red-50 ring-red-100' },
                { label: 'Net Balance', value: 'R 13,079.70', color: 'text-blue-600', bg: 'bg-blue-50 ring-blue-100' },
              ].map((card) => (
                <div key={card.label} className={`rounded-xl ring-1 p-4 ${card.bg}`}>
                  <div className="text-[11px] text-neutral-500 uppercase tracking-wider mb-1">{card.label}</div>
                  <div className={`text-lg sm:text-xl font-bold ${card.color}`}>{card.value}</div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
              {/* Transactions table */}
              <div className="lg:col-span-3 bg-white rounded-xl ring-1 ring-neutral-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-neutral-100">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-neutral-400">Recent Transactions</span>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wider text-neutral-400 border-b border-neutral-100">
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
                        className={`border-b border-neutral-50 transition-all duration-500 ${
                          visible ? 'opacity-100' : 'opacity-0'
                        }`}
                        style={{ transitionDelay: `${600 + i * 100}ms` }}
                      >
                        <td className="px-5 py-2.5 text-neutral-400 font-mono text-xs">{tx.date}</td>
                        <td className="px-5 py-2.5 text-neutral-700 font-medium">{tx.desc}</td>
                        <td className={`px-5 py-2.5 text-right font-mono text-xs font-semibold ${tx.amount >= 0 ? 'text-emerald-600' : 'text-neutral-700'}`}>
                          R {Math.abs(tx.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-5 py-2.5">
                          <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 text-neutral-600">
                            {tx.category}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Category breakdown */}
              <div className="lg:col-span-2 bg-white rounded-xl ring-1 ring-neutral-200 p-5">
                <div className="mb-4">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-neutral-400">Expense Categories</span>
                </div>
                <div className="space-y-3">
                  {categories.map((cat, i) => (
                    <div
                      key={cat.name}
                      className={`transition-all duration-700 ${
                        visible ? 'opacity-100' : 'opacity-0'
                      }`}
                      style={{ transitionDelay: `${800 + i * 80}ms` }}
                    >
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-neutral-600 font-medium">{cat.name}</span>
                        <span className="text-neutral-400 font-mono">R {cat.amount.toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all duration-1000 ease-out"
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
    </section>
  )
}
