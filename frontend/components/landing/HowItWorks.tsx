import { Upload, Cpu, FileBarChart, ArrowRight } from 'lucide-react'
import Link from 'next/link'

const steps = [
  {
    number: '1',
    title: 'Upload Your Statement',
    description:
      'Drag and drop your bank statement in CSV or PDF format. We support all major South African banks including FNB, Standard Bank, ABSA and Capitec.',
    icon: Upload,
  },
  {
    number: '2',
    title: 'Auto-Categorize Transactions',
    description:
      'Our intelligent rules engine automatically categorizes your transactions. Review, edit and create custom rules for future statements.',
    icon: Cpu,
  },
  {
    number: '3',
    title: 'Export & Analyze',
    description:
      'Get instant insights with monthly summaries and category breakdowns. Export to Excel for your accountant or further analysis.',
    icon: FileBarChart,
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 bg-neutral-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-widest text-indigo-600 mb-3">
            How It Works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Three Simple Steps
          </h2>
          <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
            Transform your bank statements into actionable financial insights in under a minute.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
          {/* Connection line (desktop) */}
          <div className="hidden md:block absolute top-14 h-px bg-gradient-to-r from-indigo-200 via-indigo-300 to-indigo-200" style={{ left: '20%', right: '20%' }} />

          {steps.map((step) => {
            const Icon = step.icon
            return (
              <div key={step.number} className="relative">
                <div className="rounded-2xl border border-neutral-200 bg-white p-8 hover:shadow-md hover:border-indigo-200 transition-all duration-200">
                  {/* Number circle */}
                  <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center text-white text-lg font-bold mx-auto mb-5 relative z-10">
                    {step.number}
                  </div>

                  {/* Icon */}
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mx-auto mb-5">
                    <Icon className="w-5 h-5 text-indigo-600" />
                  </div>

                  <h3 className="text-lg font-semibold text-neutral-900 mb-3 text-center">
                    {step.title}
                  </h3>
                  <p className="text-sm text-neutral-500 leading-relaxed text-center">
                    {step.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* CTA */}
        <div className="text-center mt-14">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-7 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-colors shadow-sm text-[15px]"
          >
            Start Analyzing Now
            <ArrowRight className="w-4 h-4" />
          </Link>
          <p className="text-sm text-neutral-400 mt-3">Free to use &middot; No credit card required</p>
        </div>
      </div>
    </section>
  )
}
