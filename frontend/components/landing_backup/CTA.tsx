import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

export default function CTA() {
  return (
    <section className="py-24 bg-neutral-950 text-white relative overflow-hidden">
      {/* Subtle gradient orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-blue-600/[0.06] rounded-full blur-[100px]" />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <h2 className="text-3xl sm:text-4xl font-bold leading-tight mb-5">
          Ready to stop categorizing<br />transactions by hand?
        </h2>

        <p className="text-base text-neutral-400 mb-10 max-w-xl mx-auto leading-relaxed">
          Upload your first statement in under a minute. Free plan includes unlimited uploads,
          auto-categorization, VAT reports and Excel exports.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 px-8 py-3.5 bg-blue-600 text-white hover:bg-blue-500 font-semibold rounded-xl transition-all duration-200 text-[15px]"
          >
            Get started free
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="/login"
            className="px-8 py-3.5 text-neutral-400 hover:text-white font-medium rounded-xl border border-neutral-800 hover:border-neutral-700 transition-colors text-[15px]"
          >
            Sign in
          </Link>
        </div>
      </div>
    </section>
  )
}
