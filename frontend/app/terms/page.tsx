import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Terms of Service | Reconex',
  description: 'Terms and conditions for using the Reconex bank statement analysis platform.',
}

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      {/* Header */}
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-neutral-900 dark:text-white tracking-tight">
            recon<span className="text-blue-500">ex</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/privacy" className="text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">Privacy</Link>
            <Link href="/security" className="text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">Security</Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">Terms of Service</h1>
        <p className="text-sm text-neutral-500 mb-10">Last updated: 24 February 2026</p>

        <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8 text-[15px] leading-relaxed">

          {/* 1. Agreement */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mt-0">1. Agreement to Terms</h2>
            <p>
              By accessing or using Reconex (&quot;the Service&quot;), you agree to be bound by these Terms of Service. 
              If you do not agree to these terms, you may not use the Service. These terms constitute a legally 
              binding agreement between you and Reconex.
            </p>
          </section>

          {/* 2. Description */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">2. Description of Service</h2>
            <p>
              Reconex is a bank statement analysis platform designed for South African businesses, bookkeepers, 
              and accountants. The Service allows you to:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Upload and parse bank statements (PDF and CSV formats)</li>
              <li>Automatically categorize transactions</li>
              <li>Map transactions for accounting purposes</li>
              <li>Generate reports and exports</li>
              <li>Manage multiple clients and financial years</li>
            </ul>
          </section>

          {/* 3. Account Registration */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">3. Account Registration</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>You must provide accurate and complete registration information</li>
              <li>You are responsible for maintaining the confidentiality of your login credentials</li>
              <li>You must be at least 18 years of age to create an account</li>
              <li>You are responsible for all activity that occurs under your account</li>
              <li>You must notify us immediately of any unauthorized use of your account</li>
            </ul>
          </section>

          {/* 4. Acceptable Use */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">4. Acceptable Use</h2>
            <p>You agree to use the Service only for lawful purposes. You may not:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Upload documents you do not have the right or authorization to process</li>
              <li>Use the Service for money laundering, fraud, or any illegal activity</li>
              <li>Attempt to gain unauthorized access to other users&apos; accounts or data</li>
              <li>Reverse-engineer, decompile, or attempt to extract the source code of the Service</li>
              <li>Use automated tools to scrape or overload the Service</li>
              <li>Upload malicious files, viruses, or harmful content</li>
              <li>Resell or sublicense the Service without written permission</li>
            </ul>
          </section>

          {/* 5. Your Data */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">5. Your Data</h2>
            <p>
              You retain all ownership rights to the bank statements and financial data you upload to the Service. 
              By uploading data, you grant Reconex a limited licence to process, store, and display the data 
              solely for the purpose of providing you with the Service.
            </p>
            <p>
              You are responsible for ensuring you have the necessary rights and authorizations to upload and 
              process any bank statements or financial data, particularly when managing data on behalf of clients.
            </p>
            <p>
              We handle your data in accordance with our <Link href="/privacy" className="text-blue-500 hover:underline">Privacy Policy</Link> and 
              the Protection of Personal Information Act (POPIA).
            </p>
          </section>

          {/* 6. Accuracy */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">6. Accuracy of Results</h2>
            <p>
              While we strive for the highest accuracy in parsing and categorizing bank statements, 
              the Service relies on OCR (Optical Character Recognition) and automated pattern matching, 
              which may not be 100% accurate in all cases.
            </p>
            <p>
              <strong>You are responsible for reviewing and verifying</strong> all extracted transaction data, 
              categorizations, and reports before using them for accounting, tax, or other financial purposes. 
              Reconex is a tool to assist you — it does not replace professional judgement.
            </p>
          </section>

          {/* 7. Pricing & Payment */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">7. Pricing &amp; Payment</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>Current pricing is displayed on the <Link href="/#pricing" className="text-blue-500 hover:underline">pricing page</Link></li>
              <li>Prices are quoted in South African Rand (ZAR) and include VAT where applicable</li>
              <li>We reserve the right to change pricing with 30 days&apos; notice</li>
              <li>Failed payments may result in a temporary suspension of your account</li>
              <li>No refunds are provided for partial periods of use</li>
            </ul>
          </section>

          {/* 8. Service Availability */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">8. Service Availability</h2>
            <p>
              We aim for high availability but do not guarantee uninterrupted access to the Service. 
              The Service may be temporarily unavailable due to:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Scheduled maintenance (we will provide advance notice where possible)</li>
              <li>Unplanned outages or technical issues</li>
              <li>Events beyond our reasonable control (force majeure)</li>
            </ul>
          </section>

          {/* 9. Intellectual Property */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">9. Intellectual Property</h2>
            <p>
              All rights, title, and interest in the Service — including the design, code, branding, 
              documentation, and all related materials — remain the exclusive property of Reconex. 
              Nothing in these terms grants you any ownership rights in the Service itself.
            </p>
          </section>

          {/* 10. Limitation of Liability */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by South African law:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>The Service is provided &quot;as is&quot; without warranties of any kind, whether express or implied</li>
              <li>Reconex shall not be liable for any indirect, incidental, special, consequential, or punitive damages</li>
              <li>Reconex shall not be liable for any losses arising from inaccuracies in parsed data, categorization errors, or OCR misreads</li>
              <li>Our total liability for any claims arising from your use of the Service shall not exceed the amount you paid to us in the 12 months preceding the claim</li>
            </ul>
          </section>

          {/* 11. Indemnification */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">11. Indemnification</h2>
            <p>
              You agree to indemnify and hold Reconex harmless from any claims, damages, or expenses arising 
              from your use of the Service, violation of these terms, or infringement of any third party&apos;s rights.
            </p>
          </section>

          {/* 12. Termination */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">12. Termination</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>You may close your account at any time through the application or by contacting us</li>
              <li>We may suspend or terminate your account for violations of these terms</li>
              <li>Upon termination, your data will be handled as described in our <Link href="/privacy" className="text-blue-500 hover:underline">Privacy Policy</Link></li>
              <li>Provisions that by their nature should survive termination will remain in effect (including limitation of liability, indemnification, and dispute resolution)</li>
            </ul>
          </section>

          {/* 13. Governing Law */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">13. Governing Law &amp; Disputes</h2>
            <p>
              These terms are governed by the laws of the Republic of South Africa. Any disputes arising from 
              these terms or the Service shall be subject to the exclusive jurisdiction of the South African courts.
            </p>
            <p>
              Before initiating formal proceedings, both parties agree to attempt to resolve disputes through 
              good-faith negotiation for a period of at least 30 days.
            </p>
          </section>

          {/* 14. Changes */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">14. Changes to These Terms</h2>
            <p>
              We may update these Terms of Service from time to time. We will notify you of material changes 
              via email or a prominent notice on the Service at least 14 days before they take effect. 
              Continued use of the Service after such notice constitutes acceptance of the updated terms.
            </p>
          </section>

          {/* 15. Contact */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">15. Contact Us</h2>
            <p>
              For questions about these Terms of Service:
            </p>
            <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 text-sm">
              <p>Email: <a href="mailto:support@reconex.co.za" className="text-blue-500 hover:underline">support@reconex.co.za</a></p>
            </div>
          </section>
        </div>

        {/* Back link */}
        <div className="mt-12 pt-8 border-t border-neutral-200 dark:border-neutral-800">
          <Link href="/" className="text-sm text-blue-500 hover:underline">&larr; Back to Reconex</Link>
        </div>
      </main>
    </div>
  )
}
