import Link from 'next/link'
import { Shield, Lock, Server } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer id="contact" className="bg-neutral-950 text-neutral-400 border-t border-neutral-900 relative overflow-hidden">
      {/* Subtle gradient */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px] bg-gradient-to-r from-transparent via-neutral-700 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 relative">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mb-14">
          {/* Brand */}
          <div className="col-span-1 md:col-span-5">
            <Link href="/" className="flex items-center gap-2.5 mb-5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/10">
                <span className="text-white font-bold text-sm">R</span>
              </div>
              <span className="text-lg font-bold text-white tracking-tight">
                recon<span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">ex</span>
              </span>
            </Link>
            <p className="text-sm text-neutral-500 max-w-sm leading-relaxed mb-6">
              Bank statement analysis for South African businesses,
              bookkeepers and accountants. Upload, categorize, export.
            </p>

            {/* Trust badges */}
            <div className="flex flex-wrap gap-3">
              {[
                { icon: Shield, label: 'Encrypted' },
                { icon: Lock, label: 'Secure Auth' },
                { icon: Server, label: 'Cloud Storage' },
              ].map((badge) => (
                <div key={badge.label} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-neutral-900/60 border border-neutral-800/50 text-[11px] text-neutral-500">
                  <badge.icon className="w-3 h-3" />
                  {badge.label}
                </div>
              ))}
            </div>
          </div>

          {/* Product */}
          <div className="md:col-span-2">
            <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-600 mb-5">
              Product
            </p>
            <ul className="space-y-3 text-sm">
              <li><Link href="#features" className="hover:text-white transition-colors duration-200">Features</Link></li>
              <li><Link href="#how-it-works" className="hover:text-white transition-colors duration-200">How It Works</Link></li>
              <li><Link href="#pricing" className="hover:text-white transition-colors duration-200">Pricing</Link></li>
              <li><Link href="/register" className="hover:text-white transition-colors duration-200">Get Started</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div className="md:col-span-2">
            <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-600 mb-5">
              Company
            </p>
            <ul className="space-y-3 text-sm">
              <li><Link href="/privacy" className="hover:text-white transition-colors duration-200">Privacy Policy</Link></li>
              <li><Link href="/security" className="hover:text-white transition-colors duration-200">Security</Link></li>
              <li><Link href="/terms" className="hover:text-white transition-colors duration-200">Terms of Service</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div className="md:col-span-3">
            <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-600 mb-5">
              Support
            </p>
            <ul className="space-y-3 text-sm">
              <li><Link href="#faq" className="hover:text-white transition-colors duration-200">FAQ</Link></li>
              <li><a href="mailto:support@reconex.co.za" className="hover:text-white transition-colors duration-200">support@reconex.co.za</a></li>
            </ul>

            {/* SA-specific trust note */}
            <div className="mt-8 p-3 rounded-lg bg-neutral-900/40 border border-neutral-800/40">
              <p className="text-[11px] text-neutral-500 leading-relaxed">
                <span className="text-neutral-400 font-medium">Built for South Africa</span> — Supports 6 major SA banks, 15% VAT calculation, and ZAR currency formatting.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-neutral-900 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-neutral-600">
            &copy; {currentYear} Reconex. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs">
            <Link href="/privacy" className="text-neutral-600 hover:text-neutral-400 transition-colors duration-200">Privacy</Link>
            <Link href="/security" className="text-neutral-600 hover:text-neutral-400 transition-colors duration-200">Security</Link>
            <Link href="/terms" className="text-neutral-600 hover:text-neutral-400 transition-colors duration-200">Terms</Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
