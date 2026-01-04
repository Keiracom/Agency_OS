"use client"

// EXPERT PANEL LANDING PAGE
// Crafted by: Ogilvy + Wiebe + Schwartz + Brunson + Godin
// Date: December 31, 2025

import { GlassNav } from "@/components/glass-nav"
import { HeroSection } from "@/components/hero-section-expert"
import { SocialProofStrip } from "@/components/social-proof-strip"
import { ProblemSection } from "@/components/problem-section"
import { ProductDemo } from "@/components/product-demo"
import { HowItWorks } from "@/components/how-it-works"
import { FeaturesGrid } from "@/components/features-grid"
import { PricingSection } from "@/components/pricing-section-expert"
import { FAQSection } from "@/components/faq-section"
import { WaitlistSection } from "@/components/waitlist-section-expert"
import { Footer } from "@/components/footer"

export default function ExpertLandingPage() {
  return (
    <div className="min-h-screen bg-[#fafafa]">
      <GlassNav />
      <main>
        {/* 1. Hero - Ogilvy headline + Brunson urgency + Wiebe customer voice */}
        <HeroSection />
        
        {/* 2. Social Proof Strip - Quick credibility */}
        <SocialProofStrip />
        
        {/* 3. Problem Section - Schwartz awareness bridge */}
        <ProblemSection />
        
        {/* 4. Product Demo - Visual mechanism reveal */}
        <ProductDemo />
        
        {/* 5. How It Works - 5-phase engine */}
        <HowItWorks />
        
        {/* 6. Features Grid - Godin differentiation */}
        <FeaturesGrid />
        
        {/* 7. Pricing - Brunson founding offer */}
        <PricingSection />
        
        {/* 8. FAQ - Wiebe objection handling */}
        <FAQSection />
        
        {/* 9. Final CTA - Godin enrollment */}
        <WaitlistSection />
      </main>
      <Footer />
    </div>
  )
}
