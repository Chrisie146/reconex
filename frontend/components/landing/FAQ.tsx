'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const faqs = [
  {
    question: 'Which banks are supported?',
    answer:
      'We support all major South African banks including FNB, Standard Bank, ABSA, Capitec, Nedbank and more. We can process both CSV and PDF statements with automatic bank format detection.',
  },
  {
    question: 'Is my financial data secure?',
    answer:
      'Absolutely. Your data is processed securely and encrypted at rest. We use bank-level encryption and strict access controls to ensure maximum privacy.',
  },
  {
    question: 'Do I need to create an account?',
    answer:
      'A free account is required to save your work and access your statements across sessions. Registration takes under 30 seconds.',
  },
  {
    question: 'What file formats are supported?',
    answer:
      'We support CSV files from most banks, as well as PDF statements. Our advanced OCR technology can extract transactions from scanned and digital PDFs with high accuracy.',
  },
  {
    question: 'How accurate is the automatic categorization?',
    answer:
      'Our rule-based categorization system achieves 95%+ accuracy on average. The more you use it and refine your custom rules, the more accurate it becomes for your specific transaction patterns.',
  },
  {
    question: 'Can I edit the categories?',
    answer:
      'Yes. You can edit individual transactions, create custom categories and set up rules to automatically categorize similar transactions in the future. Bulk editing is also supported.',
  },
  {
    question: 'Can I export my categorized data?',
    answer:
      'Yes. Export your categorized transactions to Excel format, ready for your accountant or further analysis. The export includes all categories, monthly summaries and detailed breakdowns.',
  },
  {
    question: 'What happens to my data after my session ends?',
    answer:
      'Your data is retained in your account until you choose to delete it. You can also export to Excel at any time for offline storage.',
  },
  {
    question: 'Is there a limit on the number of transactions?',
    answer:
      'The free plan has no limits on the number of transactions or statements you can process. Analyze statements with thousands of transactions without any restrictions.',
  },
  {
    question: 'Can I use this for multiple businesses or clients?',
    answer:
      'The free plan supports a single workspace. Our upcoming Professional plan will include multi-client management features for bookkeepers and accountants managing multiple businesses.',
  },
]

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 bg-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-14">
          <p className="text-[11px] font-bold uppercase tracking-widest text-indigo-600 mb-3">
            FAQ
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-neutral-500">
            Everything you need to know about StatementBur
          </p>
        </div>

        {/* Accordion */}
        <div className="space-y-3">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index
            return (
              <div
                key={index}
                className={`rounded-xl border transition-colors ${
                  isOpen ? 'border-indigo-200 bg-indigo-50/40' : 'border-neutral-200 bg-white hover:border-neutral-300'
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
                    className={`w-4 h-4 text-indigo-600 flex-shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-5 pb-4 text-sm text-neutral-500 leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Contact CTA */}
        <div className="mt-14 text-center p-7 rounded-2xl bg-neutral-50 ring-1 ring-neutral-200">
          <h3 className="text-lg font-bold text-neutral-900 mb-1">Still have questions?</h3>
          <p className="text-sm text-neutral-500 mb-5">
            Can&apos;t find the answer you&apos;re looking for? Send us a message.
          </p>
          <a
            href="#contact"
            className="inline-block px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            Contact Support
          </a>
        </div>
      </div>
    </section>
  )
}
