'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Menu, X } from 'lucide-react'

export default function LandingNav() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const navLinks = [
    { href: '#features', label: 'Features' },
    { href: '#how-it-works', label: 'How It Works' },
    { href: '#faq', label: 'FAQ' },
  ]

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? 'bg-neutral-950/90 backdrop-blur-2xl border-b border-neutral-800/50 shadow-lg shadow-black/10'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-18">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/40 transition-shadow duration-300">
                <span className="text-white font-bold text-sm">R</span>
              </div>
              <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-blue-400 to-indigo-500 blur-md opacity-0 group-hover:opacity-40 transition-opacity duration-300" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight hidden sm:block">
              recon<span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">ex</span>
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="animated-underline px-3 py-2 text-[13px] font-medium text-neutral-400 hover:text-white transition-colors rounded-lg hover:bg-white/[0.04]"
              >
                {l.label}
              </Link>
            ))}
          </div>

          {/* Desktop auth */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="text-[13px] font-medium text-neutral-400 hover:text-white transition-colors px-3 py-2"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="group relative px-5 py-2.5 text-[13px] font-semibold rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 transition-all duration-300 shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30"
            >
              <span className="relative z-10">Get Started</span>
              <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-blue-400 to-indigo-400 blur-lg opacity-0 group-hover:opacity-30 transition-opacity duration-300" />
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/[0.06] transition-all duration-200"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      <div
        className={`md:hidden border-t border-neutral-800/50 bg-neutral-950/98 backdrop-blur-2xl overflow-hidden transition-all duration-300 ${
          mobileOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 py-4 space-y-1">
          {navLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-3 rounded-xl text-sm font-medium text-neutral-400 hover:bg-white/[0.04] hover:text-white transition-all duration-200"
            >
              {l.label}
            </Link>
          ))}
          <div className="pt-4 mt-3 border-t border-neutral-800/50 flex flex-col gap-2">
            <Link
              href="/login"
              onClick={() => setMobileOpen(false)}
              className="px-4 py-3 rounded-xl text-sm font-medium text-neutral-400 hover:bg-white/[0.04] transition-colors text-center"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              onClick={() => setMobileOpen(false)}
              className="px-4 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 transition-all duration-300 text-center"
            >
              Get Started
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
