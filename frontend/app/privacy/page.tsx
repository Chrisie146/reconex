import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | Reconex',
  description: 'How Reconex handles your personal information in compliance with POPIA.',
}

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      {/* Header */}
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-neutral-900 dark:text-white tracking-tight">
            recon<span className="text-blue-500">ex</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/security" className="text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">Security</Link>
            <Link href="/terms" className="text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">Privacy Policy</h1>
        <p className="text-sm text-neutral-500 mb-10">Last updated: 24 February 2026</p>

        <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8 text-[15px] leading-relaxed">

          {/* 1. Introduction */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white mt-0">1. Introduction</h2>
            <p>
              Reconex (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) is committed to protecting your personal information 
              in accordance with the <strong>Protection of Personal Information Act 4 of 2013 (POPIA)</strong> and 
              all other applicable South African legislation.
            </p>
            <p>
              This Privacy Policy explains how we collect, use, store, and protect your personal information 
              when you use our bank statement analysis platform (&quot;the Service&quot;).
            </p>
          </section>

          {/* 2. Responsible Party */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">2. Responsible Party</h2>
            <p>
              For the purposes of POPIA, the responsible party is:
            </p>
            <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 text-sm">
              <p className="font-medium text-neutral-900 dark:text-white">Reconex</p>
              <p>Email: <a href="mailto:support@reconex.co.za" className="text-blue-500 hover:underline">support@reconex.co.za</a></p>
            </div>
          </section>

          {/* 3. What Information We Collect */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">3. What Information We Collect</h2>
            <p>We collect the following categories of personal information:</p>
            
            <h3 className="text-lg font-medium text-neutral-800 dark:text-neutral-200">3.1 Account Information</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Name and email address (during registration)</li>
              <li>Password (stored in hashed form only)</li>
              <li>Account preferences and settings</li>
            </ul>

            <h3 className="text-lg font-medium text-neutral-800 dark:text-neutral-200">3.2 Financial Data</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>Bank statements you upload (PDF and CSV files)</li>
              <li>Extracted transaction data (dates, descriptions, amounts)</li>
              <li>Account numbers and bank details contained in statements</li>
              <li>Categorization and mapping data you create</li>
            </ul>

            <h3 className="text-lg font-medium text-neutral-800 dark:text-neutral-200">3.3 Technical Data</h3>
            <ul className="list-disc pl-6 space-y-1">
              <li>IP address and browser information</li>
              <li>Usage analytics (pages visited, features used)</li>
              <li>Error logs for troubleshooting</li>
            </ul>
          </section>

          {/* 4. How We Use Your Information */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">4. How We Use Your Information</h2>
            <p>We process your personal information for the following purposes:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Service delivery:</strong> Parsing bank statements, categorizing transactions, generating reports and exports</li>
              <li><strong>Account management:</strong> Authentication, authorization, and managing your user account</li>
              <li><strong>Client management:</strong> Allowing bookkeepers and accountants to manage multiple client portfolios</li>
              <li><strong>Product improvement:</strong> Understanding usage patterns to improve the Service</li>
              <li><strong>Communication:</strong> Sending service-related notifications and responding to support requests</li>
              <li><strong>Legal compliance:</strong> Meeting our obligations under POPIA and other applicable laws</li>
            </ul>
          </section>

          {/* 5. Legal Basis for Processing */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">5. Legal Basis for Processing</h2>
            <p>Under POPIA, we process your personal information based on:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Consent:</strong> You voluntarily upload bank statements and provide account information</li>
              <li><strong>Contract:</strong> Processing is necessary to provide the Service you have signed up for</li>
              <li><strong>Legitimate interest:</strong> Improving our platform, ensuring security, and preventing fraud</li>
              <li><strong>Legal obligation:</strong> Compliance with South African law and regulations</li>
            </ul>
          </section>

          {/* 6. Data Storage & Retention */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">6. Data Storage &amp; Retention</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>Your data is stored on secure servers with encryption at rest and in transit</li>
              <li>Uploaded bank statements and extracted data are retained for as long as your account is active</li>
              <li>You may delete individual statements, sessions, or your entire account at any time</li>
              <li>Upon account deletion, all associated personal and financial data is permanently removed within 30 days</li>
              <li>Backups containing your data are purged according to our retention schedule (maximum 90 days)</li>
            </ul>
          </section>

          {/* 7. Data Sharing */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">7. Data Sharing &amp; Third Parties</h2>
            <p>
              <strong>We do not sell, rent, or trade your personal information.</strong>
            </p>
            <p>We may share data with:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Hosting providers:</strong> For infrastructure and data storage</li>
              <li><strong>OCR services:</strong> For processing scanned bank statement PDFs (data is processed and not retained by third-party OCR providers)</li>
              <li><strong>Analytics tools:</strong> Anonymized usage data for improving the Service</li>
              <li><strong>Legal authorities:</strong> When required by law, regulation, or legal process</li>
            </ul>
            <p>
              All third-party service providers are contractually bound to protect your information and only 
              process it for the specified purposes.
            </p>
          </section>

          {/* 8. Your POPIA Rights */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">8. Your Rights Under POPIA</h2>
            <p>As a data subject, you have the right to:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Access:</strong> Request confirmation of what personal information we hold about you</li>
              <li><strong>Correction:</strong> Request that we correct or update inaccurate personal information</li>
              <li><strong>Deletion:</strong> Request that we delete your personal information (subject to legal retention requirements)</li>
              <li><strong>Object:</strong> Object to the processing of your personal information on reasonable grounds</li>
              <li><strong>Portability:</strong> Request your data in a structured, commonly used format</li>
              <li><strong>Withdraw consent:</strong> Withdraw previously given consent (this may affect your ability to use the Service)</li>
              <li><strong>Complain:</strong> Lodge a complaint with the Information Regulator if you believe your rights have been infringed</li>
            </ul>
            <p>
              To exercise any of these rights, contact us at{' '}
              <a href="mailto:support@reconex.co.za" className="text-blue-500 hover:underline">support@reconex.co.za</a>.
              We will respond within 30 days as required by POPIA.
            </p>
          </section>

          {/* 9. Information Regulator */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">9. Information Regulator</h2>
            <p>
              If you are not satisfied with our handling of your personal information, you may lodge a complaint with:
            </p>
            <div className="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 text-sm space-y-1">
              <p className="font-medium text-neutral-900 dark:text-white">The Information Regulator (South Africa)</p>
              <p>Phone: 010 023 5207</p>
              <p>Email: <a href="mailto:enquiries@inforegulator.org.za" className="text-blue-500 hover:underline">enquiries@inforegulator.org.za</a></p>
              <p>Website: <a href="https://inforegulator.org.za" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">inforegulator.org.za</a></p>
            </div>
          </section>

          {/* 10. Cookies */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">10. Cookies &amp; Tracking</h2>
            <p>We use cookies and similar technologies for:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Essential cookies:</strong> Authentication tokens and session management (required for the Service to function)</li>
              <li><strong>Analytics cookies:</strong> Understanding how users interact with the Service (can be opted out of)</li>
            </ul>
            <p>
              You can manage cookie preferences through your browser settings. Disabling essential cookies 
              may prevent you from using the Service.
            </p>
          </section>

          {/* 11. Children */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">11. Children&apos;s Information</h2>
            <p>
              The Service is intended for use by businesses, bookkeepers, and accountants. We do not knowingly 
              collect personal information from children under 18. If we become aware that we have collected such 
              information, we will delete it promptly.
            </p>
          </section>

          {/* 12. Changes */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">12. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of material changes via 
              email or a prominent notice on the Service. Continued use of the Service after changes constitutes 
              acceptance of the updated policy.
            </p>
          </section>

          {/* 13. Contact */}
          <section>
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">13. Contact Us</h2>
            <p>
              For any questions or concerns about this Privacy Policy or how we handle your personal information:
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
