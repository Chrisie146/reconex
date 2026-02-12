import Link from 'next/link'

export default function CTA() {
  return (
    <section className="py-24 bg-gradient-to-br from-blue-600 to-blue-800 text-white relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full filter blur-3xl"></div>
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full filter blur-3xl"></div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        {/* Main Heading */}
        <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
          Ready to Transform Your
          <span className="block mt-2">Financial Analysis?</span>
        </h2>

        {/* Subheading */}
        <p className="text-xl sm:text-2xl text-blue-100 mb-12 max-w-3xl mx-auto">
          Join hundreds of businesses already saving hours every month with automated 
          bank statement analysis. Start for free in 60 seconds.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
          <Link 
            href="/dashboard" 
            className="px-10 py-5 bg-white text-blue-600 hover:bg-blue-50 font-bold rounded-lg shadow-2xl transition-all transform hover:scale-105 text-lg"
          >
            Get Started Free →
          </Link>
          <Link 
            href="#features" 
            className="px-10 py-5 bg-blue-700 hover:bg-blue-600 text-white font-semibold rounded-lg transition-all border-2 border-blue-400 text-lg"
          >
            Learn More
          </Link>
        </div>

        {/* Trust Indicators */}
        <div className="flex flex-wrap justify-center items-center gap-8 text-blue-100">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-green-300" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-lg">No credit card required</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-green-300" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-lg">Free forever plan</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-green-300" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-lg">Start immediately</span>
          </div>
        </div>
      </div>
    </section>
  )
}
