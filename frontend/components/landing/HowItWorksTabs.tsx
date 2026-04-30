"use client"

/**
 * FILE: frontend/components/landing/HowItWorksTabs.tsx
 * PURPOSE: Interactive tabs showing the 5-step process matching landing-page-v2.html
 * FEATURES: Two-column layout, visual demos for each step, auto-rotate, pill-style tabs
 */

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { Search, Users, BarChart3, Zap, Calendar, Check, Globe, Mail, Linkedin, Phone } from "lucide-react"

interface Step {
  id: string
  number: string
  title: string
  label: string
  badge: string
  badgeColor: string
  description: string
  subtext: string
  icon: React.ComponentType<{ className?: string }>
}

interface HowItWorksSectionProps {
  autoRotate?: boolean
  rotateInterval?: number
}

const steps: Step[] = [
  {
    id: "discover",
    number: "01",
    title: "Enter your website URL",
    label: "Discover",
    badge: "5 minutes",
    badgeColor: "bg-panel/20 text-amber-light",
    description:
      "Our AI scans your services, case studies, and testimonials. It extracts exactly who your ideal clients are — industries, company sizes, decision-maker titles.",
    subtext: "No forms. No questionnaires. Just your URL.",
    icon: Globe,
  },
  {
    id: "scout",
    number: "02",
    title: "AI scouts your leads",
    label: "Scout",
    badge: "Automated",
    badgeColor: "bg-amber/20 text-amber-light",
    description:
      "Our enrichment engine finds prospects matching your ICP. Verified emails, direct dials, LinkedIn profiles. Each lead gets enriched with company data, tech stack, and recent news.",
    subtext: "Hundreds of leads, ready to reach.",
    icon: Users,
  },
  {
    id: "score",
    number: "03",
    title: "Agency Lead Score (ALS)",
    label: "Score",
    badge: "Intelligent",
    badgeColor: "bg-orange-500/20 text-orange-300",
    description:
      "Not all leads are equal. Our ALS scores every prospect across 5 dimensions — Data Quality, Authority, Company Fit, Timing, and Risk. Focus on the 20% that drive 80% of results.",
    subtext: "Hot leads get priority. Cold leads get nurtured.",
    icon: BarChart3,
  },
  {
    id: "reach",
    number: "04",
    title: "Multi-channel outreach begins",
    label: "Reach",
    badge: "24/7",
    badgeColor: "bg-amber/20 text-amber-light",
    description:
      "Email → LinkedIn → SMS → Voice AI → Direct Mail. All orchestrated automatically. Hot leads get all channels. Cooler leads get email-first. AI generates personalized content that sounds like you wrote it.",
    subtext: "Your voice, amplified across every channel.",
    icon: Zap,
  },
  {
    id: "convert",
    number: "05",
    title: "Meetings land in your calendar",
    label: "Convert",
    badge: "Results",
    badgeColor: "bg-amber/20 text-amber-light",
    description:
      "When prospects reply or pick up, we capture the win, book the meeting, and update your pipeline. Conversion Intelligence learns what works for YOUR agency — and gets smarter every day.",
    subtext: "You focus on closing. We handle everything else.",
    icon: Calendar,
  },
]

