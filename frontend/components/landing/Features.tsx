export default function Features() {
  const features = [
    {
      icon: '📊',
      title: 'Automatic Categorization',
      description: 'AI-powered rules automatically categorize your transactions based on descriptions. Customize categories to match your business needs.'
    },
    {
      icon: '⚡',
      title: 'Lightning Fast Processing',
      description: 'Process thousands of transactions in seconds. Upload CSV or PDF statements and get instant results with smart OCR extraction.'
    },
    {
      icon: '📈',
      title: 'Monthly Analytics',
      description: 'Get comprehensive monthly summaries showing income, expenses, and net balance. Visual breakdowns by category help you understand spending patterns.'
    },
    {
      icon: '🏦',
      title: 'Multi-Bank Support',
      description: 'Works with statements from FNB, Standard Bank, ABSA, Capitec, and more. Automatically detects bank format and extracts data accurately.'
    },
    {
      icon: '📑',
      title: 'Excel Export',
      description: 'Export accountant-ready Excel reports with all transactions categorized. Perfect for tax season and financial reporting.'
    },
    {
      icon: '🔒',
      title: 'Secure & Private',
      description: 'Your financial data never leaves your session. No account required, no data stored permanently. Complete privacy guaranteed.'
    },
    {
      icon: '✏️',
      title: 'Inline Editing',
      description: 'Edit transactions, categories, and rules directly in the interface. Bulk update similar transactions with one click.'
    },
    {
      icon: '🎯',
      title: 'Smart Rules Engine',
      description: 'Create custom rules to automatically categorize future transactions. Learn from your patterns and improve accuracy over time.'
    },
    {
      icon: '📱',
      title: 'Responsive Design',
      description: 'Works seamlessly on desktop, tablet, and mobile. Manage your statements anywhere, anytime with a professional interface.'
    }
  ]

  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl font-bold text-neutral-900 mb-4">
            Everything You Need to Analyze Statements
          </h2>
          <p className="text-xl text-neutral-600 max-w-3xl mx-auto">
            Professional tools designed for bookkeepers, accountants, and business owners 
            who need accurate financial insights fast.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div 
              key={index} 
              className="group p-6 rounded-xl border border-neutral-200 bg-white hover:shadow-xl hover:border-blue-300 transition-all duration-300"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold text-neutral-900 mb-3 group-hover:text-blue-600 transition-colors">
                {feature.title}
              </h3>
              <p className="text-neutral-600 leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        {/* Stats Section */}
        <div className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600 mb-2">10K+</div>
            <div className="text-neutral-600">Statements Processed</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600 mb-2">500+</div>
            <div className="text-neutral-600">Happy Businesses</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600 mb-2">95%</div>
            <div className="text-neutral-600">Accuracy Rate</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600 mb-2">60s</div>
            <div className="text-neutral-600">Average Setup Time</div>
          </div>
        </div>
      </div>
    </section>
  )
}
