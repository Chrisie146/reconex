export default function Pricing() {
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
        'No account required'
      ],
      cta: 'Get Started Free',
      href: '/dashboard',
      popular: false
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
        'White-label option'
      ],
      cta: 'Coming Soon',
      href: '#',
      popular: true
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
        'Custom development'
      ],
      cta: 'Contact Sales',
      href: '#contact',
      popular: false
    }
  ]

  return (
    <section id="pricing" className="py-24 bg-gradient-to-br from-neutral-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl font-bold text-neutral-900 mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-xl text-neutral-600 max-w-3xl mx-auto">
            Start for free with unlimited access. Upgrade when you need advanced features for your growing business.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan, index) => (
            <div 
              key={index}
              className={`relative rounded-2xl p-8 ${
                plan.popular 
                  ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-2xl scale-105 border-4 border-blue-400' 
                  : 'bg-white text-neutral-900 shadow-lg border border-neutral-200'
              }`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-5 left-1/2 transform -translate-x-1/2">
                  <span className="bg-yellow-400 text-neutral-900 px-4 py-1 rounded-full text-sm font-bold shadow-lg">
                    COMING SOON
                  </span>
                </div>
              )}

              {/* Plan Name */}
              <h3 className={`text-2xl font-bold mb-2 ${plan.popular ? 'text-white' : 'text-neutral-900'}`}>
                {plan.name}
              </h3>
              
              {/* Price */}
              <div className="mb-4">
                <span className={`text-5xl font-bold ${plan.popular ? 'text-white' : 'text-blue-600'}`}>
                  {plan.price}
                </span>
                <span className={`text-lg ml-2 ${plan.popular ? 'text-blue-100' : 'text-neutral-500'}`}>
                  / {plan.period}
                </span>
              </div>

              {/* Description */}
              <p className={`mb-6 ${plan.popular ? 'text-blue-100' : 'text-neutral-600'}`}>
                {plan.description}
              </p>

              {/* CTA Button */}
              <a
                href={plan.href}
                className={`block w-full py-3 px-6 rounded-lg font-semibold text-center mb-6 transition-all ${
                  plan.popular
                    ? 'bg-white text-blue-600 hover:bg-blue-50'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                } ${plan.name === 'Professional' || plan.name === 'Enterprise' ? 'cursor-not-allowed opacity-75' : ''}`}
              >
                {plan.cta}
              </a>

              {/* Features List */}
              <ul className="space-y-3">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <svg 
                      className={`w-5 h-5 mt-0.5 flex-shrink-0 ${plan.popular ? 'text-green-300' : 'text-green-600'}`} 
                      fill="currentColor" 
                      viewBox="0 0 20 20"
                    >
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className={plan.popular ? 'text-blue-50' : 'text-neutral-700'}>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Additional Info */}
        <div className="mt-16 text-center">
          <p className="text-neutral-600">
            <strong>All plans include:</strong> Bank-level security, regular updates, and access to new features
          </p>
        </div>
      </div>
    </section>
  )
}
