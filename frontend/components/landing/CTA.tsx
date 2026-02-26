'use client'

import Link from 'next/link'
import { ArrowRight, Shield, Lock, Zap } from 'lucide-react'

export default function CTA() {
  return (
    <section className="py-28 bg-neutral-950 text-white relative overflow-hidden">
      {/* Aurora background */}
      <div className="absolute inset-0 aurora-bg" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-blue-600/[0.08] rounded-full blur-[120px] animate-aurora" />
      <div className="absolute top-1/4 right-1/4 w-[300px] h-[300px] bg-indigo-600/[0.06] rounded-full blur-[80px] animate-aurora" style={{ animationDelay: '4s' }} />

      {/* Grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight mb-6 tracking-tight">
          Ready to stop categorizing
          <br />
          <span className="shimmer-text">transactions by hand?</span>
        </h2>

        <p className="text-base sm:text-lg text-neutral-400 mb-10 max-w-xl mx-auto leading-relaxed">
          Upload your first statement in under a minute. Free plan includes unlimited uploads,
          auto-categorization, VAT reports and Excel exports.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
          <Link
            href="/register"
            className="group relative inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 font-semibold rounded-xl transition-all duration-300 text-[15px] shadow-2xl shadow-blue-600/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
          >
            Get started free
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-400 to-indigo-400 blur-xl opacity-0 group-hover:opacity-30 transition-opacity duration-500" />
          </Link>
          <Link
            href="/login"
            className="px-8 py-4 text-neutral-400 hover:text-white font-medium rounded-xl border border-neutral-800/60 hover:border-neutral-600 transition-all duration-300 text-[15px] hover:bg-white/[0.03]"
          >
            Sign in
          </Link>
        </div>

        {/* Trust row */}
        <div className="flex flex-wrap justify-center gap-6 sm:gap-10">
          <div className="flex items-center gap-2 text-neutral-500">
            <div className="w-7 h-7 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <span className="text-[13px]">Encrypted & secure</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <div className="w-7 h-7 rounded-full bg-blue-500/10 flex items-center justify-center">
              <Lock className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <span className="text-[13px]">Data encrypted at rest</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <div className="w-7 h-7 rounded-full bg-amber-500/10 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <span className="text-[13px]">No credit card needed</span>
          </div>
        </div>
      </div>
    </section>
  )
}
