import Link from 'next/link'
import { CheckCircle2, ArrowRight } from 'lucide-react'

export default function Hero() {
  return (
    <section className="relative bg-gradient-to-br from-neutral-900 via-neutral-800 to-neutral-900 text-white pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 ring-1 ring-indigo-400/30 mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-[13px] font-medium text-indigo-200">
              Trusted by 500+ South African businesses
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] mb-6">
            Bank Statement Analysis
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-indigo-300 mt-2">
              Made Effortless
            </span>
          </h1>

          {/* Sub-headline */}
          <p className="text-lg sm:text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload CSV or PDF statements from any major South African bank.
            Categorize thousands of transactions in minutes, not hours.
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-7 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-indigo-600/25 text-[15px]"
            >
              Get Started Free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="#how-it-works"
              className="px-7 py-3.5 text-neutral-300 hover:text-white font-medium rounded-xl transition-colors ring-1 ring-neutral-700 hover:ring-neutral-600 text-[15px]"
            >
              See How It Works
            </Link>
          </div>

          {/* Trust row */}
          <div className="mt-14 flex flex-wrap justify-center items-center gap-6 sm:gap-8 text-neutral-500 text-[13px]">
            {['No credit card required', 'Setup in 60 seconds', 'Bank-level security'].map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>{t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom fade to white */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent" />
    </section>
  )
}
