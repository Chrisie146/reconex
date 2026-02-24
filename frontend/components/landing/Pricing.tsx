import { Check } from 'lucide-react'
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

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 bg-neutral-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-3">
            Pricing
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Start free. Upgrade when you need to.
          </h2>
          <p className="text-base text-neutral-500 max-w-xl mx-auto">
            The free plan includes everything most businesses need. No hidden limits.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-start">
          {plans.map((plan) => {
            const isPopular = plan.popular
            return (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-7 transition-shadow duration-200 ${
                  isPopular
                    ? 'bg-neutral-900 text-white ring-1 ring-neutral-700 shadow-xl'
                    : 'bg-white ring-1 ring-neutral-200 hover:shadow-md'
                }`}
              >
                {/* Badge */}
                {isPopular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold uppercase tracking-widest bg-blue-600 text-white px-4 py-1 rounded-full">
                    Coming Soon
                  </span>
                )}

                <h3 className={`text-lg font-bold mb-1 ${isPopular ? 'text-white' : 'text-neutral-900'}`}>
                  {plan.name}
                </h3>

                <div className="mb-3">
                  <span className={`text-3xl font-bold ${isPopular ? 'text-white' : 'text-neutral-900'}`}>
                    {plan.price}
                  </span>
                  <span className={`text-sm ml-1 ${isPopular ? 'text-neutral-400' : 'text-neutral-400'}`}>
                    / {plan.period}
                  </span>
                </div>

                <p className={`text-sm mb-6 ${isPopular ? 'text-neutral-400' : 'text-neutral-500'}`}>
                  {plan.description}
                </p>

                <Link
                  href={plan.href}
                  className={`block w-full py-2.5 rounded-lg text-sm font-semibold text-center mb-6 transition-colors ${
                    isPopular
                      ? 'bg-blue-600 text-white hover:bg-blue-500'
                      : plan.disabled
                      ? 'bg-neutral-100 text-neutral-400'
                      : 'bg-neutral-900 text-white hover:bg-neutral-800'
                  } ${plan.disabled ? 'pointer-events-none' : ''}`}
                >
                  {plan.cta}
                </Link>

                <ul className="space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5">
                      <Check
                        className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                          isPopular ? 'text-blue-400' : 'text-neutral-400'
                        }`}
                      />
                      <span className={`text-sm ${isPopular ? 'text-neutral-300' : 'text-neutral-600'}`}>
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
