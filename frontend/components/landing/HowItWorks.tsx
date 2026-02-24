'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

const steps = [
  {
    number: '01',
    title: 'Upload your statement',
    description:
      'Drag and drop a CSV or PDF bank statement. The system auto-detects whether it is FNB, Standard Bank, ABSA, Capitec, Nedbank or Investec and parses accordingly. For unsupported formats, map your columns manually.',
  },
  {
    number: '02',
    title: 'Review & categorize',
    description:
      'Transactions are auto-categorized using built-in rules and learned patterns. Edit inline, bulk-categorize by keyword, or create custom rules that apply to every future upload.',
  },
  {
    number: '03',
    title: 'Analyze & export',
    description:
      'View monthly summaries, cash flow charts, category breakdowns and merchant analytics. Export to Excel, PDF or CSV  including dedicated VAT reports for your accountant.',
  },
]

function StepCard({ step, index }: { step: typeof steps[0]; index: number }) {
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

  return (
    <div
      ref={ref}
      className={`relative transition-all duration-700 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
      style={{ transitionDelay: `${index * 150}ms` }}
    >
      <div className="rounded-2xl border border-neutral-200 bg-white p-8 h-full">
        <div className="text-[40px] font-bold text-neutral-100 leading-none mb-4 select-none">
          {step.number}
        </div>
        <h3 className="text-lg font-semibold text-neutral-900 mb-3">
          {step.title}
        </h3>
        <p className="text-sm text-neutral-500 leading-relaxed">
          {step.description}
        </p>
      </div>
    </div>
  )
}

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 bg-neutral-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-3">
            How it works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Three steps. That is it.
          </h2>
          <p className="text-base text-neutral-500 max-w-xl mx-auto">
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
        <div className="text-center mt-14">
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 text-[15px]"
          >
            Try it now
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <p className="text-sm text-neutral-400 mt-3">Free to use. No credit card required.</p>
        </div>
      </div>
    </section>
  )
}
