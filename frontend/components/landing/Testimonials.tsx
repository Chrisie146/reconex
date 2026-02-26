'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Building2, FileText, Receipt, Download, Shield, Zap } from 'lucide-react'

const banks = [
  { name: 'FNB', detail: 'Aspire & Premier accounts' },
  { name: 'Standard Bank', detail: 'CSV & PDF statements' },
  { name: 'ABSA', detail: 'CSV & PDF with OCR' },
  { name: 'Capitec', detail: 'CSV export support' },
]

const capabilities = [
  {
    icon: Building2,
    title: '4 SA Banks supported',
    description: 'Statements from FNB, Standard Bank, ABSA and Capitec are parsed automatically. More banks are on the roadmap.',
    gradient: 'from-blue-500 to-cyan-500',
  },
  {
    icon: FileText,
    title: 'CSV and PDF — including scanned',
    description: 'Upload digital bank exports or scanned PDF statements. OCR handles both English and Afrikaans text formats.',
    gradient: 'from-violet-500 to-purple-500',
  },
  {
    icon: Receipt,
    title: '15% SA VAT, per transaction',
    description: 'Automatic VAT calculation on every transaction. Configure which categories are VAT-applicable. Export VAT Input and Output reports.',
    gradient: 'from-emerald-500 to-teal-500',
  },
  {
    icon: Download,
    title: 'Export to Excel, PDF or CSV',
    description: 'Export your categorized data as spreadsheets, PDFs or CSV files — including monthly summaries and accountant-ready reports.',
    gradient: 'from-orange-500 to-amber-500',
  },
  {
    icon: Shield,
    title: 'Encrypted at rest and in transit',
    description: 'All data is encrypted in storage and over the wire. Authentication uses JWT with bcrypt-hashed passwords and rate-limited resets.',
    gradient: 'from-pink-500 to-rose-500',
  },
  {
    icon: Zap,
    title: 'Free plan — no hidden limits',
    description: 'The free plan has no cap on statements, transactions, clients or exports. Paid tiers add multi-client management and priority support.',
    gradient: 'from-indigo-500 to-blue-500',
  },
]

function CapabilityCard({ cap, index, visible }: { cap: (typeof capabilities)[0]; index: number; visible: boolean }) {
  const Icon = cap.icon
  return (
    <div
      className={`group flex gap-4 p-5 rounded-xl border border-neutral-100 bg-white hover:border-neutral-200 hover:shadow-md transition-all duration-500 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
      }`}
      style={{ transitionDelay: `${index * 80}ms` }}
    >
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cap.gradient} flex items-center justify-center flex-shrink-0 shadow-sm transition-transform duration-300 group-hover:scale-105`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <h3 className="text-[14px] font-semibold text-neutral-900 mb-1">{cap.title}</h3>
        <p className="text-[13px] text-neutral-500 leading-relaxed">{cap.description}</p>
      </div>
    </div>
  )
}

export default function TrustSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
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
    if (sectionRef.current) observer.observe(sectionRef.current)
    return () => observer.disconnect()
  }, [])

  return (
    <section id="testimonials" className="py-28 bg-neutral-50 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={sectionRef}>
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100 mb-5">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-blue-600">
              Built for South Africa
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-neutral-900 mb-4 tracking-tight">
            Everything you need, nothing you don&apos;t
          </h2>
          <p className="text-base sm:text-lg text-neutral-500 max-w-xl mx-auto leading-relaxed">
            Reconex is purpose-built for South African bank statement formats, VAT rules and accounting workflows.
          </p>
        </div>

        {/* Bank support grid */}
        <div className="mb-14">
          <p className="text-center text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-6">
            Supported banks
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {banks.map((bank, i) => (
              <div
                key={bank.name}
                className={`rounded-xl border border-neutral-200/80 bg-white p-4 text-center hover:border-blue-200 hover:shadow-sm transition-all duration-500 ${
                  visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
                }`}
                style={{ transitionDelay: `${i * 60}ms` }}
              >
                <div className="text-sm font-bold text-neutral-800 mb-1">{bank.name}</div>
                <div className="text-[11px] text-neutral-400 leading-tight">{bank.detail}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Capability highlights */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-14">
          {capabilities.map((cap, i) => (
            <CapabilityCard key={cap.title} cap={cap} index={i} visible={visible} />
          ))}
        </div>

        {/* Beta CTA */}
        <div
          className={`relative rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50 p-8 text-center transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
          style={{ transitionDelay: '600ms' }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-100 border border-blue-200 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-blue-700">Early Access</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-neutral-900 mb-3">
            Try it now — completely free
          </h3>
          <p className="text-sm text-neutral-500 max-w-md mx-auto mb-6 leading-relaxed">
            Reconex is in active development. Sign up for free access, and your feedback directly shapes what gets built next.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 text-sm shadow-lg shadow-blue-600/20"
          >
            Create a free account
          </Link>
        </div>
      </div>
    </section>
  )
}
