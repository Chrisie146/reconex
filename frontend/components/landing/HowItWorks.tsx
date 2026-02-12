export default function HowItWorks() {
  const steps = [
    {
      number: '1',
      title: 'Upload Your Statement',
      description: 'Drag and drop your bank statement in CSV or PDF format. We support all major South African banks including FNB, Standard Bank, ABSA, and Capitec.',
      icon: '📤'
    },
    {
      number: '2',
      title: 'Auto-Categorize Transactions',
      description: 'Our intelligent rules engine automatically categorizes your transactions. Review, edit, and create custom rules for future statements.',
      icon: '🤖'
    },
    {
      number: '3',
      title: 'Export & Analyze',
      description: 'Get instant insights with monthly summaries and category breakdowns. Export to Excel for your accountant or further analysis.',
      icon: '📊'
    }
  ]

  return (
    <section id="how-it-works" className="py-24 bg-gradient-to-br from-neutral-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl font-bold text-neutral-900 mb-4">
            How It Works
          </h2>
          <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
            Three simple steps to transform your bank statements into actionable financial insights
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {/* Connection Lines (hidden on mobile) */}
          <div className="hidden md:block absolute top-16 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-300 via-blue-400 to-blue-300 transform -translate-y-1/2" style={{ width: '66%', left: '17%' }}></div>

          {steps.map((step, index) => (
            <div key={index} className="relative">
              {/* Step Card */}
              <div className="bg-white rounded-2xl shadow-lg p-8 border-2 border-neutral-100 hover:border-blue-300 transition-all duration-300 hover:shadow-2xl">
                {/* Step Number Circle */}
                <div className="relative mb-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-700 rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-lg mx-auto">
                    {step.number}
                  </div>
                  <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 text-5xl">
                    {step.icon}
                  </div>
                </div>

                {/* Content */}
                <h3 className="text-2xl font-bold text-neutral-900 mb-4 text-center mt-8">
                  {step.title}
                </h3>
                <p className="text-neutral-600 leading-relaxed text-center">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center mt-16">
          <a 
            href="/dashboard" 
            className="inline-block px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-lg transition-all transform hover:scale-105 text-lg"
          >
            Start Analyzing Now →
          </a>
          <p className="text-neutral-500 mt-4">No signup required • Free to use • Start immediately</p>
        </div>
      </div>
    </section>
  )
}
