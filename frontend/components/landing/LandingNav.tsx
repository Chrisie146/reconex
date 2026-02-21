'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Landmark, Menu, X } from 'lucide-react'

export default function LandingNav() {
  const [mobileOpen, setMobileOpen] = useState(false)

  const navLinks = [
    { href: '#features', label: 'Features' },
    { href: '#how-it-works', label: 'How It Works' },
    { href: '#pricing', label: 'Pricing' },
    { href: '#faq', label: 'FAQ' },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white/90 backdrop-blur-md border-b border-neutral-200/80 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Landmark className="w-[18px] h-[18px] text-white" />
            </div>
            <span className="text-lg font-bold text-neutral-900 hidden sm:block tracking-tight">
              StatementBur
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-7">
            {navLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-[13px] font-medium text-neutral-500 hover:text-indigo-600 transition-colors"
              >
                {l.label}
              </Link>
            ))}
          </div>

          {/* Desktop auth */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="text-[13px] font-medium text-neutral-600 hover:text-indigo-600 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 text-[13px] font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg text-neutral-500 hover:bg-neutral-100 transition-colors"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="md:hidden border-t border-neutral-200/80 bg-white">
          <div className="px-4 py-3 space-y-1">
            {navLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2.5 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 hover:text-indigo-600 transition-colors"
              >
                {l.label}
              </Link>
            ))}
            <div className="pt-3 mt-2 border-t border-neutral-100 flex flex-col gap-2">
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors text-center"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors text-center"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
