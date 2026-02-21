import { Lightbulb, BarChart3, Zap } from 'lucide-react'

export default function Screenshots() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-widest text-indigo-600 mb-3">
            Preview
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Powerful Analytics, Beautiful Interface
          </h2>
          <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
            A professional dashboard designed for clarity and efficiency
          </p>
        </div>

        {/* Browser frame */}
        <div className="mb-12 rounded-2xl overflow-hidden shadow-xl ring-1 ring-neutral-200">
          {/* Title bar */}
          <div className="bg-neutral-900 px-4 py-3 flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <div className="ml-auto text-neutral-500 text-xs font-mono">StatementBur</div>
          </div>

          {/* Mock dashboard */}
          <div className="bg-neutral-50 p-6 sm:p-8">
            {/* Summary cards */}
            <div className="bg-white rounded-xl ring-1 ring-neutral-200 p-5 mb-5">
              <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-400 mb-4">
                Monthly Summary
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-emerald-50 ring-1 ring-emerald-200 p-4">
                  <div className="text-xs text-emerald-700 mb-1">Total Income</div>
                  <div className="text-xl font-bold text-emerald-600">R 45,230</div>
                </div>
                <div className="rounded-lg bg-red-50 ring-1 ring-red-200 p-4">
                  <div className="text-xs text-red-700 mb-1">Total Expenses</div>
                  <div className="text-xl font-bold text-red-600">R 32,150</div>
                </div>
                <div className="rounded-lg bg-indigo-50 ring-1 ring-indigo-200 p-4">
                  <div className="text-xs text-indigo-700 mb-1">Net Balance</div>
                  <div className="text-xl font-bold text-indigo-600">R 13,080</div>
                </div>
              </div>
            </div>

            {/* Category breakdown */}
            <div className="bg-white rounded-xl ring-1 ring-neutral-200 p-5">
              <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-400 mb-4">
                Category Breakdown
              </p>
              <div className="space-y-3">
                {[
                  { category: 'Groceries', amount: 8500, color: 'bg-indigo-500' },
                  { category: 'Rent', amount: 12000, color: 'bg-violet-500' },
                  { category: 'Utilities', amount: 3200, color: 'bg-amber-500' },
                  { category: 'Transportation', amount: 4500, color: 'bg-emerald-500' },
                ].map((item) => (
                  <div key={item.category} className="flex items-center gap-3">
                    <span className="text-sm text-neutral-600 min-w-[110px]">{item.category}</span>
                    <div className="flex-1 bg-neutral-100 rounded-full h-5 overflow-hidden">
                      <div
                        className={`${item.color} h-full rounded-full flex items-center justify-end pr-2`}
                        style={{ width: `${(item.amount / 12000) * 100}%` }}
                      >
                        <span className="text-[10px] text-white font-semibold">
                          R {item.amount.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Highlight cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            {
              icon: Lightbulb,
              title: 'Smart Categorization',
              description:
                'AI-powered rules learn from your patterns to automatically categorize transactions accurately.',
              accent: 'indigo',
            },
            {
              icon: BarChart3,
              title: 'Visual Analytics',
              description:
                'Beautiful charts and graphs help you understand your financial health at a glance.',
              accent: 'emerald',
            },
            {
              icon: Zap,
              title: 'Lightning Fast',
              description:
                'Process thousands of transactions in seconds with our optimized parsing engine.',
              accent: 'violet',
            },
          ].map((card) => {
            const Icon = card.icon
            const bgMap: Record<string, string> = {
              indigo: 'bg-indigo-50 ring-indigo-200',
              emerald: 'bg-emerald-50 ring-emerald-200',
              violet: 'bg-violet-50 ring-violet-200',
            }
            const iconColorMap: Record<string, string> = {
              indigo: 'text-indigo-600',
              emerald: 'text-emerald-600',
              violet: 'text-violet-600',
            }
            return (
              <div
                key={card.title}
                className={`rounded-xl p-6 ring-1 ${bgMap[card.accent]}`}
              >
                <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center mb-4">
                  <Icon className={`w-5 h-5 ${iconColorMap[card.accent]}`} />
                </div>
                <h4 className="text-base font-semibold text-neutral-900 mb-2">{card.title}</h4>
                <p className="text-sm text-neutral-500 leading-relaxed">{card.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
