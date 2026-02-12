import Link from 'next/link'

export default function LandingNav() {
  return (
    <nav className="fixed top-0 left-0 right-0 bg-white/95 backdrop-blur-sm border-b border-neutral-200 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">$</span>
            </div>
            <span className="text-xl font-bold text-neutral-900 hidden sm:block">Statement Analyzer</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="#features" className="text-neutral-600 hover:text-blue-600 font-medium transition-colors">
              Features
            </Link>
            <Link href="#how-it-works" className="text-neutral-600 hover:text-blue-600 font-medium transition-colors">
              How It Works
            </Link>
            <Link href="#pricing" className="text-neutral-600 hover:text-blue-600 font-medium transition-colors">
              Pricing
            </Link>
            <Link href="#faq" className="text-neutral-600 hover:text-blue-600 font-medium transition-colors">
              FAQ
            </Link>
            <Link 
              href="/dashboard" 
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all shadow-sm"
            >
              Get Started →
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <Link 
            href="/dashboard" 
            className="md:hidden px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all text-sm"
          >
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  )
}
