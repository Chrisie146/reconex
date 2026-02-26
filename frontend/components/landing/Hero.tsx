'use client'

import Link from 'next/link'
import { ArrowRight, Shield, Zap, BarChart3 } from 'lucide-react'
import { useEffect, useState, useRef, useCallback } from 'react'

const banks = ['FNB', 'Standard Bank', 'ABSA', 'Capitec']

function AnimatedCounter({ target, suffix = '', prefix = '' }: { target: number; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const hasAnimated = useRef(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true
          const duration = 2000
          const startTime = Date.now()
          const animate = () => {
            const elapsed = Date.now() - startTime
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setCount(Math.floor(eased * target))
            if (progress < 1) requestAnimationFrame(animate)
          }
          requestAnimationFrame(animate)
        }
      },
      { threshold: 0.5 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [target])

  return <span ref={ref}>{prefix}{count}{suffix}</span>
}

// Floating particles component
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          className="absolute w-1 h-1 rounded-full bg-blue-400/20"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animation: `float ${4 + Math.random() * 4}s ease-in-out ${Math.random() * 4}s infinite`,
          }}
        />
      ))}
    </div>
  )
}

export default function Hero() {
  const [visibleIndex, setVisibleIndex] = useState(0)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const heroRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setVisibleIndex((prev) => (prev + 1) % banks.length)
    }, 2200)
    return () => clearInterval(interval)
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!heroRef.current) return
    const rect = heroRef.current.getBoundingClientRect()
    setMousePos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    })
  }, [])

  return (
    <section
      ref={heroRef}
      onMouseMove={handleMouseMove}
      className="relative min-h-[100vh] flex items-center bg-neutral-950 text-white pt-16 overflow-hidden"
    >
      {/* Interactive spotlight that follows mouse */}
      <div
        className="absolute w-[800px] h-[800px] rounded-full pointer-events-none transition-all duration-700 ease-out"
        style={{
          left: `${mousePos.x}%`,
          top: `${mousePos.y}%`,
          transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(circle, rgba(59, 130, 246, 0.08) 0%, transparent 70%)',
        }}
      />

      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      {/* Animated aurora orbs */}
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[150px] animate-aurora" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-600/[0.08] rounded-full blur-[120px] animate-aurora" style={{ animationDelay: '4s' }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-purple-600/[0.05] rounded-full blur-[100px] animate-aurora" style={{ animationDelay: '2s' }} />

      <FloatingParticles />

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        {/* Trust badge */}
        <div className="inline-flex items-center gap-3 px-5 py-2.5 rounded-full border border-neutral-800/60 bg-neutral-900/40 backdrop-blur-xl mb-10 animate-fade-in-down">
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[12px] text-emerald-400 font-semibold">Encrypted & Secure</span>
          </div>
          <span className="h-4 w-px bg-neutral-800" />
          <span className="text-[12px] text-neutral-500 uppercase tracking-wider font-medium">Supports</span>
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

        {/* Headline with shimmer effect */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.08] mb-6 animate-fade-in-up">
          Bank statement analysis
          <br />
          <span className="shimmer-text">
            done in minutes
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg sm:text-xl text-neutral-400 max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-in-up animation-delay-200">
          Upload CSV or PDF statements from any major SA bank.
          Auto-categorize transactions, generate VAT reports, and export accountant-ready spreadsheets — all in under a minute.
        </p>

        {/* CTA buttons with glow */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-fade-in-up animation-delay-400">
          <Link
            href="/register"
            className="group relative inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl transition-all duration-300 text-[15px] shadow-2xl shadow-blue-600/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
          >
            <span className="relative z-10 flex items-center gap-2">
              Get started free
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </span>
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-400 to-indigo-400 blur-xl opacity-0 group-hover:opacity-30 transition-opacity duration-500" />
          </Link>
          <Link
            href="#features"
            className="group px-8 py-4 text-neutral-400 hover:text-white font-medium rounded-xl transition-all duration-300 border border-neutral-800/60 hover:border-neutral-600 text-[15px] hover:bg-white/[0.03]"
          >
            See what it does
          </Link>
        </div>

        {/* Trust indicators */}
        <div className="mt-14 flex flex-wrap justify-center gap-8 animate-fade-in-up animation-delay-600">
          <div className="flex items-center gap-2 text-neutral-500">
            <Shield className="w-4 h-4 text-neutral-600" />
            <span className="text-[13px]">Encrypted at rest &amp; in transit</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <Zap className="w-4 h-4 text-neutral-600" />
            <span className="text-[13px]">No credit card required</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <BarChart3 className="w-4 h-4 text-neutral-600" />
            <span className="text-[13px]">Setup in 60 seconds</span>
          </div>
        </div>

        {/* Animated stats */}
        <div className="mt-20 grid grid-cols-2 sm:grid-cols-4 gap-8 animate-fade-in-up animation-delay-800">
          {[
            { value: 6, suffix: '', label: 'SA Banks Supported' },
            { value: 15, suffix: '%', label: 'SA VAT Calculated' },
            { value: 15, suffix: '', label: 'Default Categories' },
            { value: 0, suffix: '', label: 'To Get Started', displayValue: 'Free' },
          ].map((stat) => (
            <div key={stat.label} className="text-center group">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1.5 transition-colors group-hover:text-blue-400">
                {stat.displayValue || <AnimatedCounter target={stat.value} suffix={stat.suffix} />}
              </div>
              <div className="text-[11px] text-neutral-500 uppercase tracking-wider font-medium">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-white via-white/50 to-transparent" />
    </section>
  )
}
