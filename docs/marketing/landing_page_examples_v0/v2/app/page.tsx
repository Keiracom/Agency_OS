import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { LogosSection } from "@/components/logos-section"
import { ProductDemo } from "@/components/product-demo"
import { TestimonialsSection } from "@/components/testimonials-section"
import { PricingSection } from "@/components/pricing-section"
import { WaitlistSection } from "@/components/waitlist-section"
import { Footer } from "@/components/footer"

export default function Page() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <HeroSection />
        <LogosSection />
        <ProductDemo />
        <TestimonialsSection />
        <PricingSection />
        <WaitlistSection />
      </main>
      <Footer />
    </div>
  )
}
