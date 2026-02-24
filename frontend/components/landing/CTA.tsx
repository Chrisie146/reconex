import Link from 'next/link'
import { ArrowRight, CheckCircle2 } from 'lucide-react'

export default function CTA() {
  return (
    <section className="py-24 bg-blue-600 text-white relative overflow-hidden">
      {/* Decorative blurs */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-white rounded-full blur-3xl" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-white rounded-full blur-3xl" />
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight mb-5">
          Ready to Transform Your
          <span className="block mt-1">Financial Analysis?</span>
        </h2>

        <p className="text-lg text-blue-200 mb-10 max-w-2xl mx-auto leading-relaxed">
          Join hundreds of businesses already saving hours every month with automated
          bank statement analysis. Start for free in 60 seconds.
        </p>

        {/* Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center mb-10">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-blue-600 hover:bg-blue-50 font-semibold rounded-xl transition-colors shadow-lg text-[15px]"
          >
            Get Started Free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="#features"
            className="px-8 py-3.5 text-white font-medium rounded-xl ring-1 ring-blue-400 hover:bg-blue-500 transition-colors text-[15px]"
          >
            Learn More
          </Link>
        </div>

        {/* Trust row */}
        <div className="flex flex-wrap justify-center items-center gap-6 text-blue-200 text-[13px]">
          {['No credit card required', 'Free forever plan', 'Start immediately'].map((t) => (
            <div key={t} className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-300" />
              <span>{t}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
