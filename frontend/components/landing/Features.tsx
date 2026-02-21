import {
  BarChart3, Zap, TrendingUp, Building2, FileSpreadsheet,
  ShieldCheck, PenLine, Target, Smartphone
} from 'lucide-react'

const features = [
  {
    icon: BarChart3,
    title: 'Automatic Categorization',
    description:
      'AI-powered rules automatically categorize your transactions based on descriptions. Customize categories to match your business needs.',
  },
  {
    icon: Zap,
    title: 'Lightning Fast Processing',
    description:
      'Process thousands of transactions in seconds. Upload CSV or PDF statements and get instant results with smart OCR extraction.',
  },
  {
    icon: TrendingUp,
    title: 'Monthly Analytics',
    description:
      'Comprehensive monthly summaries showing income, expenses and net balance. Visual breakdowns by category reveal spending patterns.',
  },
  {
    icon: Building2,
    title: 'Multi-Bank Support',
    description:
      'Works with FNB, Standard Bank, ABSA, Capitec, Nedbank and more. Automatically detects bank format and extracts data accurately.',
  },
  {
    icon: FileSpreadsheet,
    title: 'Excel Export',
    description:
      'Export accountant-ready Excel reports with all transactions categorized. Perfect for tax season and financial reporting.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure & Private',
    description:
      'Your financial data never leaves your session. Bank-level encryption with no permanent storage. Complete privacy guaranteed.',
  },
  {
    icon: PenLine,
    title: 'Inline Editing',
    description:
      'Edit transactions, categories and rules directly in the interface. Bulk update similar transactions with one click.',
  },
  {
    icon: Target,
    title: 'Smart Rules Engine',
    description:
      'Create custom rules to automatically categorize future transactions. Learn from your patterns and improve accuracy over time.',
  },
  {
    icon: Smartphone,
    title: 'Responsive Design',
    description:
      'Works seamlessly on desktop, tablet, and mobile. Manage your statements anywhere, anytime with a professional interface.',
  },
]

const stats = [
  { value: '10K+', label: 'Statements Processed' },
  { value: '500+', label: 'Happy Businesses' },
  { value: '95%', label: 'Accuracy Rate' },
  { value: '60s', label: 'Average Setup Time' },
]

export default function Features() {
  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-widest text-indigo-600 mb-3">
            Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Everything You Need to Analyze Statements
          </h2>
          <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
            Professional tools designed for bookkeepers, accountants and business owners
            who need accurate financial insights fast.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => {
            const Icon = f.icon
            return (
              <div
                key={f.title}
                className="group rounded-xl border border-neutral-200 bg-white p-6 hover:shadow-md hover:border-indigo-200 transition-all duration-200"
              >
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mb-4 group-hover:bg-indigo-100 transition-colors">
                  <Icon className="w-5 h-5 text-indigo-600" />
                </div>
                <h3 className="text-base font-semibold text-neutral-900 mb-2 group-hover:text-indigo-600 transition-colors">
                  {f.title}
                </h3>
                <p className="text-sm text-neutral-500 leading-relaxed">
                  {f.description}
                </p>
              </div>
            )
          })}
        </div>

        {/* Stats */}
        <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((s) => (
            <div key={s.label} className="text-center py-6 rounded-xl bg-neutral-50">
              <div className="text-3xl font-bold text-indigo-600 mb-1">{s.value}</div>
              <div className="text-sm text-neutral-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
