export default function Screenshots() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl font-bold text-neutral-900 mb-4">
            Powerful Analytics, Beautiful Interface
          </h2>
          <p className="text-xl text-neutral-600 max-w-3xl mx-auto">
            A professional dashboard designed for clarity and efficiency
          </p>
        </div>

        {/* Main Dashboard Preview */}
        <div className="mb-12 rounded-2xl overflow-hidden shadow-2xl border border-neutral-200">
          <div className="bg-gradient-to-r from-neutral-800 to-neutral-900 px-4 py-3 flex items-center gap-2">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
            <div className="ml-auto text-neutral-400 text-sm font-mono">Bank Statement Analyzer</div>
          </div>
          
          {/* Mock Dashboard Screenshot */}
          <div className="bg-neutral-50 p-8">
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">📊 Monthly Summary</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="text-sm text-green-700 mb-1">Total Income</div>
                  <div className="text-2xl font-bold text-green-600">R 45,230</div>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-sm text-red-700 mb-1">Total Expenses</div>
                  <div className="text-2xl font-bold text-red-600">R 32,150</div>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="text-sm text-blue-700 mb-1">Net Balance</div>
                  <div className="text-2xl font-bold text-blue-600">R 13,080</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">📈 Category Breakdown</h3>
              <div className="space-y-3">
                {[
                  { category: 'Groceries', amount: 8500, color: 'bg-blue-500' },
                  { category: 'Rent', amount: 12000, color: 'bg-purple-500' },
                  { category: 'Utilities', amount: 3200, color: 'bg-yellow-500' },
                  { category: 'Transportation', amount: 4500, color: 'bg-green-500' }
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="text-sm text-neutral-600 min-w-[120px]">{item.category}</div>
                    <div className="flex-1 bg-neutral-100 rounded-full h-6 overflow-hidden">
                      <div 
                        className={`${item.color} h-full rounded-full flex items-center justify-end pr-2`}
                        style={{ width: `${(item.amount / 12000) * 100}%` }}
                      >
                        <span className="text-xs text-white font-semibold">R {item.amount.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 border border-blue-200">
            <div className="text-3xl mb-3">💡</div>
            <h4 className="text-lg font-semibold text-neutral-900 mb-2">Smart Categorization</h4>
            <p className="text-neutral-600 text-sm">AI-powered rules learn from your patterns to automatically categorize transactions accurately.</p>
          </div>
          
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-6 border border-green-200">
            <div className="text-3xl mb-3">📊</div>
            <h4 className="text-lg font-semibold text-neutral-900 mb-2">Visual Analytics</h4>
            <p className="text-neutral-600 text-sm">Beautiful charts and graphs help you understand your financial health at a glance.</p>
          </div>
          
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-6 border border-purple-200">
            <div className="text-3xl mb-3">⚡</div>
            <h4 className="text-lg font-semibold text-neutral-900 mb-2">Lightning Fast</h4>
            <p className="text-neutral-600 text-sm">Process thousands of transactions in seconds with our optimized parsing engine.</p>
          </div>
        </div>
      </div>
    </section>
  )
}
