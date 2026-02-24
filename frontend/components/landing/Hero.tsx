'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { useEffect, useState } from 'react'

const banks = ['FNB', 'Standard Bank', 'ABSA', 'Capitec', 'Nedbank', 'Investec']

export default function Hero() {
  const [visibleIndex, setVisibleIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setVisibleIndex((prev) => (prev + 1) % banks.length)
    }, 2200)
    return () => clearInterval(interval)
  }, [])

  return (
    <section className="relative min-h-[92vh] flex items-center bg-neutral-950 text-white pt-16 overflow-hidden">
      {/* Subtle grid background */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      {/* Gradient orbs */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-indigo-600/[0.08] rounded-full blur-[100px] animate-pulse-slow animation-delay-2000" />

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        {/* Supported banks ticker */}
        <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-neutral-800 bg-neutral-900/60 backdrop-blur-sm mb-10 animate-fade-in">
          <span className="text-[12px] text-neutral-500 uppercase tracking-wider font-medium">Supports</span>
          <span className="h-4 w-px bg-neutral-800" />
          <div className="relative h-5 w-28 overflow-hidden">
            {banks.map((bank, i) => (
              <span
                key={bank}
                className={`absolute inset-0 flex items-center justify-center text-[13px] font-semibold text-neutral-300 transition-all duration-500 ${
                  i === visibleIndex
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-3'
                }`}
              >
                {bank}
              </span>
            ))}
          </div>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl lg:text-[3.5rem] font-bold tracking-tight leading-[1.1] mb-6 animate-fade-in-up">
          Bank statement analysis
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-blue-300 to-indigo-400">
            for South African businesses
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg text-neutral-400 max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-in-up animation-delay-200">
          Upload CSV or PDF statements from FNB, Standard Bank, ABSA, Capitec, Nedbank or Investec.
          Auto-categorize transactions, generate VAT reports, and export accountant-ready spreadsheets.
        </p>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center animate-fade-in-up animation-delay-400">
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-blue-600/20 text-[15px]"
          >
            Get started free
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="#features"
            className="px-7 py-3.5 text-neutral-400 hover:text-white font-medium rounded-xl transition-colors border border-neutral-800 hover:border-neutral-700 text-[15px]"
          >
            See what it does
          </Link>
        </div>

        {/* Key facts */}
        <div className="mt-20 grid grid-cols-2 sm:grid-cols-4 gap-6 animate-fade-in-up animation-delay-600">
          {[
            { value: '6', label: 'SA Banks Supported' },
            { value: 'CSV & PDF', label: 'File Formats' },
            { value: '15%', label: 'SA VAT Calculation' },
            { value: 'Free', label: 'To Get Started' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-white mb-1">{stat.value}</div>
              <div className="text-[12px] text-neutral-500 uppercase tracking-wider">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent" />
    </section>
  )
}
