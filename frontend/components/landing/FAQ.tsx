'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'

const faqs = [
  {
    question: 'Which banks are supported?',
    answer:
      'FNB, Standard Bank, ABSA, Capitec, Nedbank and Investec. The system auto-detects the bank from your file. For any other bank, you can manually map the columns using the built-in column mapping tool.',
  },
  {
    question: 'What file formats can I upload?',
    answer:
      'CSV files from any bank, and PDF statements (both digital and scanned). Scanned PDFs are processed using OCR with support for Afrikaans and English text. You can also define custom extraction regions for complex layouts.',
  },
  {
    question: 'How does the auto-categorization work?',
    answer:
      'A rule-based engine matches transaction descriptions against a built-in database of South African merchants and keywords. There are 15 default categories. You can create custom categories and rules, and the system learns from your corrections over time.',
  },
  {
    question: 'Can I calculate VAT from my statements?',
    answer:
      'Yes. The system calculates 15% SA VAT per transaction automatically. You can configure which categories are VAT-applicable and set custom VAT rates. Export dedicated VAT Input and Output reports with date range filtering.',
  },
  {
    question: 'What export formats are available?',
    answer:
      'Excel, PDF and CSV. Export options include: all transactions, monthly summaries, per-category breakdowns, accountant reports with executive summaries, and dedicated VAT reports.',
  },
  {
    question: 'Can I manage multiple clients?',
    answer:
      'Yes. Create separate clients within your account. Each client has isolated transactions, categories, rules, invoices and financial years. Switch between clients from the sidebar.',
  },
  {
    question: 'Is my data secure?',
    answer:
      'Your data is encrypted at rest and in transit. Authentication uses JWT tokens with bcrypt-hashed passwords. Password reset uses single-use tokens with rate limiting. Cloud storage supports S3, Azure Blob or Google Cloud.',
  },
  {
    question: 'Is there a limit on uploads or transactions?',
    answer:
      'The free plan has no limits on the number of statements or transactions you can process. CSV uploads support up to 5 MB and PDFs up to 10 MB per file.',
  },
  {
    question: 'Can I match invoices to bank transactions?',
    answer:
      'Yes. Upload invoice PDFs and the system will auto-extract metadata and match them to bank transactions using supplier name similarity, amount matching and date proximity. You confirm or reject each match.',
  },
  {
    question: 'What analytics are available?',
    answer:
      'The dashboard includes: daily cash flow / running balance charts, monthly income vs expense trends, category spending breakdowns, top merchant analysis with averages and counts, and auto-detected recurring transactions.',
  },
]

function FAQItem({ faq, index, isOpen, onToggle }: {
  faq: (typeof faqs)[0]
  index: number
  isOpen: boolean
  onToggle: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={`transition-all duration-500 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
      style={{ transitionDelay: `${index * 50}ms` }}
    >
      <div
        className={`rounded-xl border transition-all duration-300 ${
          isOpen
            ? 'border-blue-200/60 bg-blue-50/30 shadow-sm shadow-blue-100/50'
            : 'border-neutral-200/80 bg-white hover:border-neutral-300 hover:shadow-sm'
        }`}
      >
        <button
          onClick={onToggle}
          className="w-full px-6 py-5 text-left flex items-center justify-between gap-4 group"
        >
          <span className={`text-[15px] font-semibold transition-colors ${
            isOpen ? 'text-blue-900' : 'text-neutral-900 group-hover:text-neutral-700'
          }`}>
            {faq.question}
          </span>
          <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
            isOpen ? 'bg-blue-500 rotate-180' : 'bg-neutral-100 group-hover:bg-neutral-200'
          }`}>
            <ChevronDown
              className={`w-4 h-4 transition-colors ${
                isOpen ? 'text-white' : 'text-neutral-400'
              }`}
            />
          </div>
        </button>
        <div
          ref={contentRef}
          className={`overflow-hidden transition-all duration-300 ease-in-out ${
            isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="px-6 pb-5 text-sm text-neutral-600 leading-relaxed">
            {faq.answer}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="py-28 bg-white relative">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neutral-200 to-transparent" />

      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-50 border border-cyan-100 mb-5">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-cyan-600">
              FAQ
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-bold text-neutral-900 mb-4 tracking-tight">
            Common questions
          </h2>
          <p className="text-base text-neutral-500 max-w-md mx-auto leading-relaxed">
            Everything you need to know about Reconex
          </p>
        </div>

        {/* Accordion */}
        <div className="space-y-3">
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              index={index}
              isOpen={openIndex === index}
              onToggle={() => setOpenIndex(openIndex === index ? null : index)}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