// Demo panels for each step
function DiscoverDemo() {
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-mint-500 to-mint-600 flex items-center justify-center">
          <Globe className="w-5 h-5 text-ink" />
        </div>
        <div className="flex-1">
          <input
            type="text"
            value="https://yourwebsite.com.au"
            disabled
            className="w-full bg-transparent text-ink border-b border-white/20 pb-2 text-sm focus:outline-none"
          />
        </div>
      </div>
      <div className="space-y-3">
        {[
          "Industries: Healthcare, Professional Services, Real Estate",
          "Company size: 50-500 employees",
          "Titles: CMO, Marketing Director, Head of Growth",
        ].map((item, i) => (
          <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-bg-panel/5">
            <Check className="w-5 h-5 text-amber" />
            <span className="text-sm text-ink/80">{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScoutDemo() {
  const leads = [
    { initials: "SC", name: "Sarah Chen", title: "Marketing Director at Bloom Digital", gradient: "from-text-secondary to-amber" },
    { initials: "MJ", name: "Michael Jones", title: "CMO at Growth Labs", gradient: "from-amber to-amber" },
    { initials: "LW", name: "Lisa Wong", title: "Head of Growth at Pixel Perfect", gradient: "from-amber-400 to-amber-600" },
  ]

  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-6 space-y-3">
      {leads.map((lead, i) => (
        <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-bg-panel/5">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${lead.gradient} flex items-center justify-center text-ink text-xs font-bold`}>
            {lead.initials}
          </div>
          <div className="flex-1">
            <p className="font-medium text-sm text-ink">{lead.name}</p>
            <p className="text-xs text-ink/50">{lead.title}</p>
          </div>
          <span className="text-xs px-2 py-1 rounded bg-amber/20 text-amber-light">Verified</span>
        </div>
      ))}
    </div>
  )
}

function ScoreDemo() {
  const dimensions = [
    { name: "Data Quality", score: "18/20", percent: 90, color: "bg-panel" },
    { name: "Authority", score: "23/25", percent: 92, color: "bg-amber" },
    { name: "Company Fit", score: "22/25", percent: 88, color: "bg-amber" },
    { name: "Timing", score: "14/15", percent: 93, color: "bg-amber-500" },
    { name: "Risk", score: "15/15", percent: 100, color: "bg-amber" },
  ]

  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-amber to-amber-light flex items-center justify-center text-ink text-xl font-bold">
            92
          </div>
          <div>
            <p className="font-medium text-ink">Sarah Chen</p>
            <p className="text-xs text-ink/50">Bloom Digital</p>
          </div>
        </div>
        <span className="text-xs px-3 py-1 rounded-full bg-amber/20 text-amber-light font-medium">HOT</span>
      </div>
      <div className="space-y-3">
        {dimensions.map((dim, i) => (
          <div key={i}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-ink/50">{dim.name}</span>
              <span className="text-ink/80">{dim.score}</span>
            </div>
            <div className="h-1.5 rounded-full bg-bg-panel/10">
              <div className={`h-full rounded-full ${dim.color}`} style={{ width: `${dim.percent}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ReachDemo() {
  const steps = [
    { icon: Mail, label: "Email sent", sub: "Personalized intro", status: "Opened", statusColor: "text-amber", iconBg: "bg-panel/20", iconColor: "text-ink-2" },
    { icon: Linkedin, label: "LinkedIn connection", sub: "With note", status: "Accepted", statusColor: "text-amber", iconBg: "bg-amber/20", iconColor: "text-amber" },
    { icon: Phone, label: "Voice AI call", sub: "Friendly follow-up", status: "In progress", statusColor: "text-ink-2", iconBg: "bg-amber/20", iconColor: "text-amber", pulse: true },
  ]

  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-6">
      <div className="space-y-4">
        {steps.map((step, i) => (
          <div key={i}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-lg ${step.iconBg} flex items-center justify-center`}>
                <step.icon className={`w-5 h-5 ${step.iconColor}`} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-ink">{step.label}</p>
                <p className="text-xs text-ink/50">{step.sub}</p>
              </div>
              <span className={`text-xs ${step.statusColor} ${step.pulse ? "animate-pulse" : ""}`}>
                {step.pulse ? "●" : "✓"} {step.status}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="border-l-2 border-white/10 ml-5 pl-8 py-2">
                <span className="text-xs text-ink/30">Wait {i === 0 ? "2 days" : "1 day"}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function ConvertDemo() {
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-6">
      <div className="flex items-center gap-3 mb-6 p-4 rounded-lg bg-amber-glow border border-amber/20">
        <div className="w-10 h-10 rounded-full bg-amber flex items-center justify-center">
          <Check className="w-5 h-5 text-ink" />
        </div>
        <div>
          <p className="font-medium text-amber-light">Meeting Booked!</p>
          <p className="text-xs text-ink/50">Sarah Chen • Tomorrow 2:00 PM AEST</p>
        </div>
      </div>
      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-bg-panel/5">
          <p className="text-xs text-ink/40 mb-2">What converted this lead:</p>
          <div className="flex flex-wrap gap-2">
            <span className="text-xs px-2 py-1 rounded bg-panel/20 text-amber-light">Case study mention</span>
            <span className="text-xs px-2 py-1 rounded bg-amber/20 text-amber-light">3rd touchpoint</span>
            <span className="text-xs px-2 py-1 rounded bg-amber/20 text-amber-light">Morning send time</span>
          </div>
        </div>
        <div className="p-4 rounded-lg bg-bg-panel/5">
          <p className="text-xs text-ink/40 mb-2">Pipeline impact:</p>
          <p className="text-2xl font-bold text-amber">+$45,000</p>
          <p className="text-xs text-ink/50">Estimated deal value</p>
        </div>
      </div>
    </div>
  )
}

const demoComponents: Record<string, React.FC> = {
  discover: DiscoverDemo,
  scout: ScoutDemo,
  score: ScoreDemo,
  reach: ReachDemo,
  convert: ConvertDemo,
}

export default function HowItWorksSection({ autoRotate = true, rotateInterval = 6000 }: HowItWorksSectionProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [isInView, setIsInView] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const sectionRef = useRef<HTMLDivElement>(null)
  const pauseTimeoutRef = useRef<NodeJS.Timeout>()
  const rotateTimeoutRef = useRef<NodeJS.Timeout>()

  // IntersectionObserver for visibility detection
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsInView(entry.isIntersecting)
      },
      { threshold: 0.3 },
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  // Auto-rotation logic
  useEffect(() => {
    if (!autoRotate || !isInView || isPaused) {
      if (rotateTimeoutRef.current) {
        clearTimeout(rotateTimeoutRef.current)
      }
      return
    }

    rotateTimeoutRef.current = setTimeout(() => {
      setActiveStep((prev) => (prev + 1) % steps.length)
    }, rotateInterval)

    return () => {
      if (rotateTimeoutRef.current) {
        clearTimeout(rotateTimeoutRef.current)
      }
    }
  }, [activeStep, isInView, isPaused, autoRotate, rotateInterval])

  const handleTabClick = (index: number) => {
    setActiveStep(index)
    setIsPaused(true)

    if (pauseTimeoutRef.current) {
      clearTimeout(pauseTimeoutRef.current)
    }

    pauseTimeoutRef.current = setTimeout(() => {
      setIsPaused(false)
    }, 10000)
  }

  const activeStepData = steps[activeStep]
  const DemoComponent = demoComponents[activeStepData.id]

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="py-20 px-6"
    >
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-ink-2 font-semibold text-sm uppercase tracking-wider mb-3">How It Works</p>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-ink">
            From zero to booked meetings
          </h2>
          <p className="text-xl text-ink/50">In days, not months.</p>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {steps.map((step, index) => (
            <button
              key={step.id}
              onClick={() => handleTabClick(index)}
              className={`
                px-6 py-3 rounded-full text-sm font-medium transition-all duration-300
                ${
                  activeStep === index
                    ? "bg-gradient-to-r from-mint-500 to-mint-600 text-ink"
                    : "bg-bg-panel/5 text-ink/60 hover:text-ink hover:bg-bg-panel/10"
                }
              `}
            >
              {step.number} {step.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="rounded-2xl bg-[#12121a] border border-white/10 overflow-hidden">
          <div className="p-8 md:p-12">
            <div className="grid md:grid-cols-2 gap-10 items-center">
              {/* Left: Text Content */}
              <div>
                <span className={`text-xs px-3 py-1 rounded-full ${activeStepData.badgeColor} mb-4 inline-block`}>
                  {activeStepData.badge}
                </span>
                <h3 className="text-2xl md:text-3xl font-bold mb-4 text-ink">{activeStepData.title}</h3>
                <p className="text-ink/60 leading-relaxed mb-6">{activeStepData.description}</p>
                <p className="text-ink/40 text-sm">{activeStepData.subtext}</p>
              </div>

              {/* Right: Visual Demo */}
              <div>
                <DemoComponent />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
