/**
 * FILE: frontend/app/page.tsx
 * PURPOSE: Premium landing page combining Expert Panel animations + Buyer Guide ROI math
 * AESTHETIC: Dynamic gradients, floating orbs, glass morphism, scroll-triggered animations
 * SELLING POINTS: SDR comparison, cost-per-meeting, ROI breakdown
 */

"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { WaitlistForm } from "@/components/marketing/waitlist-form";
import { useFoundingSpots } from "@/components/marketing/founding-spots";
import { FloatingFoundingSpots } from "@/components/marketing/floating-founding-spots";
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
    <main className="min-h-screen bg-gray-50 text-gray-900 antialiased overflow-x-hidden">
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
          background: rgba(255, 255, 255, 0.85);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
        }
        
        .gradient-text {
          background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .card-hover {
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .card-hover:hover {
          transform: translateY(-8px);
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
        }

        .btn-gradient {
          background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
          transition: all 0.3s ease;
        }
        .btn-gradient:hover {
          opacity: 0.95;
          transform: translateY(-2px);
          box-shadow: 0 20px 40px rgba(59, 130, 246, 0.35);
        }
      `}</style>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-gray-200/50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <span className="text-white font-bold text-sm">A</span>
              </div>
              <span className="font-bold text-xl tracking-tight">Agency OS</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Features</a>
              <a href="#how-it-works" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">How It Works</a>
              <a href="#comparison" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">ROI</a>
              <a href="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Pricing</a>
            </div>
            
            <div className="flex items-center gap-4">
              <Link href="/login" className="hidden sm:block text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
                Sign in
              </Link>
              <a href="#pricing" className="btn-gradient text-white px-5 py-2.5 rounded-xl font-semibold text-sm shadow-lg">
                Claim Your Spot
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section className="relative overflow-hidden pt-32 pb-20 md:pt-40 md:pb-32 bg-gradient-to-b from-white via-gray-50/50 to-gray-50">
        {/* Floating orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 left-10 w-[500px] h-[500px] bg-gradient-to-r from-blue-400/20 to-purple-500/20 rounded-full blur-3xl animate-float" />
          <div className="absolute top-40 right-10 w-[600px] h-[600px] bg-gradient-to-r from-purple-400/15 to-pink-500/15 rounded-full blur-3xl animate-float-delayed" />
          <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px] bg-gradient-to-r from-cyan-400/10 to-blue-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: "-5s" }} />
        </div>

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="flex flex-col items-center text-center">
            
            {/* Urgency Badge */}
            <div className="inline-flex items-center gap-2.5 rounded-full border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 px-5 py-2.5 text-sm mb-8 animate-slide-up shadow-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              </span>
              <span className="font-semibold text-amber-800">
                {soldOut ? "Founding spots sold out!" : `Founding Offer: ${spotsRemaining ?? "..."} of 20 spots remaining`}
              </span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6 max-w-5xl animate-slide-up" style={{ animationDelay: "100ms" }}>
              Find perfect-fit leads and book meetings
              <span className="gradient-text"> — while you focus on client work.</span>
            </h1>

            {/* Audience qualifier */}
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-6 animate-slide-up" style={{ animationDelay: "150ms" }}>
              For Australian marketing agencies only
            </p>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-gray-600 max-w-3xl leading-relaxed mb-10 animate-slide-up" style={{ animationDelay: "200ms" }}>
              You started an agency to do great work—not to spend 60% of your time chasing leads. 
              Agency OS finds, qualifies, and books meetings with ideal clients across 5 channels. 
              <span className="text-gray-900 font-medium">You just show up and close.</span>
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-6 animate-slide-up" style={{ animationDelay: "300ms" }}>
              <a href="#pricing" className="btn-gradient text-white px-10 py-4 rounded-xl font-semibold text-lg shadow-xl inline-flex items-center gap-2 group">
                Claim Your Founding Spot
                <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
              </a>
              <a href="#comparison" className="text-gray-600 hover:text-gray-900 font-medium py-3 inline-flex items-center gap-2 group">
                <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                See the ROI math
              </a>
            </div>

            {/* Trust signals */}
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-gray-500 mb-16 animate-slide-up" style={{ animationDelay: "350ms" }}>
              <span>✓ Lock in 50% off for life</span>
              <span>✓ Booking results guaranteed or your money back</span>
              <span>✓ Cancel anytime</span>
            </div>

            {/* Dashboard Preview */}
            <div className="w-full max-w-5xl animate-slide-up" style={{ animationDelay: "400ms" }}>
              <div className="relative w-full aspect-video rounded-2xl overflow-hidden shadow-2xl border border-gray-200 bg-white group hover:shadow-blue-500/20 transition-all duration-500">
                {/* Browser chrome */}
                <div className="absolute top-0 left-0 right-0 h-10 bg-gray-100 border-b border-gray-200 flex items-center px-4 gap-2 z-10">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                  </div>
                  <div className="flex-1 mx-4">
                    <div className="bg-white rounded px-3 py-1 text-xs text-gray-500 max-w-sm mx-auto flex items-center justify-center gap-2">
                      <Lock className="w-3 h-3 text-green-500" />
                      app.agencyos.com.au/dashboard
                    </div>
                  </div>
                </div>
                
                {/* Dashboard mockup */}
                <div className="pt-10 h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    {[
                      { label: "Pipeline Value", value: "$284K", change: "↑ 23% this month", color: "text-green-400" },
                      { label: "Meetings Booked", value: "47", change: "↑ 12 this week", color: "text-green-400" },
                      { label: "Reply Rate", value: "12.4%", change: "3x industry avg", color: "text-blue-400" },
                      { label: "Active Leads", value: "2,847", change: "Across 5 channels", color: "text-purple-400" },
                    ].map((stat, i) => (
                      <div key={i} className="bg-white/5 backdrop-blur rounded-lg p-4 border border-white/10">
                        <div className="text-xs text-gray-400 mb-1">{stat.label}</div>
                        <div className="text-2xl font-bold text-white">{stat.value}</div>
                        <div className={`text-xs ${stat.color}`}>{stat.change}</div>
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="col-span-2 bg-white/5 backdrop-blur rounded-lg p-4 border border-white/10">
                      <div className="text-sm font-semibold mb-3 flex items-center gap-2 text-white">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                        Live Activity Feed
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-gray-300 bg-blue-500/10 rounded p-2 border border-blue-500/20">
                          <span className="text-green-400">✓</span> Meeting booked with Pixel Studios — Thursday 2pm
                        </div>
                        <div className="flex items-center gap-2 text-gray-300 bg-white/5 rounded p-2">
                          <span className="text-blue-400">→</span> Sarah Williams replied — interested in demo
                        </div>
                        <div className="flex items-center gap-2 text-gray-300 bg-white/5 rounded p-2">
                          <Mail className="w-4 h-4 text-purple-400" /> AI sent personalized email to Marcus Chen
                        </div>
                      </div>
                    </div>
                    <div className="bg-white/5 backdrop-blur rounded-lg p-4 border border-white/10">
                      <div className="text-sm font-semibold mb-3 text-white">ALS Score™ Distribution</div>
                      <div className="space-y-3">
                        {[
                          { label: "Hot (80-100)", count: "127", pct: 85, color: "bg-gradient-to-r from-orange-500 to-red-500" },
                          { label: "Warm (50-79)", count: "892", pct: 60, color: "bg-gradient-to-r from-yellow-500 to-orange-500" },
                          { label: "Nurture (0-49)", count: "1,828", pct: 40, color: "bg-gray-500" },
                        ].map((tier, i) => (
                          <div key={i}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-gray-400">{tier.label}</span>
                              <span className="text-gray-300">{tier.count}</span>
                            </div>
                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                              <div className={`h-full ${tier.color} rounded-full`} style={{ width: `${tier.pct}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF METRICS */}
      <section className="py-16 border-y border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
            {[
              { value: 35, suffix: "%+", label: "Open rate", sub: "Industry avg: 15-20%" },
              { value: 12, suffix: "%", label: "Reply rate", sub: "3x typical cold email" },
              { value: 14, prefix: "<", suffix: " days", label: "To first meeting", sub: "From campaign launch" },
              { value: 5, suffix: " channels", label: "Unified", sub: "One dashboard" },
            ].map((stat, i) => (
              <ScrollReveal key={i} delay={i * 100}>
                <div className="flex flex-col items-center text-center">
                  <div className="text-4xl md:text-5xl font-bold gradient-text">
                    <AnimatedCounter target={stat.value} suffix={stat.suffix} prefix={stat.prefix} />
                  </div>
                  <div className="text-sm font-medium text-gray-900 mt-2">{stat.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{stat.sub}</div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20 md:py-28 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          
          <ScrollReveal>
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
                This isn't another AI sales tool.
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                It's your agency's growth operating system.
              </p>
            </div>
          </ScrollReveal>

          {/* Comparison Grid */}
          <ScrollReveal delay={100}>
            <div className="max-w-4xl mx-auto mb-20">
              <div className="grid md:grid-cols-2 gap-8 p-8 rounded-2xl bg-white border border-gray-200 shadow-lg">
                <div>
                  <h3 className="font-bold text-gray-400 uppercase text-sm tracking-wider mb-4">Generic AI SDRs</h3>
                  <ul className="space-y-3">
                    {["Spray-and-pray to any B2B", "US-centric data and timing", "Email-only or email-first", '"Set and forget" black box', "$5,000-10,000/month pricing"].map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-gray-500">
                        <span className="text-red-400 mt-0.5">✗</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="font-bold gradient-text uppercase text-sm tracking-wider mb-4">Agency OS</h3>
                  <ul className="space-y-3">
                    {["Trained on agency-client relationships", "Australian market, AEST, local compliance", "True 5-channel: Email, SMS, LinkedIn, Voice, Mail", "Conversion Intelligence shows WHY it works", "Founding tier: $1,250-3,750/month"].map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-gray-900">
                        <span className="text-green-500 mt-0.5">✓</span>
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
              <div className="bg-white rounded-2xl p-8 border border-gray-200 card-hover h-full">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-6 shadow-lg">
                  <Globe className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Australian-First</h3>
                <p className="text-gray-600 leading-relaxed">Built specifically for Australian agencies. Understands ACMA/DNCR compliance, Aussie business culture, and AEST timing.</p>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={100}>
              <div className="bg-white rounded-2xl p-8 border border-gray-200 card-hover h-full">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-6 shadow-lg">
                  <Brain className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-4">Conversion Intelligence</h3>
                <p className="text-gray-600 leading-relaxed">ML learns from every interaction. See exactly what subject lines, messages, and timing work for YOUR ideal clients.</p>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={200}>
              <div className="bg-white rounded-2xl p-8 border border-gray-200 card-hover h-full">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center mb-6 shadow-lg">
                  <Target className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-4">ALS Score™</h3>
                <p className="text-gray-600 leading-relaxed">Proprietary scoring ranks leads by budget, decision timeline, and agency fit. Focus only on deals worth your time.</p>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="py-20 md:py-28 bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-6xl mx-auto px-6">
          <ScrollReveal>
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">How it works</h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">From setup to your first booked meeting in less than 2 weeks</p>
            </div>
          </ScrollReveal>

          <div className="grid md:grid-cols-5 gap-6">
            {/* Discover */}
            <ScrollReveal delay={0}>
              <div className="text-center group">
                <div className="relative inline-block mb-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg mx-auto group-hover:scale-110 transition-transform">
                    <Search className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-600 shadow">
                    01
                  </div>
                </div>
                <h3 className="font-bold text-lg mb-2">Discover</h3>
                <p className="text-sm text-gray-600">ICP extracted from your website in 5 minutes.</p>
              </div>
            </ScrollReveal>
            {/* Find */}
            <ScrollReveal delay={100}>
              <div className="text-center group">
                <div className="relative inline-block mb-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg mx-auto group-hover:scale-110 transition-transform">
                    <Eye className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-600 shadow">
                    02
                  </div>
                </div>
                <h3 className="font-bold text-lg mb-2">Find</h3>
                <p className="text-sm text-gray-600">AI scouts Australian businesses showing buying signals.</p>
              </div>
            </ScrollReveal>
            {/* Score */}
            <ScrollReveal delay={200}>
              <div className="text-center group">
                <div className="relative inline-block mb-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg mx-auto group-hover:scale-110 transition-transform">
                    <BarChart3 className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-600 shadow">
                    03
                  </div>
                </div>
                <h3 className="font-bold text-lg mb-2">Score</h3>
                <p className="text-sm text-gray-600">ALS Score™ ranks by budget, timeline, and fit.</p>
              </div>
            </ScrollReveal>
            {/* Reach */}
            <ScrollReveal delay={300}>
              <div className="text-center group">
                <div className="relative inline-block mb-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg mx-auto group-hover:scale-110 transition-transform">
                    <Rocket className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-600 shadow">
                    04
                  </div>
                </div>
                <h3 className="font-bold text-lg mb-2">Reach</h3>
                <p className="text-sm text-gray-600">5-channel outreach: Email, SMS, LinkedIn, Voice, Mail.</p>
              </div>
            </ScrollReveal>
            {/* Convert */}
            <ScrollReveal delay={400}>
              <div className="text-center group">
                <div className="relative inline-block mb-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg mx-auto group-hover:scale-110 transition-transform">
                    <Calendar className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-600 shadow">
                    05
                  </div>
                </div>
                <h3 className="font-bold text-lg mb-2">Convert</h3>
                <p className="text-sm text-gray-600">Meetings booked on your calendar. Automatically.</p>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* SDR COMPARISON */}
      <section id="comparison" className="py-20 md:py-28 bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-6">
          <ScrollReveal>
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 border border-white/20 text-sm mb-6">
                <DollarSign className="w-4 h-4 text-green-400" />
                <span className="text-white/80">The math that matters</span>
              </div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Agency OS vs. Hiring a Junior SDR</h2>
              <p className="text-lg text-white/60 max-w-2xl mx-auto">The numbers don't lie. Here's what the real comparison looks like.</p>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={100}>
            <div className="overflow-x-auto mb-16">
              <table className="w-full max-w-4xl mx-auto">
                <thead>
                  <tr className="border-b border-white/20">
                    <th className="text-left py-4 px-4 text-white/60 font-medium">Factor</th>
                    <th className="text-center py-4 px-4 text-white/60 font-medium">Junior SDR</th>
                    <th className="text-center py-4 px-4 font-medium"><span className="gradient-text">Agency OS Velocity</span></th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    { factor: "Monthly cost", sdr: "$6,500-8,750", aos: "$2,500 (founding)", winner: "aos" },
                    { factor: "Meetings/month", sdr: "8-12 (after ramp)", aos: "15-16", winner: "aos" },
                    { factor: "Cost per meeting", sdr: "$600-900", aos: "$156", winner: "aos" },
                    { factor: "Time to first meeting", sdr: "3-4 months", aos: "Week 2-4", winner: "aos" },
                    { factor: "Your time required", sdr: "5-10 hrs/week", aos: "<1 hr/week", winner: "aos" },
                    { factor: "Sick days / Leave", sdr: "Yes", aos: "No", winner: "aos" },
                    { factor: "Turnover risk", sdr: "High (1.8yr tenure)", aos: "None", winner: "aos" },
                    { factor: "Channels covered", sdr: "2-3 (manual)", aos: "5 (automated)", winner: "aos" },
                    { factor: "Works 24/7", sdr: "No", aos: "Yes", winner: "aos" },
                  ].map((row, i) => (
                    <tr key={i} className="border-b border-white/10">
                      <td className="py-4 px-4 text-white/80">{row.factor}</td>
                      <td className="py-4 px-4 text-center text-white/50">{row.sdr}</td>
                      <td className="py-4 px-4 text-center">
                        <span className={row.winner === "aos" ? "text-green-400 font-semibold" : "text-white/80"}>{row.aos}</span>
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
              <div className="p-8 rounded-2xl bg-white/5 border border-white/10">
                <h3 className="text-lg font-semibold text-white/60 mb-4">Year 1: Junior SDR</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-white/60">Total cost</span><span className="text-white font-semibold">$84,000</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Total meetings</span><span className="text-white font-semibold">~85</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Cost per meeting</span><span className="text-red-400 font-semibold">$988</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Your time invested</span><span className="text-white font-semibold">250-500 hrs</span></div>
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={300}>
              <div className="p-8 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30">
                <h3 className="text-lg font-semibold text-blue-300 mb-4">Year 1: Agency OS Velocity (founding)</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-white/60">Total cost</span><span className="text-white font-semibold">$30,000</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Total meetings</span><span className="text-green-400 font-semibold">~187</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Cost per meeting</span><span className="text-green-400 font-semibold">$160</span></div>
                  <div className="flex justify-between"><span className="text-white/60">Your time invested</span><span className="text-green-400 font-semibold">&lt;50 hrs</span></div>
                </div>
              </div>
            </ScrollReveal>
          </div>

          <ScrollReveal delay={400}>
            <div className="mt-16 text-center">
              <div className="inline-block p-8 rounded-2xl bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30">
                <p className="text-3xl md:text-4xl font-bold text-white mb-3">
                  Save <span className="text-green-400">$54,000</span> + Get <span className="text-green-400">2.2x</span> more meetings
                </p>
                <p className="text-white/60">84% lower cost per meeting • 200-450 hours of your time saved • Ramp in weeks</p>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="py-20 md:py-28 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <ScrollReveal>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 px-4 py-2 text-sm mb-6">
                <svg className="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                </svg>
                <span className="font-semibold text-amber-800">
                  {soldOut ? "Founding spots sold out!" : `Founding Member Pricing — ${spotsRemaining ?? "..."} of 20 spots left`}
                </span>
              </div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Lock in 50% off. Forever.</h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">Founding members keep their rate for life. No contracts. Cancel anytime.</p>
            </div>
          </ScrollReveal>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { name: "Ignition", originalPrice: "$2,500", foundingPrice: "$1,250", savings: "Save $15K/year", expectedMeetings: "8-9 meetings/month expected", desc: "Perfect for getting started", limits: ["1,250 leads/month", "5 campaigns", "1 LinkedIn seat"], cta: "Get Started", popular: false },
              { name: "Velocity", originalPrice: "$5,000", foundingPrice: "$2,500", savings: "Save $30K/year", expectedMeetings: "15-16 meetings/month expected", desc: "Most popular for growing agencies", limits: ["2,250 leads/month", "10 campaigns", "3 LinkedIn seats"], cta: "Claim Your Spot", popular: true },
              { name: "Dominance", originalPrice: "$7,500", foundingPrice: "$3,750", savings: "Save $45K/year", expectedMeetings: "31-32 meetings/month expected", desc: "Maximum pipeline capacity", limits: ["4,500 leads/month", "20 campaigns", "5 LinkedIn seats"], cta: "Get Started", popular: false },
            ].map((tier, i) => (
              <ScrollReveal key={i} delay={i * 100}>
                <div className={`rounded-2xl p-8 card-hover flex flex-col h-full relative ${tier.popular ? "bg-white border-2 border-blue-500 shadow-xl shadow-blue-500/10 scale-105" : "bg-white border border-gray-200"}`}>
                  {tier.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-1.5 rounded-full text-sm font-semibold shadow-lg flex items-center gap-1">
                      <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>
                      Most Popular
                    </div>
                  )}
                  <div className="mb-6">
                    <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                    <p className="text-gray-500 text-sm mb-4">{tier.desc}</p>
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-5xl font-bold tracking-tight">{tier.foundingPrice}</span>
                      <span className="text-gray-500 text-lg">/mo</span>
                    </div>
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-gray-400 line-through text-sm">Was {tier.originalPrice}/mo</span>
                      <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded">{tier.savings}</span>
                    </div>
                    {/* Expected Meetings Highlight */}
                    <div className={`p-3 rounded-xl ${tier.popular ? "bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-200" : "bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200"}`}>
                      <div className="flex items-center gap-2">
                        <Calendar className={`w-5 h-5 ${tier.popular ? "text-blue-600" : "text-green-600"}`} />
                        <span className={`text-sm font-bold ${tier.popular ? "text-blue-700" : "text-green-700"}`}>{tier.expectedMeetings}</span>
                      </div>
                    </div>
                  </div>
                  <ul className="space-y-3 mb-8 flex-grow">
                    {tier.limits.map((limit, j) => (
                      <li key={j} className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                        </svg>
                        <span className="text-sm text-gray-700 font-medium">{limit}</span>
                      </li>
                    ))}
                  </ul>
                  <a href="#waitlist" className={`w-full py-3 px-6 rounded-xl font-semibold text-center transition-all ${tier.popular ? "btn-gradient text-white" : "border-2 border-gray-200 text-gray-700 hover:border-blue-500 hover:text-blue-600"}`}>
                    {tier.cta}
                  </a>
                </div>
              </ScrollReveal>
            ))}
          </div>

          {/* All Plans Include */}
          <ScrollReveal delay={200}>
            <div className="max-w-4xl mx-auto mt-16">
              <h3 className="text-xl font-bold text-center mb-8 text-gray-900">All plans include</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { icon: Mail, label: "Full 5-channel outreach", sub: "Email, LinkedIn, Voice AI, SMS, Direct Mail" },
                  { icon: Brain, label: "Advanced Conversion Intelligence", sub: "ML learns what works for you" },
                  { icon: Target, label: "ALS lead scoring", sub: "Prioritize your best prospects" },
                  { icon: BarChart3, label: "All reporting & analytics", sub: "Real-time dashboard" },
                  { icon: Globe, label: "API access", sub: "Integrate with your stack" },
                  { icon: Shield, label: "Priority support", sub: "We're here when you need us" },
                ].map((feature, i) => (
                  <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <feature.icon className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{feature.label}</p>
                      <p className="text-xs text-gray-500">{feature.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={300}>
            <div className="max-w-3xl mx-auto mt-16">
              <div className="rounded-2xl p-8 bg-gradient-to-br from-blue-50 to-purple-50 border border-blue-100 text-center">
                <h3 className="text-xl font-bold mb-4">The ROI Math</h3>
                <p className="text-3xl font-bold text-blue-600 mb-3">Close ONE new client → Pay for an entire year</p>
                <p className="text-gray-600">At $2,500/month with a typical agency retainer of $5,000/month, one new client covers more than 2 years of Agency OS.</p>
              </div>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={400}>
            <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 mt-12 text-sm text-gray-500">
              <span className="inline-flex items-center gap-1.5"><Shield className="w-4 h-4" /> Australian Privacy Act Compliant</span>
              <span className="inline-flex items-center gap-1.5"><Smartphone className="w-4 h-4" /> DNCR Integration Built-In</span>
              <span className="inline-flex items-center gap-1.5"><CreditCard className="w-4 h-4" /> Cancel Anytime—No Lock-In</span>
              <span className="inline-flex items-center gap-1.5"><Globe className="w-4 h-4" /> Built for Australian Agencies</span>
            </div>
            {/* Ramp Clause */}
            <p className="text-center text-xs text-gray-400 mt-6">
              *Full guarantee kicks in after 30-day onboarding period
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* FINAL CTA */}
      <section id="waitlist" className="py-20 md:py-28 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <ScrollReveal>
              <div>
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
                  20 agencies will build the future of agency growth.
                  <span className="gradient-text"> Will you be one of them?</span>
                </h2>
                <p className="text-lg text-gray-600 mb-8">Most agencies will wait. Wait until it's proven. Wait until everyone has it. Wait until competitive advantage disappears.</p>
                <p className="text-lg font-medium text-gray-900 mb-8">The agencies that win don't wait. They move first.</p>
                <div className="space-y-4">
                  {["Lock in 50% off for life", "Direct line to the product team", "White-glove onboarding"].map((item, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/>
                        </svg>
                      </div>
                      <span className="text-gray-700">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={200}>
              <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-xl">
                <div className="flex items-center justify-center gap-2 mb-6">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                  </span>
                  <span className="text-sm font-medium text-gray-600">
                    {soldOut ? "Founding spots sold out!" : `${spotsRemaining ?? "..."} founding spots remaining`}
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-center mb-2">Claim your founding spot</h3>
                <p className="text-gray-500 text-sm text-center mb-6">Booking results guaranteed or your money back. Cancel anytime.</p>
                <WaitlistForm source="landing-page-bottom" variant="full" />
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-blue-500" />
                      <span>Australian Privacy Compliant</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-blue-500" />
                      <span>DNCR Integrated</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Unlock className="w-4 h-4 text-blue-500" />
                      <span>Cancel Anytime</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-blue-500" />
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
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <span className="text-white font-bold text-sm">A</span>
                </div>
                <span className="font-bold text-xl text-white">Agency OS</span>
              </div>
              <p className="text-sm leading-relaxed mb-4 max-w-sm">The client acquisition operating system for Australian marketing agencies.</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
                <li><a href="#comparison" className="hover:text-white transition-colors">ROI Calculator</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm">© 2025 Agency OS. All rights reserved.</p>
            <p className="text-sm inline-flex items-center gap-1.5"><Globe className="w-4 h-4" /> Proudly built in Australia, for Australian agencies.</p>
          </div>
        </div>
      </footer>

      {/* Floating Founding Spots Counter */}
      <FloatingFoundingSpots />
    </main>
  );
}
