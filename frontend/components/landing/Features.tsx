'use client'

import { useEffect, useRef, useState } from 'react'

const features = [
  {
    title: 'Multi-Bank Support',
    description:
      'Auto-detects and parses statements from FNB, Standard Bank, ABSA, Capitec, Nedbank and Investec. Manual column mapping available for any other bank.',
  },
  {
    title: 'CSV & PDF Upload',
    description:
      'Upload CSV exports or PDF statements. OCR-powered extraction handles scanned PDFs with support for Afrikaans and English formats.',
  },
  {
    title: 'Auto-Categorization',
    description:
      'Rule-based engine with a built-in South African merchant database. 15 default categories, custom categories, and learned patterns that improve over time.',
  },
  {
    title: 'VAT Calculation',
    description:
      'Automatic 15% SA VAT computation per transaction. Configure VAT per category. Export VAT Input and Output reports with date range filtering.',
  },
  {
    title: 'Excel & PDF Export',
    description:
      'Export categorized transactions, monthly summaries, per-category breakdowns and accountant reports. Available in Excel, PDF and CSV.',
  },
  {
    title: 'Invoice Matching',
    description:
      'Upload invoices and auto-match them to bank transactions using supplier name similarity, amount matching and date proximity scoring.',
  },
  {
    title: 'Multi-Client Management',
    description:
      'Manage multiple clients from a single account. Each client has isolated transactions, rules, categories, invoices and financial years.',
  },
  {
    title: 'Inline Editing',
    description:
      'Edit transactions, categories and merchants directly in the table. Bulk-categorize by keyword or selection. Undo bulk actions instantly.',
  },
  {
    title: 'Analytics Dashboard',
    description:
      'Cash flow charts, income vs expense trends, category breakdowns, merchant analytics and recurring transaction detection  all in one view.',
  },
  {
    title: 'Financial Years',
    description:
      'Define financial year periods per client. Archive completed years and access historical data in read-only mode at any time.',
  },
  {
    title: 'Reconciliation',
    description:
      'Set opening and closing balances. Running balance validation with deterministic arithmetic verification and 1-cent tolerance.',
  },
  {
    title: 'Custom Rules Engine',
    description:
      'Create keyword-based categorization rules with priority ordering. Clone rules across clients. Auto-apply on every upload.',
  },
]

function FeatureCard({ feature, index }: { feature: typeof features[0]; index: number }) {
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
      { threshold: 0.15 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={`group relative rounded-xl border border-neutral-200 bg-white p-6 transition-all duration-500 hover:border-neutral-300 hover:shadow-sm ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
      }`}
      style={{ transitionDelay: `${index * 60}ms` }}
    >
      <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center mb-4 text-[13px] font-bold text-neutral-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
        {String(index + 1).padStart(2, '0')}
      </div>
      <h3 className="text-[15px] font-semibold text-neutral-900 mb-2">
        {feature.title}
      </h3>
      <p className="text-sm text-neutral-500 leading-relaxed">
        {feature.description}
      </p>
    </div>
  )
}

export default function Features() {
  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-3">
            What it does
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Every feature, real and working
          </h2>
          <p className="text-base text-neutral-500 max-w-xl mx-auto">
            No vaporware. Every capability listed here is built, tested, and ready to use today.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <FeatureCard key={f.title} feature={f} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
