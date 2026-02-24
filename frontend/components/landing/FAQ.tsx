'use client'

import { useState } from 'react'
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

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 bg-white">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 mb-3">
            FAQ
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Common questions
          </h2>
        </div>

        {/* Accordion */}
        <div className="space-y-2">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index
            return (
              <div
                key={index}
                className={`rounded-xl border transition-all duration-200 ${
                  isOpen ? 'border-neutral-300 bg-neutral-50' : 'border-neutral-200 bg-white hover:border-neutral-300'
                }`}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  className="w-full px-5 py-4 text-left flex items-center justify-between gap-4"
                >
                  <span className="text-sm font-semibold text-neutral-900">
                    {faq.question}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-neutral-400 flex-shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                <div
                  className={`overflow-hidden transition-all duration-200 ${
                    isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  <div className="px-5 pb-4 text-sm text-neutral-500 leading-relaxed">
                    {faq.answer}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
