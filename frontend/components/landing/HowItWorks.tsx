'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowRight, Upload, Sparkles, FileSpreadsheet } from 'lucide-react'

const steps = [
  {
    number: '01',
    icon: Upload,
    title: 'Upload your statement',
    description:
      'Drag and drop a CSV or PDF bank statement. The system auto-detects whether it is FNB, Standard Bank, ABSA, Capitec, Nedbank or Investec and parses accordingly. For unsupported formats, map your columns manually.',
    gradient: 'from-blue-500 to-cyan-500',
    glowColor: 'blue',
  },
  {
    number: '02',
    icon: Sparkles,
    title: 'Review & categorize',
    description:
      'Transactions are auto-categorized using built-in rules and learned patterns. Edit inline, bulk-categorize by keyword, or create custom rules that apply to every future upload.',
    gradient: 'from-violet-500 to-purple-500',
    glowColor: 'violet',
  },
  {
    number: '03',
    icon: FileSpreadsheet,
    title: 'Analyze & export',
    description:
      'View monthly summaries, cash flow charts, category breakdowns and merchant analytics. Export to Excel, PDF or CSV — including dedicated VAT reports for your accountant.',
    gradient: 'from-emerald-500 to-teal-500',
    glowColor: 'emerald',
  },
]

function StepCard({ step, index }: { step: (typeof steps)[0]; index: number }) {
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
      { threshold: 0.2 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  const Icon = step.icon

  return (
    <div
      ref={ref}
      className={`relative transition-all duration-700 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
      }`}
      style={{ transitionDelay: `${index * 200}ms` }}
    >
      {/* Connection line (not on last card) */}
      {index < 2 && (
        <div className="hidden md:block absolute top-14 -right-3 w-6 z-10">
          <div className={`h-px bg-gradient-to-r ${step.gradient} opacity-30`} />
        </div>
      )}

      <div className="group relative rounded-2xl border border-neutral-200/80 bg-white p-8 h-full hover:shadow-xl hover:shadow-neutral-200/50 transition-all duration-500 hover:-translate-y-1 overflow-hidden">
        {/* Gradient glow on hover */}
        <div className={`absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br ${step.gradient} rounded-full blur-3xl opacity-0 group-hover:opacity-10 transition-opacity duration-700`} />

        {/* Step number + icon */}
        <div className="flex items-center gap-4 mb-6">
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.gradient} flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-110`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <span className="text-[42px] font-bold text-neutral-100 leading-none select-none group-hover:text-neutral-200/80 transition-colors">
            {step.number}
          </span>
        </div>

        <h3 className="text-lg font-semibold text-neutral-900 mb-3">
          {step.title}
        </h3>
        <p className="text-sm text-neutral-500 leading-relaxed relative z-10">
          {step.description}
        </p>
      </div>
    </div>
  )
}

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-28 bg-neutral-50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 mb-5">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-indigo-600">
              How It Works
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-neutral-900 mb-4 tracking-tight">
            Three steps. That&apos;s it.
          </h2>
          <p className="text-base sm:text-lg text-neutral-500 max-w-xl mx-auto leading-relaxed">
            From raw bank statement to categorized, exportable data in under a minute.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <StepCard key={step.number} step={step} index={i} />
          ))}
        </div>

        {/* CTA */}
        <div className="text-center mt-16">
          <Link
            href="/register"
            className="group relative inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl transition-all duration-300 text-[15px] shadow-xl shadow-blue-600/20 hover:shadow-blue-500/30 hover:-translate-y-0.5"
          >
            Try it now
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <p className="text-sm text-neutral-400 mt-4">Free to use. No credit card required.</p>
        </div>
      </div>
    </section>
  )
}
