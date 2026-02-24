import { Check } from 'lucide-react'
import Link from 'next/link'

const plans = [
  {
    name: 'Free',
    price: 'R 0',
    period: 'forever',
    description: 'Perfect for individuals and small businesses',
    features: [
      'Unlimited statement uploads',
      'Automatic categorization',
      'Monthly summaries',
      'Excel export',
      'Multi-bank support',
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
    description: 'For bookkeepers and accountants managing multiple clients',
    features: [
      'Everything in Free',
      'Multi-client management',
      'Advanced reporting',
      'Custom categories & rules',
      'Priority support',
      'API access',
      'White-label option',
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
    description: 'For large organizations with specific requirements',
    features: [
      'Everything in Professional',
      'Custom integrations',
      'Dedicated support',
      'SLA guarantees',
      'On-premise deployment',
      'Training & onboarding',
      'Custom development',
    ],
    cta: 'Contact Sales',
    href: '#contact',
    popular: false,
    disabled: true,
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 bg-neutral-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-widest text-blue-600 mb-3">
            Pricing
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
            Start for free with unlimited access. Upgrade when you need advanced features for your growing business.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {plans.map((plan) => {
            const isPopular = plan.popular
            return (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-7 ${
                  isPopular
                    ? 'bg-blue-600 text-white ring-2 ring-blue-400 shadow-xl md:scale-105'
                    : 'bg-white ring-1 ring-neutral-200 shadow-sm'
                }`}
              >
                {/* Badge */}
                {isPopular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 text-[11px] font-bold uppercase tracking-widest bg-amber-400 text-neutral-900 px-4 py-1 rounded-full shadow">
                    Coming Soon
                  </span>
                )}

                <h3
                  className={`text-xl font-bold mb-1 ${isPopular ? 'text-white' : 'text-neutral-900'}`}
                >
                  {plan.name}
                </h3>

                {/* Price */}
                <div className="mb-3">
                  <span className={`text-4xl font-bold ${isPopular ? 'text-white' : 'text-blue-600'}`}>
                    {plan.price}
                  </span>
                  <span className={`text-sm ml-1 ${isPopular ? 'text-blue-200' : 'text-neutral-400'}`}>
                    / {plan.period}
                  </span>
                </div>

                <p className={`text-sm mb-6 ${isPopular ? 'text-blue-200' : 'text-neutral-500'}`}>
                  {plan.description}
                </p>

                {/* CTA */}
                <Link
                  href={plan.href}
                  className={`block w-full py-2.5 rounded-lg text-sm font-semibold text-center mb-6 transition-colors ${
                    isPopular
                      ? 'bg-white text-blue-600 hover:bg-blue-50'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  } ${plan.disabled ? 'pointer-events-none opacity-60' : ''}`}
                >
                  {plan.cta}
                </Link>

                {/* Features */}
                <ul className="space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5">
                      <Check
                        className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                          isPopular ? 'text-emerald-300' : 'text-emerald-600'
                        }`}
                      />
                      <span className={`text-sm ${isPopular ? 'text-blue-100' : 'text-neutral-600'}`}>
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>

        {/* Footer note */}
        <p className="mt-12 text-center text-sm text-neutral-400">
          All plans include bank-level security, regular updates and access to new features.
        </p>
      </div>
    </section>
  )
}
