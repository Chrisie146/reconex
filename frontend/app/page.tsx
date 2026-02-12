import LandingNav from '@/components/landing/LandingNav'
import Hero from '@/components/landing/Hero'
import Features from '@/components/landing/Features'
import HowItWorks from '@/components/landing/HowItWorks'
import Screenshots from '@/components/landing/Screenshots'
import Pricing from '@/components/landing/Pricing'
import CTA from '@/components/landing/CTA'
import FAQ from '@/components/landing/FAQ'
import Footer from '@/components/landing/Footer'

export default function LandingPage() {
  return (
    <main className="bg-white">
      <LandingNav />
      <Hero />
      <Features />
      <HowItWorks />
      <Screenshots />
      <Pricing />
      <CTA />
      <FAQ />
      <Footer />
    </main>
  )
}
