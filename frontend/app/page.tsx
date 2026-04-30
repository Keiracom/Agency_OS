"use client";

/**
 * FILE: frontend/app/page.tsx
 * PURPOSE: Premium landing page combining Expert Panel animations + Buyer Guide ROI math
 * AESTHETIC: Dynamic gradients, floating orbs, glass morphism, scroll-triggered animations
 * SELLING POINTS: SDR comparison, cost-per-meeting, ROI breakdown
 * NOTE: ISR removed - incompatible with "use client". Founding spots fetched client-side.
 */

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { WaitlistForm } from "@/components/marketing/waitlist-form";
import { useFoundingSpots } from "@/components/marketing/founding-spots";
import { FoundingDepositButton } from "@/components/billing/StripeCheckoutButton";
import { FloatingFoundingSpots } from "@/components/marketing/floating-founding-spots";
import HeroSection from "@/components/landing/HeroSection";
import TypingDemo from "@/components/landing/TypingDemo";
import HowItWorksCarousel from "@/components/landing/HowItWorksCarousel";
import DashboardDemo from "@/components/landing/DashboardDemo";
import {
  Search,
  Eye,
  BarChart3,
  Rocket,
  Calendar,
  Globe,
  Brain,
  Target,
  DollarSign,
  Mail,
  Shield,
  Phone,
  Unlock,
  Lock,
  Smartphone,
  CreditCard,
} from "lucide-react";

