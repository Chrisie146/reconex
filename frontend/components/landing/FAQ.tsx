'use client'

import { useState } from 'react'

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  const faqs = [
    {
      question: 'Which banks are supported?',
      answer: 'We support all major South African banks including FNB, Standard Bank, ABSA, Capitec, Nedbank, and more. We can process both CSV and PDF statements with automatic bank format detection.'
    },
    {
      question: 'Is my financial data secure?',
      answer: 'Absolutely. Your data is processed in your browser session and is never permanently stored on our servers. We use bank-level encryption and do not require any account creation, ensuring maximum privacy.'
    },
    {
      question: 'Do I need to create an account?',
      answer: 'No! You can start using the Bank Statement Analyzer immediately without any signup or login. Simply upload your statement and start analyzing. For advanced features like multi-client management, an account will be optional.'
    },
    {
      question: 'What file formats are supported?',
      answer: 'We support CSV files from most banks, as well as PDF statements. Our advanced OCR technology can extract transactions from scanned PDF documents and digital PDFs with high accuracy.'
    },
    {
      question: 'How accurate is the automatic categorization?',
      answer: 'Our rule-based categorization system achieves 95%+ accuracy on average. The more you use it and refine your custom rules, the more accurate it becomes for your specific transaction patterns.'
    },
    {
      question: 'Can I edit the categories?',
      answer: 'Yes! You can edit individual transactions, create custom categories, and set up rules to automatically categorize similar transactions in the future. Bulk editing is also supported for efficiency.'
    },
    {
      question: 'Can I export my categorized data?',
      answer: 'Yes, you can export your categorized transactions to Excel format, ready for your accountant or further analysis. The export includes all categories, monthly summaries, and detailed breakdowns.'
    },
    {
      question: 'What happens to my data after my session ends?',
      answer: 'Session data is automatically cleared after 24 hours of inactivity. You can also manually clear your data at any time. For permanent storage, we recommend exporting your categorized data to Excel.'
    },
    {
      question: 'Is there a limit on the number of transactions?',
      answer: 'No! The free version has no limits on the number of transactions or statements you can process. Analyze statements with thousands of transactions without any restrictions.'
    },
    {
      question: 'Can I use this for multiple businesses or clients?',
      answer: 'The free version processes one statement at a time. Our upcoming Professional plan will include multi-client management features for bookkeepers and accountants managing multiple businesses.'
    }
  ]

  return (
    <section id="faq" className="py-24 bg-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl font-bold text-neutral-900 mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-xl text-neutral-600">
            Everything you need to know about the Bank Statement Analyzer
          </p>
        </div>

        {/* FAQ Accordion */}
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div 
              key={index}
              className="border border-neutral-200 rounded-lg overflow-hidden bg-white hover:border-blue-300 transition-colors"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full px-6 py-5 text-left flex items-center justify-between gap-4 hover:bg-neutral-50 transition-colors"
              >
                <span className="text-lg font-semibold text-neutral-900">
                  {faq.question}
                </span>
                <svg
                  className={`w-6 h-6 text-blue-600 flex-shrink-0 transition-transform ${
                    openIndex === index ? 'transform rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {openIndex === index && (
                <div className="px-6 pb-5 text-neutral-600 leading-relaxed">
                  {faq.answer}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Contact CTA */}
        <div className="mt-16 text-center p-8 bg-gradient-to-br from-blue-50 to-neutral-50 rounded-2xl border border-blue-100">
          <h3 className="text-2xl font-bold text-neutral-900 mb-2">Still have questions?</h3>
          <p className="text-neutral-600 mb-6">
            Can't find the answer you're looking for? Send us a message.
          </p>
          <a 
            href="#contact" 
            className="inline-block px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all"
          >
            Contact Support
          </a>
        </div>
      </div>
    </section>
  )
}
