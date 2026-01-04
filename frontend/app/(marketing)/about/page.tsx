/**
 * FILE: app/(marketing)/about/page.tsx
 * PURPOSE: About page - team, mission, story
 */

"use client";

import Link from "next/link";
import { ScrollReveal } from "@/hooks/use-scroll-animation";
import { WaitlistForm } from "@/components/marketing/waitlist-form";

export default function AboutPage() {
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
            <Link href="/pricing" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">Pricing</Link>
            <Link href="/about" className="text-[#1d1d1f] font-medium">About</Link>
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
            <p className="text-sm font-medium text-[#0066CC] uppercase tracking-wider mb-4">About Agency OS</p>
            <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
              Built by agency people,<br />for agency people
            </h1>
            <p className="text-xl text-[#1d1d1f]/60 max-w-2xl mx-auto">
              We've lived the chaos of agency client acquisition. We built Agency OS to fix it.
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* The Problem */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-4xl mx-auto">
          <ScrollReveal animation="fade-up">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-8">
              The problem we're solving
            </h2>
            <div className="prose prose-lg max-w-none text-[#1d1d1f]/70">
              <p>
                Every marketing agency knows the drill: you're brilliant at getting results for your clients, but your own client acquisition is a mess of spreadsheets, half-finished sequences, and tools that don't talk to each other.
              </p>
              <p>
                You've got Apollo for data. Instantly for email. LinkedIn Sales Nav for social. Twilio for SMS. Maybe a dialer for calls. A CRM that's always half-updated. And a mountain of manual work to keep it all running.
              </p>
              <p>
                The irony isn't lost on anyone: agencies that help other businesses grow often struggle to grow themselves. Not because they don't know marketing—but because the tools weren't built for how agencies actually work.
              </p>
              <p className="font-medium text-[#1d1d1f]">
                Agency OS changes that.
              </p>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* The Vision */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-4xl mx-auto">
          <ScrollReveal animation="fade-up">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-8">
              Our vision
            </h2>
            <div className="prose prose-lg max-w-none text-[#1d1d1f]/70">
              <p>
                We're building the "Bloomberg Terminal for Client Acquisition" — a single platform where agencies can see, manage, and automate their entire outbound pipeline.
              </p>
              <p>
                Imagine waking up to meetings already booked in your calendar. Leads scored and prioritized automatically. Personalized outreach running across five channels without you touching a thing. Conversion Intelligence that gets smarter every day, learning what works for YOUR agency.
              </p>
              <p>
                That's Agency OS. One platform. Every channel. Full automation—or full control when you want it.
              </p>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* Why Australia First */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <ScrollReveal animation="fade-right">
              <div>
                <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-6">
                  Why Australia first?
                </h2>
                <div className="prose prose-lg max-w-none text-[#1d1d1f]/70">
                  <p>
                    We're launching in Australia because we know this market. We understand DNCR compliance, AEST working hours, and the unique dynamics of the AU agency landscape.
                  </p>
                  <p>
                    Australia has over 8,000 digital agencies in a $3.7B market. Most are using US-centric tools that don't account for local regulations, time zones, or market nuances.
                  </p>
                  <p>
                    We're building Agency OS right—starting local, with deep compliance and localization—before expanding globally.
                  </p>
                </div>
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100}>
              <div className="bg-[#f5f5f7] rounded-2xl p-8 border border-black/5">
                <p className="text-sm text-[#1d1d1f]/40 uppercase tracking-wider mb-6">🇦🇺 Built for Australia</p>
                <ul className="space-y-4">
                  {[
                    { label: "DNCR Compliance", desc: "Automatic Do Not Call Register checking" },
                    { label: "AEST Optimized", desc: "Outreach timed for Australian business hours" },
                    { label: "Local Data Sources", desc: "Australian business databases prioritized" },
                    { label: "AUD Pricing", desc: "No currency conversion headaches" },
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <div>
                        <p className="font-medium text-sm">{item.label}</p>
                        <p className="text-sm text-[#1d1d1f]/50">{item.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="px-6 py-24 bg-[#1d1d1f] text-white">
        <div className="max-w-5xl mx-auto">
          <ScrollReveal animation="fade-up">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-center mb-12">
              What we believe
            </h2>
          </ScrollReveal>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: "Results over features",
                desc: "We measure success by meetings booked and deals closed—not feature checklists. Every feature exists to drive revenue for agencies.",
              },
              {
                title: "Automation with control",
                desc: "Full autopilot when you want it, full control when you need it. Co-Pilot mode lets you approve every message. Autopilot handles the rest.",
              },
              {
                title: "Transparent pricing",
                desc: "No hidden fees, no per-seat surprises, no gotchas. You know exactly what you pay and what you get. Simple as that.",
              },
            ].map((value, i) => (
              <ScrollReveal key={i} animation="fade-up" delay={i * 100}>
                <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-xl font-semibold mb-3">{value.title}</h3>
                  <p className="text-white/60">{value.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-3xl mx-auto text-center">
          <ScrollReveal animation="fade-up">
            <h2 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
              Be part of the founding cohort
            </h2>
            <p className="text-xl text-[#1d1d1f]/60 mb-10">
              20 spots. 50% off for life. Help shape the future of Agency OS.
            </p>
            <WaitlistForm source="about" />
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
