'use client'

import { useState } from 'react'
import {
  Upload, BarChart3, FileSpreadsheet, Tag, Users, ArrowRight,
  ArrowLeft, CheckCircle2, Landmark, Sparkles, X,
} from 'lucide-react'

/* ── Types ─────────────────────────────────────────────────────────── */
interface OnboardingWizardProps {
  onComplete: () => void
  userName?: string | null
}

interface Step {
  title: string
  subtitle: string
  icon: React.ReactNode
  content: React.ReactNode
}

/* ── Component ─────────────────────────────────────────────────────── */
export default function OnboardingWizard({ onComplete, userName }: OnboardingWizardProps) {
  const [current, setCurrent] = useState(0)

  const greeting = userName ? userName.split(' ')[0] : 'there'

  const steps: Step[] = [
    /* ── Step 0 – Welcome ────────────────────────────────────────── */
    {
      title: `Welcome, ${greeting}!`,
      subtitle: 'Let\u2019s walk through the basics so you can get the most out of Reconex.',
      icon: <Landmark className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { icon: Upload, label: 'Upload CSV or PDF statements' },
              { icon: Tag, label: 'Auto-categorize transactions' },
              { icon: BarChart3, label: 'View monthly analytics' },
              { icon: FileSpreadsheet, label: 'Export to Excel' },
            ].map((item) => {
              const Icon = item.icon
              return (
                <div
                  key={item.label}
                  className="flex items-center gap-3 rounded-xl bg-blue-50 ring-1 ring-blue-100 p-3"
                >
                  <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-sm text-neutral-700">{item.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      ),
    },

    /* ── Step 1 – Upload ─────────────────────────────────────────── */
    {
      title: 'Upload a Statement',
      subtitle: 'Drag & drop or browse for a CSV or PDF bank statement. We support FNB, Standard Bank, ABSA, Capitec and more.',
      icon: <Upload className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
            <Upload className="w-7 h-7 text-blue-500" />
          </div>
          <p className="text-sm font-semibold text-neutral-900 mb-1">
            Supported formats
          </p>
          <p className="text-xs text-neutral-500">
            CSV files from most banks, PDF digital & scanned statements
          </p>
          <div className="flex items-center justify-center gap-3 mt-4">
            {['FNB', 'Standard Bank', 'ABSA', 'Capitec', 'Nedbank'].map((b) => (
              <span
                key={b}
                className="text-[10px] font-bold uppercase tracking-widest text-neutral-400 bg-white ring-1 ring-neutral-200 rounded px-2 py-0.5"
              >
                {b}
              </span>
            ))}
          </div>
        </div>
      ),
    },

    /* ── Step 2 – Categorize ─────────────────────────────────────── */
    {
      title: 'Auto-Categorize',
      subtitle: 'Transactions are automatically categorized using our rules engine. You can edit categories, create custom rules and bulk-update.',
      icon: <Tag className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="space-y-2">
          {[
            { desc: 'WOOLWORTHS FOOD', cat: 'Groceries', color: 'bg-emerald-500' },
            { desc: 'PROPERTY RENTAL', cat: 'Rent', color: 'bg-violet-500' },
            { desc: 'CITY POWER PREPAID', cat: 'Utilities', color: 'bg-amber-500' },
            { desc: 'UBER TRIP', cat: 'Transportation', color: 'bg-sky-500' },
          ].map((t) => (
            <div key={t.desc} className="flex items-center justify-between rounded-lg bg-white ring-1 ring-neutral-200 px-4 py-2.5">
              <span className="text-sm text-neutral-700 truncate">{t.desc}</span>
              <span className={`text-[10px] font-bold uppercase tracking-widest text-white px-2 py-0.5 rounded ${t.color}`}>
                {t.cat}
              </span>
            </div>
          ))}
        </div>
      ),
    },

    /* ── Step 3 – Analyze & Export ────────────────────────────────── */
    {
      title: 'Analyze & Export',
      subtitle: 'View monthly summaries, category breakdowns and export accountant-ready Excel reports in one click.',
      icon: <BarChart3 className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl bg-emerald-50 ring-1 ring-emerald-200 p-4 text-center">
            <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mb-1">Income</p>
            <p className="text-lg font-bold text-emerald-700">R 45,230</p>
          </div>
          <div className="rounded-xl bg-red-50 ring-1 ring-red-200 p-4 text-center">
            <p className="text-[10px] font-bold uppercase tracking-widest text-red-600 mb-1">Expenses</p>
            <p className="text-lg font-bold text-red-700">R 32,150</p>
          </div>
          <div className="rounded-xl bg-blue-50 ring-1 ring-blue-200 p-4 text-center">
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-1">Net</p>
            <p className="text-lg font-bold text-blue-700">R 13,080</p>
          </div>
        </div>
      ),
    },

    /* ── Step 4 – Clients (optional) ─────────────────────────────── */
    {
      title: 'Multi-Client Ready',
      subtitle: 'Managing multiple businesses? Create separate client workspaces and switch between them instantly from the sidebar.',
      icon: <Users className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="rounded-xl bg-neutral-50 ring-1 ring-neutral-200 p-5">
          <div className="space-y-2">
            {['Acme Pty Ltd', 'Smith & Partners', 'Personal'].map((c, i) => (
              <div
                key={c}
                className={`flex items-center gap-3 rounded-lg px-4 py-2.5 ${
                  i === 0 ? 'bg-blue-50 ring-1 ring-blue-200' : 'bg-white ring-1 ring-neutral-200'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${i === 0 ? 'bg-blue-500' : 'bg-neutral-300'}`} />
                <span className={`text-sm ${i === 0 ? 'font-semibold text-blue-700' : 'text-neutral-600'}`}>
                  {c}
                </span>
                {i === 0 && (
                  <span className="ml-auto text-[10px] font-bold uppercase tracking-widest text-blue-500">
                    Active
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      ),
    },

    /* ── Step 5 – Ready! ─────────────────────────────────────────── */
    {
      title: 'You\u2019re All Set!',
      subtitle: 'Your workspace is ready. Upload your first statement to get started.',
      icon: <Sparkles className="w-6 h-6 text-blue-600" />,
      content: (
        <div className="text-center py-4">
          <div className="w-16 h-16 rounded-2xl bg-emerald-50 ring-1 ring-emerald-200 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
          </div>
          <p className="text-sm text-neutral-600 max-w-xs mx-auto">
            Head to the dashboard to upload your first bank statement and see Reconex in action.
          </p>
        </div>
      ),
    },
  ]

  const step = steps[current]
  const isLast = current === steps.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl ring-1 ring-neutral-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
              {step.icon}
            </div>
            <div>
              <h2 className="text-lg font-bold text-neutral-900">{step.title}</h2>
            </div>
          </div>
          <button
            onClick={onComplete}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
            aria-label="Skip onboarding"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Subtitle */}
        <p className="px-6 text-sm text-neutral-500 leading-relaxed mb-5">
          {step.subtitle}
        </p>

        {/* Content */}
        <div className="px-6 mb-6">
          {step.content}
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex items-center justify-between">
          {/* Progress dots */}
          <div className="flex items-center gap-1.5">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === current ? 'bg-blue-600' : i < current ? 'bg-blue-300' : 'bg-neutral-200'
                }`}
              />
            ))}
          </div>

          {/* Nav buttons */}
          <div className="flex items-center gap-2">
            {current > 0 && (
              <button
                onClick={() => setCurrent(current - 1)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </button>
            )}
            <button
              onClick={() => {
                if (isLast) {
                  onComplete()
                } else {
                  setCurrent(current + 1)
                }
              }}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              {isLast ? 'Go to Dashboard' : 'Next'}
              {!isLast && <ArrowRight className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
