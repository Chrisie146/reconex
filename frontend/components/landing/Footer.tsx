import Link from 'next/link'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer id="contact" className="bg-neutral-950 text-neutral-400 border-t border-neutral-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <span className="text-lg font-bold text-white tracking-tight">
                recon<span className="text-blue-400">ex</span>
              </span>
            </div>
            <p className="text-sm text-neutral-500 max-w-sm leading-relaxed">
              Bank statement analysis for South African businesses,
              bookkeepers and accountants. Upload, categorize, export.
            </p>
          </div>

          {/* Product */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-600 mb-4">
              Product
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="#features" className="hover:text-white transition-colors">Features</Link></li>
              <li><Link href="#how-it-works" className="hover:text-white transition-colors">How It Works</Link></li>
              <li><Link href="#pricing" className="hover:text-white transition-colors">Pricing</Link></li>
              <li><Link href="/register" className="hover:text-white transition-colors">Get Started</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-neutral-600 mb-4">
              Support
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="#faq" className="hover:text-white transition-colors">FAQ</Link></li>
              <li><a href="mailto:support@reconex.co.za" className="hover:text-white transition-colors">support@reconex.co.za</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-neutral-900">
          <p className="text-xs text-neutral-600 text-center">
            &copy; {currentYear} Reconex. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
