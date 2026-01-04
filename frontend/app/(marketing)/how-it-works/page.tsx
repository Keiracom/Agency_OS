/**
 * FILE: app/(marketing)/how-it-works/page.tsx
 * PURPOSE: Detailed How It Works page
 */

"use client";

import Link from "next/link";
import { ScrollReveal } from "@/hooks/use-scroll-animation";
import { WaitlistForm } from "@/components/marketing/waitlist-form";

export default function HowItWorksPage() {
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
            <Link href="/how-it-works" className="text-[#1d1d1f] font-medium">How it Works</Link>
            <Link href="/pricing" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">Pricing</Link>
            <Link href="/about" className="text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors">About</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-[#1d1d1f]/60 hover:text-[#1d1d1f] transition-colors hidden sm:block">
              Sign in
            </Link>
            <Link href="/#waitlist" className="text-sm font-medium px-4 py-2 rounded-full bg-[#1d1d1f] text-white hover:bg-[#1d1d1f]/90 transition-all hover:scale-105">
              Join Waitlist
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <ScrollReveal animation="fade-up">
            <p className="text-sm font-medium text-[#0066CC] uppercase tracking-wider mb-4">How It Works</p>
            <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
              From zero to booked meetings<br />in 5 simple steps
            </h1>
            <p className="text-xl text-[#1d1d1f]/60 max-w-2xl mx-auto">
              Agency OS handles the heavy lifting. You handle the closing.
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* Step 1: ICP Discovery */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <ScrollReveal animation="fade-right">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0066CC]/10 text-[#0066CC] text-sm font-medium mb-6">
                  <span className="w-6 h-6 rounded-full bg-[#0066CC] text-white flex items-center justify-center text-xs font-bold">1</span>
                  <span>ICP Discovery</span>
                </div>
                <h2 className="text-4xl font-semibold tracking-tight mb-4">
                  Enter your website.<br />We extract your ICP.
                </h2>
                <p className="text-lg text-[#1d1d1f]/60 mb-6 leading-relaxed">
                  Our AI analyzes your website, case studies, testimonials, and service pages to understand exactly who your ideal clients are. In minutes, not hours.
                </p>
                <ul className="space-y-3">
                  {[
                    "Automatic industry detection from your portfolio",
                    "Company size patterns from your case studies",
                    "Geographic focus from your client base",
                    "Decision-maker titles you typically work with",
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-[#1d1d1f]/70">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100}>
              <div className="bg-[#f5f5f7] rounded-2xl p-8 border border-black/5">
                <div className="bg-white rounded-xl p-6 shadow-sm border border-black/5">
                  <p className="text-sm text-[#1d1d1f]/40 uppercase tracking-wider mb-4">Extracted ICP</p>
                  <div className="space-y-4">
                    <div>
                      <p className="text-xs text-[#1d1d1f]/40 mb-1">Industries</p>
                      <div className="flex flex-wrap gap-2">
                        {["Healthcare", "Legal", "Professional Services", "Real Estate"].map((i) => (
                          <span key={i} className="px-3 py-1 bg-[#0066CC]/10 text-[#0066CC] rounded-full text-sm">{i}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-[#1d1d1f]/40 mb-1">Company Size</p>
                      <p className="font-medium">10-100 employees</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#1d1d1f]/40 mb-1">Decision Makers</p>
                      <div className="flex flex-wrap gap-2">
                        {["Marketing Director", "CMO", "Business Owner", "CEO"].map((t) => (
                          <span key={t} className="px-3 py-1 bg-[#f5f5f7] rounded-full text-sm">{t}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-[#1d1d1f]/40 mb-1">Location</p>
                      <p className="font-medium">Australia (Primary), New Zealand</p>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Step 2: Lead Enrichment */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <ScrollReveal animation="fade-right" className="order-2 md:order-1">
              <div className="bg-white rounded-2xl p-8 border border-black/5 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium">Scout Engine Active</p>
                    <p className="text-sm text-[#1d1d1f]/50">Finding leads matching your ICP</p>
                  </div>
                </div>
                <div className="space-y-3">
                  {[
                    { name: "Sarah Chen", company: "Bloom Digital", title: "Marketing Director", confidence: "98%" },
                    { name: "Marcus Webb", company: "Pixel Perfect", title: "CEO", confidence: "94%" },
                    { name: "Emma Thompson", company: "Growth Labs", title: "CMO", confidence: "91%" },
                  ].map((lead, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[#f5f5f7]">
                      <div>
                        <p className="font-medium text-sm">{lead.name}</p>
                        <p className="text-xs text-[#1d1d1f]/50">{lead.title} at {lead.company}</p>
                      </div>
                      <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
                        {lead.confidence} match
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-center text-sm text-[#1d1d1f]/40 mt-4">+247 more leads found</p>
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100} className="order-1 md:order-2">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0066CC]/10 text-[#0066CC] text-sm font-medium mb-6">
                  <span className="w-6 h-6 rounded-full bg-[#0066CC] text-white flex items-center justify-center text-xs font-bold">2</span>
                  <span>Lead Enrichment</span>
                </div>
                <h2 className="text-4xl font-semibold tracking-tight mb-4">
                  AI scouts leads<br />matching your ICP
                </h2>
                <p className="text-lg text-[#1d1d1f]/60 mb-6 leading-relaxed">
                  Our Scout Engine uses a waterfall enrichment process—Apollo, Apify, Clay—to find and verify prospects that match your ideal client profile.
                </p>
                <ul className="space-y-3">
                  {[
                    "Verified email addresses (bounces excluded)",
                    "Direct phone numbers where available",
                    "LinkedIn profiles for social outreach",
                    "Company firmographics for personalization",
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-[#1d1d1f]/70">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>


      {/* Step 3: ALS Scoring */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <ScrollReveal animation="fade-right">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0066CC]/10 text-[#0066CC] text-sm font-medium mb-6">
                  <span className="w-6 h-6 rounded-full bg-[#0066CC] text-white flex items-center justify-center text-xs font-bold">3</span>
                  <span>ALS Scoring</span>
                </div>
                <h2 className="text-4xl font-semibold tracking-tight mb-4">
                  Every lead scored.<br />Hottest first.
                </h2>
                <p className="text-lg text-[#1d1d1f]/60 mb-6 leading-relaxed">
                  Our Agency Lead Score (ALS) evaluates every prospect across 5 dimensions to prioritize the leads most likely to convert.
                </p>
                <div className="space-y-4">
                  {[
                    { name: "Data Quality", points: "20 pts", desc: "Verified email, phone, LinkedIn" },
                    { name: "Authority", points: "25 pts", desc: "Decision-maker seniority" },
                    { name: "Company Fit", points: "25 pts", desc: "Industry, size, location match" },
                    { name: "Timing", points: "15 pts", desc: "New role, hiring, funded" },
                    { name: "Risk", points: "15 pts", desc: "Bounced, competitor, bad fit" },
                  ].map((dim, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[#f5f5f7]">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0066CC] to-[#5856D6] flex items-center justify-center text-white text-xs font-bold">
                          {dim.points.split(' ')[0]}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{dim.name}</p>
                          <p className="text-xs text-[#1d1d1f]/50">{dim.desc}</p>
                        </div>
                      </div>
                      <span className="text-sm text-[#1d1d1f]/40">{dim.points}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100}>
              <div className="bg-[#1d1d1f] rounded-2xl p-8 text-white">
                <p className="text-sm text-white/40 uppercase tracking-wider mb-6">Lead Tiers</p>
                <div className="space-y-4">
                  {[
                    { tier: "Hot", range: "85-100", color: "from-red-500 to-orange-500", channels: "All 5 channels" },
                    { tier: "Warm", range: "60-84", color: "from-orange-400 to-yellow-400", channels: "Email, LinkedIn, Voice" },
                    { tier: "Cool", range: "35-59", color: "from-blue-400 to-cyan-400", channels: "Email, LinkedIn" },
                    { tier: "Cold", range: "20-34", color: "from-gray-400 to-gray-500", channels: "Email only" },
                  ].map((t, i) => (
                    <div key={i} className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${t.color} flex items-center justify-center font-bold`}>
                        {t.range.split('-')[0]}+
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{t.tier} Lead</p>
                        <p className="text-sm text-white/50">{t.channels}</p>
                      </div>
                      <span className="text-sm text-white/40">{t.range}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Step 4: Multi-Channel Outreach */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <ScrollReveal animation="fade-right" className="order-2 md:order-1">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { icon: "✉️", name: "Email", desc: "Personalized sequences", status: "Active" },
                  { icon: "💼", name: "LinkedIn", desc: "Connection + InMails", status: "Active" },
                  { icon: "💬", name: "SMS", desc: "DNCR-compliant", status: "Active" },
                  { icon: "📞", name: "Voice AI", desc: "Conversational calls", status: "Active" },
                  { icon: "📬", name: "Direct Mail", desc: "Postcards + letters", status: "Active" },
                  { icon: "🧠", name: "AI Content", desc: "Per-prospect copy", status: "Learning" },
                ].map((ch, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white border border-black/5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-2xl">{ch.icon}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${ch.status === 'Active' ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'}`}>
                        {ch.status}
                      </span>
                    </div>
                    <p className="font-medium text-sm mb-1">{ch.name}</p>
                    <p className="text-xs text-[#1d1d1f]/50">{ch.desc}</p>
                  </div>
                ))}
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100} className="order-1 md:order-2">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0066CC]/10 text-[#0066CC] text-sm font-medium mb-6">
                  <span className="w-6 h-6 rounded-full bg-[#0066CC] text-white flex items-center justify-center text-xs font-bold">4</span>
                  <span>Multi-Channel Outreach</span>
                </div>
                <h2 className="text-4xl font-semibold tracking-tight mb-4">
                  5 channels working<br />in perfect harmony
                </h2>
                <p className="text-lg text-[#1d1d1f]/60 mb-6 leading-relaxed">
                  Each channel is coordinated to maximize touchpoints without overwhelming prospects. Hot leads get all channels. Cool leads get email-first.
                </p>
                <div className="p-4 rounded-xl bg-white border border-black/5">
                  <p className="text-sm font-medium mb-3">Example Hot Lead sequence:</p>
                  <div className="space-y-2 text-sm">
                    {[
                      { day: "D1", action: "Email (personalized intro)" },
                      { day: "D2", action: "LinkedIn connection request" },
                      { day: "D4", action: "Email follow-up (case study)" },
                      { day: "D6", action: "Voice AI call attempt" },
                      { day: "D8", action: "SMS with direct CTA" },
                    ].map((s, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-[#f5f5f7] flex items-center justify-center text-xs">{s.day}</span>
                        <span>{s.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Step 5: Meetings & Conversion */}
      <section className="px-6 py-24 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <ScrollReveal animation="fade-right">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0066CC]/10 text-[#0066CC] text-sm font-medium mb-6">
                  <span className="w-6 h-6 rounded-full bg-[#0066CC] text-white flex items-center justify-center text-xs font-bold">5</span>
                  <span>Meetings & Conversion</span>
                </div>
                <h2 className="text-4xl font-semibold tracking-tight mb-4">
                  Meetings booked.<br />Pipeline filled.
                </h2>
                <p className="text-lg text-[#1d1d1f]/60 mb-6 leading-relaxed">
                  When prospects reply positively, they're automatically moved to your calendar. Conversion Intelligence learns what's working so every campaign improves.
                </p>
                <ul className="space-y-3">
                  {[
                    "Calendar integration (Google, Outlook, Calendly)",
                    "AI-powered reply detection and classification",
                    "Automatic meeting scheduling for positive replies",
                    "Conversion Intelligence learns from every interaction",
                    "Full pipeline visibility from first touch to close",
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-[#1d1d1f]/70">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
            <ScrollReveal animation="fade-left" delay={100}>
              <div className="bg-gradient-to-br from-[#0066CC] to-[#5856D6] rounded-2xl p-8 text-white">
                <p className="text-sm text-white/60 uppercase tracking-wider mb-6">This Month's Results</p>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {[
                    { value: "2,847", label: "Leads Contacted" },
                    { value: "342", label: "Replies" },
                    { value: "47", label: "Meetings Booked" },
                    { value: "$284K", label: "Pipeline Value" },
                  ].map((stat, i) => (
                    <div key={i} className="p-4 rounded-xl bg-white/10 backdrop-blur">
                      <p className="text-2xl font-bold">{stat.value}</p>
                      <p className="text-sm text-white/60">{stat.label}</p>
                    </div>
                  ))}
                </div>
                <div className="p-4 rounded-xl bg-white/10 backdrop-blur">
                  <p className="text-sm text-white/60 mb-2">Conversion Intelligence Insight</p>
                  <p className="font-medium">"Healthcare leads convert 2.3x better when contacted on Tuesday mornings with case study content."</p>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 py-24 bg-[#fafafa]">
        <div className="max-w-3xl mx-auto text-center">
          <ScrollReveal animation="fade-up">
            <h2 className="text-4xl md:text-5xl font-semibold tracking-tight mb-4">
              Ready to automate your outbound?
            </h2>
            <p className="text-xl text-[#1d1d1f]/60 mb-10">
              Join the waitlist for early access at 50% off for life.
            </p>
          </ScrollReveal>
          <ScrollReveal animation="fade-up" delay={100}>
            <WaitlistForm source="how-it-works-page" />
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
