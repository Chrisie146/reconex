'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Check, Sparkles } from 'lucide-react'
import Link from 'next/link'

const plans = [
  {
    name: 'Free',
    price: 'R 0',
    period: 'forever',
    description: 'Full access for individuals and small businesses.',
    features: [
      'Unlimited statement uploads',
      'CSV & PDF parsing with OCR',
      'Auto-categorization & custom rules',
      'Monthly summaries & analytics',
      'VAT calculation & VAT reports',
      'Excel, PDF and CSV export',
      '6 SA banks auto-detected',
      'Invoice upload & matching',
    ],
    cta: 'Get Started Free',
    href: '/register',
    popular: false,
    disabled: false,
  },
  {
    name: 'Professional',
    price: 'R 299',
    period: 'per month',
    description: 'For bookkeepers and accountants with multiple clients.',
    features: [
      'Everything in Free',
      'Multi-client management',
      'Financial year archiving',
      'Advanced accountant reports',
      'Priority support',
      'API access',
    ],
    cta: 'Coming Soon',
    href: '#',
    popular: true,
    disabled: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'contact us',
    description: 'For organizations with specific requirements.',
    features: [
      'Everything in Professional',
      'Custom integrations',
      'Dedicated support & SLA',
      'On-premise deployment',
      'Training & onboarding',
    ],
    cta: 'Contact Us',
    href: '#contact',
    popular: false,
    disabled: true,
  },
]

function PricingCard({ plan, index }: { plan: (typeof plans)[0]; index: number }) {
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

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    e.currentTarget.style.setProperty('--mouse-x', `${x}px`)
    e.currentTarget.style.setProperty('--mouse-y', `${y}px`)
  }, [])

  const isPopular = plan.popular

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      className={`relative transition-all duration-700 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
      }`}
      style={{
        transitionDelay: `${index * 150}ms`,
        transform: visible && isPopular ? 'translateY(-8px)' : undefined
      }}
    >
      {/* Animated gradient border for popular plan */}
      {isPopular && (
        <div className="absolute -inset-[1px] rounded-2xl bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 opacity-80 blur-[1px]" style={{ backgroundSize: '200% 200%', animation: 'gradientX 3s ease infinite' }} />
      )}

      <div
        className={`spotlight-card relative rounded-2xl p-8 h-full transition-all duration-300 ${
          isPopular
            ? 'bg-neutral-950 text-white shadow-2xl shadow-indigo-500/10'
            : 'bg-white ring-1 ring-neutral-200/80 hover:shadow-xl hover:shadow-neutral-200/50 hover:-translate-y-1'
        }`}
      >
        {/* Badge */}
        {isPopular && (
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-1.5 rounded-full shadow-lg shadow-blue-500/30">
              <Sparkles className="w-3 h-3" />
              Coming Soon
            </div>
          </div>
        )}

        <h3 className={`text-lg font-bold mb-1 ${isPopular ? 'text-white' : 'text-neutral-900'}`}>
          {plan.name}
        </h3>

        <div className="mb-4">
          <span className={`text-4xl font-bold ${isPopular ? 'text-white' : 'text-neutral-900'}`}>
            {plan.price}
          </span>
          <span className={`text-sm ml-1.5 ${isPopular ? 'text-neutral-400' : 'text-neutral-400'}`}>
            / {plan.period}
          </span>
        </div>

        <p className={`text-sm mb-7 ${isPopular ? 'text-neutral-400' : 'text-neutral-500'}`}>
          {plan.description}
        </p>

        <Link
          href={plan.href}
          className={`block w-full py-3 rounded-xl text-sm font-semibold text-center mb-7 transition-all duration-300 ${
            isPopular
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 shadow-lg shadow-blue-500/20'
              : plan.disabled
              ? 'bg-neutral-100 text-neutral-400'
              : 'bg-neutral-900 text-white hover:bg-neutral-800 shadow-lg shadow-neutral-900/10'
          } ${plan.disabled ? 'pointer-events-none' : ''}`}
        >
          {plan.cta}
        </Link>

        <ul className="space-y-3">
          {plan.features.map((f) => (
            <li key={f} className="flex items-start gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                isPopular ? 'bg-blue-500/15' : 'bg-emerald-50'
              }`}>
                <Check
                  className={`w-3 h-3 ${
                    isPopular ? 'text-blue-400' : 'text-emerald-500'
                  }`}
                />
              </div>
              <span className={`text-sm leading-relaxed ${isPopular ? 'text-neutral-300' : 'text-neutral-600'}`}>
                {f}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function Pricing() {
  return (
    <section id="pricing" className="py-28 bg-neutral-50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-100/20 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-100 mb-5">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-amber-600">
              Pricing
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-neutral-900 mb-4 tracking-tight">
            Start free. Upgrade when you need to.
          </h2>
          <p className="text-base sm:text-lg text-neutral-500 max-w-xl mx-auto leading-relaxed">
            The free plan includes everything most businesses need. No hidden limits.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {plans.map((plan, i) => (
            <PricingCard key={plan.name} plan={plan} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
