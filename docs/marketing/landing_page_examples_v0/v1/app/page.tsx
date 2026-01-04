"use client"

import { GlassNav } from "@/components/glass-nav"
import { HeroSection } from "@/components/hero-section"
import { SocialProofStrip } from "@/components/social-proof-strip"
import { ProductDemo } from "@/components/product-demo"
import { HowItWorks } from "@/components/how-it-works"
import { FeaturesGrid } from "@/components/features-grid"
import { PricingSection } from "@/components/pricing-section"
import { WaitlistSection } from "@/components/waitlist-section"
import { Footer } from "@/components/footer"

export default function Page() {
  return (
    <div className="min-h-screen bg-[#fafafa]">
      <GlassNav />
      <main>
        <HeroSection />
        <SocialProofStrip />
        <ProductDemo />
        <HowItWorks />
        <FeaturesGrid />
        <PricingSection />
        <WaitlistSection />
      </main>
      <Footer />
    </div>
  )
}