// Custom hook for intersection observer animations
function useScrollAnimation() {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

// Animated counter component
function AnimatedCounter({ target, suffix = "", prefix = "" }: { target: number; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState(0);
  const { ref, isVisible } = useScrollAnimation();

  useEffect(() => {
    if (!isVisible) return;
    
    const duration = 2000;
    const steps = 60;
    const increment = target / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [isVisible, target]);

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}{count.toLocaleString()}{suffix}
    </span>
  );
}

// Scroll reveal wrapper
function ScrollReveal({ 
  children, 
  className = "", 
  delay = 0 
}: { 
  children: React.ReactNode; 
  className?: string; 
  delay?: number;
}) {
  const { ref, isVisible } = useScrollAnimation();

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${className}`}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "translateY(0)" : "translateY(30px)",
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

export default function LandingPage() {
  const { remaining: spotsRemaining, soldOut, isUrgent } = useFoundingSpots();

  return (
    <main className="min-h-screen bg-bg-panel text-ink antialiased overflow-x-hidden">
      {/* Custom Styles */}
      <style jsx global>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(3deg); }
        }
        
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 1; }
          100% { transform: scale(2); opacity: 0; }
        }
        
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }

        @keyframes slide-up {
          from { opacity: 0; transform: translateY(40px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .animate-float { animation: float 20s ease-in-out infinite; }
        .animate-float-delayed { animation: float 25s ease-in-out infinite; animation-delay: -10s; }
        .animate-gradient { 
          background-size: 200% 200%;
          animation: gradient-shift 8s ease infinite;
        }
        .animate-slide-up {
          animation: slide-up 0.8s ease-out forwards;
        }
        
        .glass {
          background: rgba(255,255,255,0.04);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
        }
        
        .gradient-text {
          background: linear-gradient(135deg, #D4956A 0%, #E8B48A 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .card-hover {
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .card-hover:hover {
          transform: translateY(-8px);
          box-shadow: 0 25px 50px -12px rgba(212,149,106,0.15);
        }

        .btn-gradient {
          background: linear-gradient(135deg, #D4956A 0%, #E8B48A 100%);
          transition: all 0.3s ease;
        }
        .btn-gradient:hover {
          opacity: 0.95;
          transform: translateY(-2px);
          box-shadow: 0 20px 40px rgba(212,149,106,0.35);
        }
      `}</style>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg shadow-amber/25" style={{ background: "#D4956A" }}>
                <span className="text-ink font-bold text-sm">A</span>
              </div>
              <span className="font-bold text-xl tracking-tight">Agency OS</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm font-medium text-ink-3 hover:text-ink transition-colors">Features</a>
              <a href="#how-it-works" className="text-sm font-medium text-ink-3 hover:text-ink transition-colors">How It Works</a>
              <a href="#comparison" className="text-sm font-medium text-ink-3 hover:text-ink transition-colors">ROI</a>
              <a href="#pricing" className="text-sm font-medium text-ink-3 hover:text-ink transition-colors">Pricing</a>
            </div>
            
            <div className="flex items-center gap-4">
              <Link href="/login" className="hidden sm:block text-sm font-medium text-ink-3 hover:text-ink transition-colors">
                Sign in
              </Link>
              <a href="#pricing" className="btn-gradient text-ink px-5 py-2.5 rounded-xl font-semibold text-sm shadow-lg">
                Claim Your Spot
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section className="relative overflow-hidden pt-32 pb-20 md:pt-40 md:pb-32 bg-bg-cream">
        {/* Floating orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 left-10 w-[500px] h-[500px] bg-gradient-to-r from-amber/10 to-amber-light/10 rounded-full blur-3xl animate-float" />
          <div className="absolute top-40 right-10 w-[600px] h-[600px] bg-gradient-to-r from-amber/08 to-amber/08 rounded-full blur-3xl animate-float-delayed" />
          <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px] bg-gradient-to-r from-amber/06 to-amber/06 rounded-full blur-3xl animate-float" style={{ animationDelay: "-5s" }} />
        </div>

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="flex flex-col items-center text-center">
            
            {/* Urgency Badge */}
            <div className="inline-flex items-center gap-2.5 rounded-full border border-amber/30 bg-amber-glow px-5 py-2.5 text-sm mb-8 animate-slide-up shadow-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber"></span>
              </span>
              <span className="font-semibold text-amber">
                {soldOut ? "Founding spots sold out!" : `Founding Offer: ${spotsRemaining ?? "..."} of 20 spots remaining`}
              </span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6 max-w-5xl animate-slide-up" style={{ animationDelay: "100ms" }}>
              Your next clients are already out there.
              <span className="gradient-text"> We find them, qualify them, and book them.</span>
            </h1>

            {/* Audience qualifier */}
            <p className="text-sm font-medium text-ink-3 uppercase tracking-wider mb-6 animate-slide-up" style={{ animationDelay: "150ms" }}>
              For Australian marketing agencies only
            </p>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-ink-3 max-w-3xl leading-relaxed mb-10 animate-slide-up" style={{ animationDelay: "200ms" }}>
              Agency OS runs your outbound acquisition across 5 channels while you focus on doing the work. 
              Booked meetings. Not leads. 
              
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-6 animate-slide-up" style={{ animationDelay: "300ms" }}>
              <a href="#pricing" className="btn-gradient text-ink px-10 py-4 rounded-xl font-semibold text-lg shadow-xl inline-flex items-center gap-2 group">
                Claim Your Founding Spot
                <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
              </a>
              <a href="#comparison" className="text-ink-3 hover:text-ink font-medium py-3 inline-flex items-center gap-2 group">
                <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                See how it works
              </a>
            </div>

            {/* Trust signals */}
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-ink-3 mb-16 animate-slide-up" style={{ animationDelay: "350ms" }}>
              <span>✓ Lock in 50% off for life</span>
              <span>✓ 3 booked meetings guaranteed or full refund</span>
              <span>✓ Cancel anytime</span>
            </div>

            {/* Animated Dashboard Demo */}
            <div className="w-full max-w-5xl animate-slide-up" style={{ animationDelay: "400ms" }}>
              <DashboardDemo />
            </div>
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF METRICS */}
      <section className="py-16 border-y border-white/10 bg-bg-panel">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
            {[
              { value: 55, suffix: "%+", label: "Open rate", sub: "Industry avg: 15-20%" },
              { value: 12, suffix: "%+", label: "Reply rate", sub: "3x typical cold email" },
              { value: 14, prefix: "<", suffix: " days", label: "To first meeting", sub: "From campaign launch" },
              { value: 5, suffix: " channels", label: "Unified", sub: "One dashboard" },
            ].map((stat, i) => (
              <ScrollReveal key={i} delay={i * 100}>
                <div className="flex flex-col items-center text-center">
                  <div className="text-4xl md:text-5xl font-bold gradient-text">
                    <AnimatedCounter target={stat.value} suffix={stat.suffix} prefix={stat.prefix} />
                  </div>
                  <div className="text-sm font-medium text-ink mt-2">{stat.label}</div>
                  <div className="text-xs text-ink-3 mt-0.5">{stat.sub}</div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* LIVE DEMO SECTION - Using v0 Components */}
      <section className="py-20 md:py-28 bg-bg-cream text-ink relative overflow-hidden">
        {/* Subtle background orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-amber/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-amber/08 rounded-full blur-[120px]" />
        </div>

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <ScrollReveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
                See the AI in action
              </h2>
              <p className="text-lg text-ink/60 max-w-2xl mx-auto">
                Watch how Agency OS crafts personalized outreach while you focus on closing deals.
              </p>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={100}>
            <div className="flex justify-center">
              <TypingDemo className="w-full max-w-2xl" />
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20 md:py-28 bg-bg-panel">
        <div className="max-w-7xl mx-auto px-6">
          
          <ScrollReveal>
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
                This isn't another AI sales tool.
              </h2>
              <p className="text-lg text-ink-3 max-w-2xl mx-auto">
                It's your agency's growth operating system.
              </p>
            </div>
          </ScrollReveal>

          {/* Comparison Grid */}
          <ScrollReveal delay={100}>
            <div className="max-w-4xl mx-auto mb-20">
              <div className="grid md:grid-cols-2 gap-8 p-8 rounded-2xl bg-bg-panel border border-white/10 shadow-lg">
                <div>
                  <h3 className="font-bold text-ink-3 uppercase text-sm tracking-wider mb-4">Generic AI SDRs</h3>
                  <ul className="space-y-3">
                    {["Spray-and-pray to any B2B", "US-centric data and timing", "Email-only or email-first", '"Set and forget" black box', "$5,000-10,000/month pricing"].map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-ink-3">
                        <span className="text-amber mt-0.5">✗</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="font-bold gradient-text uppercase text-sm tracking-wider mb-4">Agency OS</h3>
                  <ul className="space-y-3">
                    {["Built around your actual client portfolio", "Australian market, AEST, local compliance", "True 5-channel: Email, SMS, LinkedIn, Voice, Mail", "Conversion Intelligence shows WHY it works", "Founding tier: $375-2,500/month"].map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-ink">
                        <span className="text-amber mt-0.5">✓</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-8">
            <ScrollReveal delay={0}>
              <div className="bg-bg-panel rounded-2xl p-8 border border-white/10 card-hover h-full">
                <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 shadow-lg" style={{ background: "#D4956A" }}>
                  <Globe className="w-7 h-7 text-ink" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Australian-First</h3>
                <p className="text-ink-3 leading-relaxed">Built specifically for Australian agencies. Understands ACMA/DNCR compliance, Aussie business culture, and AEST timing.</p>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={100}>
              <div className="bg-bg-panel rounded-2xl p-8 border border-white/10 card-hover h-full">
                <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 shadow-lg" style={{ background: "#D4956A" }}>
                  <Brain className="w-7 h-7 text-ink" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Conversion Intelligence</h3>
                <p className="text-ink-3 leading-relaxed">ML learns from every interaction. See exactly what subject lines, messages, and timing work for YOUR ideal clients.</p>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={200}>
              <div className="bg-bg-panel rounded-2xl p-8 border border-white/10 card-hover h-full">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-orange-500 to-amber flex items-center justify-center mb-6 shadow-lg">
                  <Target className="w-7 h-7 text-ink" />
                </div>
                <h3 className="text-2xl font-bold mb-4">ALS Score™</h3>
                <p className="text-ink-3 leading-relaxed">Proprietary scoring ranks leads by budget, decision timeline, and agency fit. Focus only on deals worth your time.</p>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS - Instagram-style Carousel */}
      <section className="bg-bg-cream text-ink relative overflow-hidden">
        {/* Subtle background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0f] via-[#0f0f13] to-[#0a0a0f] pointer-events-none" />

        <div className="relative z-10">
          <HowItWorksCarousel />
        </div>
      </section>

      {/* SDR COMPARISON */}
      <section id="comparison" className="py-20 md:py-28 bg-bg-cream text-ink">
        <div className="max-w-6xl mx-auto px-6">
          <ScrollReveal>
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-bg-panel/10 border border-white/20 text-sm mb-6">
                <DollarSign className="w-4 h-4 text-amber" />
                <span className="text-ink/80">The math that matters</span>
              </div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Agency OS vs. Hiring a Junior SDR</h2>
              <p className="text-lg text-ink/60 max-w-2xl mx-auto">The numbers don't lie. Here's what the real comparison looks like.</p>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={100}>
            <div className="overflow-x-auto mb-16">
              <table className="w-full max-w-4xl mx-auto">
                <thead>
                  <tr className="border-b border-white/20">
                    <th className="text-left py-4 px-4 text-ink/60 font-medium">Factor</th>
                    <th className="text-center py-4 px-4 text-ink/60 font-medium">Junior SDR</th>
                    <th className="text-center py-4 px-4 font-medium"><span className="gradient-text">Agency OS (founding)</span></th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    { factor: "Monthly cost", sdr: "$6,500-8,750", aos: "$2,500 (founding)", winner: "aos" },
                    { factor: "Meetings/month", sdr: "8-12 (after ramp)", aos: "15-16", winner: "aos" },
                    { factor: "Cost per meeting", sdr: "$600-900", aos: "$185-200", winner: "aos" },
                    { factor: "Time to first meeting", sdr: "3-4 months", aos: "Week 2-4", winner: "aos" },
                    { factor: "Your time required", sdr: "5-10 hrs/week", aos: "<1 hr/week", winner: "aos" },
                    { factor: "Sick days / Leave", sdr: "Yes", aos: "No", winner: "aos" },
                    { factor: "Turnover risk", sdr: "High (1.8yr tenure)", aos: "None", winner: "aos" },
                    { factor: "Channels covered", sdr: "2-3 (manual)", aos: "5 (automated)", winner: "aos" },
                    { factor: "Works 24/7", sdr: "No", aos: "Yes", winner: "aos" },
                  ].map((row, i) => (
                    <tr key={i} className="border-b border-white/10">
                      <td className="py-4 px-4 text-ink/80">{row.factor}</td>
                      <td className="py-4 px-4 text-center text-ink/50">{row.sdr}</td>
                      <td className="py-4 px-4 text-center">
                        <span className={row.winner === "aos" ? "text-amber font-semibold" : "text-ink/80"}>{row.aos}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ScrollReveal>

          {/* Year 1 Summary */}
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <ScrollReveal delay={200}>
              <div className="p-8 rounded-2xl bg-bg-panel/5 border border-white/10">
                <h3 className="text-lg font-semibold text-ink/60 mb-4">Year 1: Junior SDR</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-ink/60">Total cost</span><span className="text-ink font-semibold">$84,000</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Total meetings</span><span className="text-ink font-semibold">~85</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Cost per meeting</span><span className="text-amber font-semibold">$988</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Your time invested</span><span className="text-ink font-semibold">250-500 hrs</span></div>
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={300}>
              <div className="p-8 rounded-2xl bg-gradient-to-br from-amber/10 to-amber-light/10 border border-amber/30">
                <h3 className="text-lg font-semibold text-amber-light mb-4">Year 1: Agency OS (founding) (founding)</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-ink/60">Total cost</span><span className="text-ink font-semibold">$30,000</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Total meetings</span><span className="text-amber font-semibold">~187</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Cost per meeting</span><span className="text-amber font-semibold">$160</span></div>
                  <div className="flex justify-between"><span className="text-ink/60">Your time invested</span><span className="text-amber font-semibold">&lt;50 hrs</span></div>
                </div>
              </div>
            </ScrollReveal>
          </div>

          <ScrollReveal delay={400}>
            <div className="mt-16 text-center">
              <div className="inline-block p-8 rounded-2xl bg-gradient-to-r from-amber/20 to-amber/20 border border-amber/30">
                <p className="text-3xl md:text-4xl font-bold text-ink mb-3">
                  Save <span className="text-amber">$54,000</span> + Get <span className="text-amber">2.2x</span> more meetings
                </p>
                <p className="text-ink/60">84% lower cost per meeting • 200-450 hours of your time saved • Ramp in weeks</p>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="py-20 md:py-28 bg-bg-panel">
        <div className="max-w-6xl mx-auto px-6">
          <ScrollReveal>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 rounded-full bg-amber-glow border border-amber/30 px-4 py-2 text-sm mb-6">
                <svg className="w-4 h-4 text-amber" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                </svg>
                <span className="font-semibold text-amber">
                  {soldOut ? "Founding spots sold out!" : `Founding Member Pricing — ${spotsRemaining ?? "..."} of 20 spots left`}
                </span>
              </div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Lock in 50% off. Forever.</h2>
              <p className="text-lg text-ink-3 max-w-2xl mx-auto">Founding members keep their rate for life. No contracts. Cancel anytime.</p>
            </div>
          </ScrollReveal>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { name: "Spark", originalPrice: "$750", foundingPrice: "$375", savings: "Save $4.5K/year", expectedMeetings: "All 4 outreach channels", desc: "Launch your outbound engine", limits: ["150 records/month", "All 4 outreach channels • Full AI intelligence • Haiku personalisation"], cta: "Get Started", popular: false },
              { name: "Ignition", originalPrice: "$2,500", foundingPrice: "$1,250", savings: "Save $15K/year", expectedMeetings: "All 4 outreach channels", desc: "Perfect for growing agencies", limits: ["600 records/month", "All 4 outreach channels • Full AI intelligence • Haiku personalisation"], cta: "Claim Your Spot", popular: true },
              { name: "Velocity", originalPrice: "$5,000", foundingPrice: "$2,500", savings: "Save $30K/year", expectedMeetings: "All 4 outreach channels", desc: "Maximum pipeline capacity", limits: ["1,500 records/month", "All 4 outreach channels • Full AI intelligence • Haiku personalisation"], cta: "Get Started", popular: false },
            ].map((tier, i) => (
              <ScrollReveal key={i} delay={i * 100}>
                <div className={`rounded-2xl p-8 card-hover flex flex-col h-full relative ${tier.popular ? "bg-bg-panel border-2 border-amber shadow-xl shadow-amber/10 scale-105" : "bg-bg-panel border border-white/10"}`}>
                  {tier.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 text-ink px-6 py-1.5 rounded-full text-sm font-semibold shadow-lg flex items-center gap-1" style={{ background: "linear-gradient(135deg, #D4956A 0%, #E8B48A 100%)" }}>
                      <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>
                      Most Chosen
                    </div>
                  )}
                  <div className="mb-6">
                    <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                    <p className="text-ink-3 text-sm mb-4">{tier.desc}</p>
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-5xl font-bold tracking-tight">{tier.foundingPrice}</span>
                      <span className="text-ink-3 text-lg">/mo</span>
                    </div>
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-ink-3 line-through text-sm">Was {tier.originalPrice}/mo</span>
                      <span className="text-xs font-semibold text-amber bg-amber-glow px-2 py-0.5 rounded">{tier.savings}</span>
                    </div>
                    {/* Expected Meetings Highlight */}
                    <div className={`p-3 rounded-xl ${tier.popular ? "bg-gradient-to-r from-amber/10 to-amber-light/10 border border-amber/30" : "bg-gradient-to-r from-amber/5 to-amber-light/5 border border-amber/20"}`}>
                      <div className="flex items-center gap-2">
                        <Calendar className={`w-5 h-5 ${tier.popular ? "text-amber" : "text-amber"}`} />
                        <span className={`text-sm font-bold ${tier.popular ? "text-amber" : "text-amber"}`}>{tier.expectedMeetings}</span>
                      </div>
                    </div>
                  </div>
                  <ul className="space-y-3 mb-8 flex-grow">
                    {tier.limits.map((limit, j) => (
                      <li key={j} className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-amber shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                        </svg>
                        <span className="text-sm text-ink-3 font-medium">{limit}</span>
                      </li>
                    ))}
                  </ul>
                  <a href="#waitlist" className={`w-full py-3 px-6 rounded-xl font-semibold text-center transition-all ${tier.popular ? "btn-gradient text-ink" : "border-2 border-white/10 text-ink-3 hover:border-amber hover:text-amber"}`}>
                    {tier.cta}
                  </a>
                </div>
              </ScrollReveal>
            ))}
          </div>

          {/* All Plans Include */}
          <ScrollReveal delay={200}>
            <div className="max-w-4xl mx-auto mt-16">
              <h3 className="text-xl font-bold text-center mb-8 text-ink">All plans include</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { icon: Mail, label: "Full 5-channel outreach", sub: "Email, LinkedIn, Voice AI, SMS, Direct Mail" },
                  { icon: Brain, label: "Advanced Conversion Intelligence", sub: "ML learns what works for you" },
                  { icon: Target, label: "ALS lead scoring", sub: "Prioritize your best prospects" },
                  { icon: BarChart3, label: "All reporting & analytics", sub: "Real-time dashboard" },
                  { icon: Globe, label: "API access", sub: "Integrate with your stack" },
                  { icon: Shield, label: "Priority support", sub: "We're here when you need us" },
                ].map((feature, i) => (
                  <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-bg-panel border border-white/06">
                    <feature.icon className="w-5 h-5 text-amber shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-ink">{feature.label}</p>
                      <p className="text-xs text-ink-3">{feature.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={300}>
            <div className="max-w-3xl mx-auto mt-16">
              <div className="rounded-2xl p-8 bg-bg-elevated border border-amber/20 text-center">
                <h3 className="text-xl font-bold mb-4">The ROI Math</h3>
                <p className="text-3xl font-bold text-amber mb-3">Close ONE new client → Pay for an entire year</p>
                <p className="text-ink-3">At $1,250/month founding price, one new client at a $5,000/month retainer covers 4 months of Agency OS.</p>
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={400}>
            <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 mt-12 text-sm text-ink-3">
              <span className="inline-flex items-center gap-1.5"><Shield className="w-4 h-4" /> Australian Privacy Act Compliant</span>
              <span className="inline-flex items-center gap-1.5"><Smartphone className="w-4 h-4" /> DNCR Integration Built-In</span>
              <span className="inline-flex items-center gap-1.5"><CreditCard className="w-4 h-4" /> Cancel Anytime—No Lock-In</span>
              <span className="inline-flex items-center gap-1.5"><Globe className="w-4 h-4" /> Built for Australian Agencies</span>
            </div>
            {/* Ramp Clause */}
            <p className="text-center text-xs text-ink-3 mt-6">
              *Full guarantee kicks in after 30-day onboarding period
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* FINAL CTA */}
      <section id="waitlist" className="py-20 md:py-28 bg-bg-cream">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <ScrollReveal>
              <div>
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
                  20 agencies will build the future of agency growth.
                  <span className="gradient-text"> Will you be one of them?</span>
                </h2>
                <p className="text-lg text-ink-3 mb-8">Most agencies will wait. Wait until it's proven. Wait until everyone has it. Wait until competitive advantage disappears.</p>
                <p className="text-lg font-medium text-ink mb-8">The agencies that win don't wait. They move first.</p>
                <div className="space-y-4">
                  {["Lock in 50% off for life", "Direct line to the product team", "White-glove onboarding"].map((item, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-amber-glow flex items-center justify-center">
                        <svg className="w-4 h-4 text-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                        </svg>
                      </div>
                      <span className="text-ink-3">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={200}>
              <div className="bg-bg-panel rounded-2xl p-8 border border-white/10 shadow-xl">
                <div className="flex items-center justify-center gap-2 mb-6">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-amber"></span>
                  </span>
                  <span className="text-sm font-medium text-ink-3">
                    {soldOut ? "Founding spots sold out!" : `${spotsRemaining ?? "..."} founding spots remaining`}
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-center mb-2">Claim your founding spot</h3>
                <p className="text-ink-3 text-sm text-center mb-6">$500 AUD • Funds your pilot campaign • 3 meetings guaranteed or full refund</p>
                {/* Step 8/8: Stripe Checkout Button */}
                <FoundingDepositButton spotsRemaining={spotsRemaining ?? undefined} />
                <div className="mt-6 pt-6 border-t border-white/06">
                  <div className="grid grid-cols-2 gap-4 text-xs text-ink-3">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-amber" />
                      <span>Australian Privacy Compliant</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-amber" />
                      <span>DNCR Integrated</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Unlock className="w-4 h-4 text-amber" />
                      <span>Cancel Anytime</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-amber" />
                      <span>Built in Australia</span>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-bg-cream text-ink-3 py-12">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "#D4956A" }}>
                  <span className="text-ink font-bold text-sm">A</span>
                </div>
                <span className="font-bold text-xl text-ink">Agency OS</span>
              </div>
              <p className="text-sm leading-relaxed mb-4 max-w-sm">The client acquisition operating system for Australian marketing agencies.</p>
            </div>
            <div>
              <h4 className="font-semibold text-ink mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-ink transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-ink transition-colors">Pricing</a></li>
                <li><a href="#how-it-works" className="hover:text-ink transition-colors">How It Works</a></li>
                <li><a href="#comparison" className="hover:text-ink transition-colors">ROI Calculator</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-ink mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/about" className="hover:text-ink transition-colors">About</Link></li>
                <li><a href="#" className="hover:text-ink transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-ink transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-ink transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm">© 2026 Agency OS. All rights reserved.</p>
            <p className="text-sm inline-flex items-center gap-1.5"><Globe className="w-4 h-4" /> Proudly built in Australia, for Australian agencies.</p>
          </div>
        </div>
      </footer>

      {/* Floating Founding Spots Counter */}
      <FloatingFoundingSpots />
    </main>
  );
}
