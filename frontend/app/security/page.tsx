import Link from 'next/link'
import type { Metadata } from 'next'
import { Shield, Lock, Server, Eye, Trash2, AlertTriangle, CheckCircle2 } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Security | Reconex',
  description: 'How Reconex protects your financial data and bank statements.',
}

function SecurityCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
          {icon}
        </div>
        <h3 className="text-base font-semibold text-neutral-900 dark:text-white">{title}</h3>
      </div>
      <div className="text-[15px] text-neutral-600 dark:text-neutral-400 leading-relaxed">
        {children}
      </div>
    </div>
  )
}

export default function SecurityPage() {
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
            <Link href="/terms" className="text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-blue-500" />
          </div>
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white">Security</h1>
        </div>
        <p className="text-neutral-500 text-lg max-w-2xl mb-12">
          We understand that bank statements contain highly sensitive financial information. 
          Here&apos;s how we protect your data at every step.
        </p>

        {/* Security cards */}
        <div className="grid gap-6">

          <SecurityCard icon={<Lock className="w-4 h-4" />} title="Encryption">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>In transit:</strong> All data is transmitted over HTTPS/TLS 1.2+. No unencrypted connections are accepted.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>At rest:</strong> Uploaded files and database records are encrypted using industry-standard AES-256 encryption.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Passwords:</strong> Stored using bcrypt hashing with salt — we never store plaintext passwords.</span>
              </li>
            </ul>
          </SecurityCard>

          <SecurityCard icon={<Server className="w-4 h-4" />} title="Infrastructure">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Secure hosting:</strong> Our servers are hosted on reputable cloud infrastructure with enterprise-grade physical security.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Firewalls &amp; access control:</strong> Network-level firewalls and strict access controls limit who and what can reach our systems.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Regular backups:</strong> Automated encrypted backups ensure data can be recovered in the event of an incident.</span>
              </li>
            </ul>
          </SecurityCard>

          <SecurityCard icon={<Eye className="w-4 h-4" />} title="Access Controls">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Authentication:</strong> JWT-based authentication with secure token management and automatic expiry.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Data isolation:</strong> Each user&apos;s data is strictly isolated. You can only access your own statements and clients.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Session management:</strong> Active sessions are tracked, and you can view or revoke them at any time.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Admin access:</strong> Internal access to production data is strictly limited, logged, and only granted on a need-to-know basis.</span>
              </li>
            </ul>
          </SecurityCard>

          <SecurityCard icon={<Trash2 className="w-4 h-4" />} title="Data Handling &amp; Deletion">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Minimal retention:</strong> We only keep data for as long as you need it. Delete statements, sessions, or your entire account whenever you choose.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Permanent deletion:</strong> When you delete data, it is permanently removed from our systems within 30 days (including backups within 90 days).</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>No data mining:</strong> Your financial data is never used for advertising, profiling, or any purpose beyond providing you with the Service.</span>
              </li>
            </ul>
          </SecurityCard>

          <SecurityCard icon={<AlertTriangle className="w-4 h-4" />} title="Security Headers &amp; Application Security">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Security headers:</strong> Content-Security-Policy (CSP), X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security (HSTS), and more.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>CORS protection:</strong> Cross-origin requests are restricted to authorized domains only.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Request size limits:</strong> Upload size limits prevent abuse and denial-of-service attacks.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Input validation:</strong> All user inputs and file uploads are validated and sanitized server-side.</span>
              </li>
            </ul>
          </SecurityCard>

          <SecurityCard icon={<Shield className="w-4 h-4" />} title="POPIA Compliance">
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Purpose limitation:</strong> We only process your data for the specific purpose of bank statement analysis.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Data minimisation:</strong> We only collect data that is necessary for the Service to function.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Your rights:</strong> You have full rights to access, correct, delete, and export your data. See our <Link href="/privacy" className="text-blue-500 hover:underline">Privacy Policy</Link> for details.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                <span><strong>Information Regulator:</strong> You can lodge complaints with the South African Information Regulator if you believe your rights have been infringed.</span>
              </li>
            </ul>
          </SecurityCard>
        </div>

        {/* Reporting */}
        <div className="mt-12 bg-blue-50 dark:bg-blue-500/5 border border-blue-200 dark:border-blue-500/20 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Report a Security Concern</h2>
          <p className="text-[15px] text-neutral-600 dark:text-neutral-400 leading-relaxed">
            If you discover a security vulnerability or have concerns about the security of your data, 
            please contact us immediately at{' '}
            <a href="mailto:support@reconex.co.za" className="text-blue-500 hover:underline">support@reconex.co.za</a>. 
            We take all reports seriously and will respond within 24 hours.
          </p>
        </div>

        {/* Back link */}
        <div className="mt-12 pt-8 border-t border-neutral-200 dark:border-neutral-800">
          <Link href="/" className="text-sm text-blue-500 hover:underline">&larr; Back to Reconex</Link>
        </div>
      </div>
    </div>
  )
}
