/**
 * FILE: app/(marketing)/pricing/page.tsx
 * PURPOSE: Detailed Pricing page with FAQ
 */

"use client";

import Link from "next/link";
import { ScrollReveal } from "@/hooks/use-scroll-animation";
import { WaitlistForm } from "@/components/marketing/waitlist-form";
import { useState } from "react";

export default function PricingPage() {
  const [billing, setBilling] = useState<"monthly" | "annual">("monthly");

  return (
    <main className="min-h-screen bg-[#fafafa] text-[#1d1d1f] antialiased">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-white/70 border-b border-black/5">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0066CC] to-[#5856D6] flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <span className="font-semibold text-lg tracking-tight">Agency OS</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm">
            <Link href="/#features" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">Features</Link>
            <Link href="/how-it-works" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">How it Works</Link>
            <Link href="/pricing" className="text-[#1d1d1f] font-medium">Pricing</Link>
            <Link href="/about" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">About</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors hidden sm:block">Sign in</Link>
            <Link href="/#waitlist" className="text-sm font-medium px-4 py-2 rounded-full bg-[#1d1d1f] text-white hover:bg-[#1d1d1f]/90 transition-all hover:scale-105">Join Waitlist</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <ScrollReveal animation="fade-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-50 border border-red-100 mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span className="text-sm text-red-600 font-medium">Founding tier: 50% off for life — 20 spots only</span>
            </div>
            <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
              Simple pricing.<br />No hidden fees.
            </h1>
            <p className="text-xl text-[#1d1d1f]/60 max-w-2xl mx-auto">
              All prices in AUD. Cancel anytime. At $2,500/month, you need just 1 new client to break even.
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="px-6 pb-24">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                name: "Ignition",
                originalPrice: 2500,
                expectedMeetings: "8-9 meetings/month expected",
                desc: "Perfect for getting started",
                limits: ["1,250 leads/month", "5 campaigns", "1 LinkedIn seat"],
                popular: false,
              },
              {
                name: "Velocity",
                originalPrice: 5000,
                expectedMeetings: "15-16 meetings/month expected",
                desc: "Most popular for growing agencies",
                limits: ["2,250 leads/month", "10 campaigns", "3 LinkedIn seats"],
                popular: true,
              },
              {
                name: "Dominance",
                originalPrice: 7500,
                expectedMeetings: "31-32 meetings/month expected",
                desc: "Maximum pipeline capacity",
                limits: ["4,500 leads/month", "20 campaigns", "5 LinkedIn seats"],
                popular: false,
              },
            ].map((tier, i) => (
              <ScrollReveal key={i} animation="fade-up" delay={i * 100}>
                <div className={`relative h-full flex flex-col p-8 rounded-2xl border ${tier.popular ? 'bg-[#1d1d1f] text-white border-[#1d1d1f] shadow-2xl shadow-black/20 md:scale-105' : 'bg-white border-black/10'}`}>
                  {tier.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="px-4 py-1 rounded-full bg-gradient-to-r from-[#0066CC] to-[#5856D6] text-white text-sm font-medium">Most Popular</span>
                    </div>
                  )}

                  <h3 className="text-2xl font-semibold mb-2">{tier.name}</h3>
                  <p className={`text-sm mb-6 ${tier.popular ? 'text-white/60' : 'text-[#1d1d1f]/60'}`}>{tier.desc}</p>

                  <div className="mb-6">
                    <span className={`text-sm line-through ${tier.popular ? 'text-white/40' : 'text-[#1d1d1f]/40'}`}>
                      ${tier.originalPrice.toLocaleString()}
                    </span>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold">${(tier.originalPrice / 2).toLocaleString()}</span>
                      <span className={tier.popular ? 'text-white/60' : 'text-[#1d1d1f]/60'}>/month</span>
                    </div>
                    <span className="text-sm text-green-500 font-medium">Founding price (50% off for life)</span>
                    {/* Expected Meetings Highlight */}
                    <div className={`mt-4 p-3 rounded-xl ${tier.popular ? 'bg-white/10 border border-white/20' : 'bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200'}`}>
                      <div className="flex items-center gap-2">
                        <svg className={`w-5 h-5 ${tier.popular ? 'text-green-400' : 'text-green-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth={2}/>
                          <line x1="16" y1="2" x2="16" y2="6" strokeWidth={2}/>
                          <line x1="8" y1="2" x2="8" y2="6" strokeWidth={2}/>
                          <line x1="3" y1="10" x2="21" y2="10" strokeWidth={2}/>
                        </svg>
                        <span className={`text-sm font-bold ${tier.popular ? 'text-green-400' : 'text-green-700'}`}>{tier.expectedMeetings}</span>
                      </div>
                    </div>
                  </div>

                  <ul className="space-y-3 mb-8 flex-1">
                    {tier.limits.map((limit, j) => (
                      <li key={j} className="flex items-center gap-3">
                        <svg className={`w-5 h-5 flex-shrink-0 ${tier.popular ? 'text-green-400' : 'text-green-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span className={`text-sm font-medium ${tier.popular ? 'text-white/80' : 'text-[#1d1d1f]/70'}`}>
                          {limit}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    href="/#waitlist"
                    className={`block text-center py-3 px-6 rounded-full font-medium transition-all hover:scale-105 ${tier.popular ? 'bg-white text-[#1d1d1f] hover:bg-white/90' : 'bg-[#1d1d1f] text-white hover:bg-[#1d1d1f]/90'}`}
                  >
                    Claim Founding Spot
                  </Link>
                </div>
              </ScrollReveal>
            ))}
          </div>

          {/* All Plans Include */}
          <div className="max-w-4xl mx-auto mt-16">
            <h3 className="text-xl font-semibold text-center mb-8">All plans include</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                "Full 5-channel outreach",
                "Advanced Conversion Intelligence",
                "ALS lead scoring",
                "All reporting & analytics",
                "API access",
                "Priority support",
              ].map((feature, i) => (
                <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-[#f5f5f7] border border-black/5">
                  <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm text-[#1d1d1f]/70">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Ramp Clause */}
          <p className="text-center text-xs text-[#1d1d1f]/40 mt-8">
            *Full guarantee kicks in after 30-day onboarding period
          </p>
        </div>
      </section>


      {/* What's a Credit */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-4xl mx-auto">
          <ScrollReveal animation="fade-up">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-center mb-12">
              What's a lead credit?
            </h2>
          </ScrollReveal>
          <ScrollReveal animation="fade-up" delay={100}>
            <div className="bg-[#f5f5f7] rounded-2xl p-8 border border-black/5">
              <p className="text-lg text-[#1d1d1f]/70 mb-6">
                One lead credit = one fully enriched prospect with verified contact data, ready for outreach.
              </p>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <p className="font-medium mb-3">What you get per credit:</p>
                  <ul className="space-y-2">
                    {[
                      "Verified work email address",
                      "Direct phone number (where available)",
                      "LinkedIn profile URL",
                      "Company firmographic data",
                      "ALS score calculation",
                    ].map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#1d1d1f]/60">
                        <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium mb-3">What doesn't use credits:</p>
                  <ul className="space-y-2">
                    {[
                      "Sending emails or messages",
                      "SMS or voice calls",
                      "Viewing your dashboard",
                      "Analytics and reporting",
                      "AI content generation",
                    ].map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#1d1d1f]/60">
                        <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-3xl mx-auto">
          <ScrollReveal animation="fade-up">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-center mb-12">
              Frequently asked questions
            </h2>
          </ScrollReveal>
          <div className="space-y-4">
            {[
              {
                q: "What happens after the 20 founding spots are filled?",
                a: "Founding pricing is locked for life for those 20 agencies. After that, we move to standard pricing (the crossed-out prices you see). Founding members keep their 50% discount forever, even as we add new features.",
              },
              {
                q: "Can I change plans later?",
                a: "Yes, you can upgrade or downgrade at any time. If you're a founding member and upgrade, you keep your 50% discount on the new plan. Downgrades take effect at your next billing cycle.",
              },
              {
                q: "Is there a setup fee?",
                a: "No setup fees. Dominance tier includes white-glove onboarding at no extra cost. All other tiers include self-serve onboarding with documentation and support.",
              },
              {
                q: "What if I don't use all my credits?",
                a: "Credits roll over month to month (up to 2x your monthly allocation). So if you have 5,000 credits/month and only use 3,000, you'll have 7,000 available next month (capped at 10,000).",
              },
              {
                q: "Do you offer annual billing?",
                a: "Not currently during the founding phase. We'll introduce annual billing (with additional discount) once we're past the founding tier.",
              },
              {
                q: "What's the difference between Co-Pilot and Autopilot mode?",
                a: "Co-Pilot mode requires your approval before any outreach is sent—you see every email and message before it goes out. Autopilot mode handles everything automatically based on your approved sequences and rules. You can switch between modes anytime.",
              },
              {
                q: "Is there a contract or commitment?",
                a: "No long-term contracts. Month-to-month billing. Cancel anytime from your dashboard. If you cancel, you keep access until the end of your billing period.",
              },
              {
                q: "Can I get a refund?",
                a: "We guarantee booking results or your money back. After the 30-day onboarding period, if we don't deliver the expected meetings for your tier, you get a full refund.",
              },
            ].map((faq, i) => (
              <ScrollReveal key={i} animation="fade-up" delay={i * 50}>
                <div className="p-6 rounded-xl bg-white border border-black/5">
                  <h3 className="font-semibold mb-2">{faq.q}</h3>
                  <p className="text-[#1d1d1f]/60">{faq.a}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-3xl mx-auto text-center">
          <ScrollReveal animation="fade-up">
            <h2 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
              Ready to claim your spot?
            </h2>
            <p className="text-xl text-[#1d1d1f]/60 mb-10">
              Only 20 founding spots at 50% off for life.
            </p>
            <WaitlistForm source="pricing" />
          </ScrollReveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 bg-[#1d1d1f] text-white">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0066CC] to-[#5856D6] flex items-center justify-center">
                <span className="text-white font-bold text-sm">A</span>
              </div>
              <span className="font-semibold text-lg">Agency OS</span>
            </Link>
            <div className="flex items-center gap-8 text-sm text-white/60">
              <Link href="/how-it-works" className="hover:text-white transition-colors">How it Works</Link>
              <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              <Link href="/about" className="hover:text-white transition-colors">About</Link>
            </div>
            <p className="text-sm text-white/40">© 2025 Agency OS. Made in Australia 🇦🇺</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
