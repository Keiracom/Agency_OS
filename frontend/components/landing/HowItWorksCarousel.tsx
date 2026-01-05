"use client";

/**
 * FILE: frontend/components/landing/HowItWorksCarousel.tsx
 * PURPOSE: Instagram-style carousel for How It Works section
 * FEATURES: Previous/next arrows, blurred side slides, dot indicators, auto-advance
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { ChevronLeft, ChevronRight, Globe, Users, BarChart3, Zap, Calendar, Check, Mail, Linkedin, Phone } from "lucide-react";

interface Slide {
  id: string;
  number: string;
  title: string;
  badge: string;
  badgeColor: string;
  description: string;
  subtext: string;
}

const slides: Slide[] = [
  {
    id: "discover",
    number: "01",
    title: "Enter your website URL",
    badge: "5 minutes",
    badgeColor: "bg-blue-500/20 text-blue-300",
    description: "Our AI scans your services, case studies, and testimonials. It extracts exactly who your ideal clients are — industries, company sizes, decision-maker titles.",
    subtext: "No forms. No questionnaires. Just your URL.",
  },
  {
    id: "scout",
    number: "02",
    title: "AI scouts your leads",
    badge: "Automated",
    badgeColor: "bg-emerald-500/20 text-emerald-300",
    description: "Our enrichment engine finds prospects matching your ICP. Verified emails, direct dials, LinkedIn profiles. Each lead gets enriched with company data, tech stack, and recent news.",
    subtext: "Hundreds of leads, ready to reach.",
  },
  {
    id: "score",
    number: "03",
    title: "Agency Lead Score (ALS)",
    badge: "Intelligent",
    badgeColor: "bg-orange-500/20 text-orange-300",
    description: "Not all leads are equal. Our ALS scores every prospect across 5 dimensions — Data Quality, Authority, Company Fit, Timing, and Risk. Focus on the 20% that drive 80% of results.",
    subtext: "Hot leads get priority. Cold leads get nurtured.",
  },
  {
    id: "reach",
    number: "04",
    title: "Multi-channel outreach begins",
    badge: "24/7",
    badgeColor: "bg-purple-500/20 text-purple-300",
    description: "Email → LinkedIn → SMS → Voice AI → Direct Mail. All orchestrated automatically. Hot leads get all channels. Cooler leads get email-first.",
    subtext: "Your voice, amplified across every channel.",
  },
  {
    id: "convert",
    number: "05",
    title: "Meetings land in your calendar",
    badge: "Results",
    badgeColor: "bg-emerald-500/20 text-emerald-300",
    description: "When prospects reply or pick up, we capture the win, book the meeting, and update your pipeline. Conversion Intelligence learns what works for YOUR agency.",
    subtext: "You focus on closing. We handle everything else.",
  },
];

// Demo components for each slide
function DiscoverDemo() {
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <Globe className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <input type="text" value="https://yourwebsite.com.au" disabled className="w-full bg-transparent text-white border-b border-white/20 pb-2 text-sm" />
        </div>
      </div>
      <div className="space-y-2.5">
        {["Industries: Healthcare, Professional Services, Real Estate", "Company size: 50-500 employees", "Titles: CMO, Marketing Director, Head of Growth"].map((item, i) => (
          <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/5">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-xs text-white/80">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoutDemo() {
  const leads = [
    { initials: "SC", name: "Sarah Chen", title: "Marketing Director at Bloom Digital", gradient: "from-blue-400 to-blue-600" },
    { initials: "MJ", name: "Michael Jones", title: "CMO at Growth Labs", gradient: "from-purple-400 to-purple-600" },
    { initials: "LW", name: "Lisa Wong", title: "Head of Growth at Pixel Perfect", gradient: "from-amber-400 to-amber-600" },
  ];
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-5 space-y-2.5">
      {leads.map((lead, i) => (
        <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/5">
          <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${lead.gradient} flex items-center justify-center text-white text-xs font-bold shrink-0`}>
            {lead.initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm text-white truncate">{lead.name}</p>
            <p className="text-xs text-white/50 truncate">{lead.title}</p>
          </div>
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 shrink-0">Verified</span>
        </div>
      ))}
    </div>
  );
}

function ScoreDemo() {
  const dimensions = [
    { name: "Data Quality", score: "18/20", percent: 90, color: "bg-blue-500" },
    { name: "Authority", score: "23/25", percent: 92, color: "bg-purple-500" },
    { name: "Company Fit", score: "22/25", percent: 88, color: "bg-emerald-500" },
    { name: "Timing", score: "14/15", percent: 93, color: "bg-amber-500" },
    { name: "Risk", score: "15/15", percent: 100, color: "bg-red-500" },
  ];
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-5">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center text-white text-lg font-bold">92</div>
          <div>
            <p className="font-medium text-white text-sm">Sarah Chen</p>
            <p className="text-xs text-white/50">Bloom Digital</p>
          </div>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full bg-red-500/20 text-red-300 font-medium">HOT</span>
      </div>
      <div className="space-y-2.5">
        {dimensions.map((dim, i) => (
          <div key={i}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-white/50">{dim.name}</span>
              <span className="text-white/70">{dim.score}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10">
              <div className={`h-full rounded-full ${dim.color}`} style={{ width: `${dim.percent}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReachDemo() {
  const steps = [
    { icon: Mail, label: "Email sent", sub: "Personalized intro", status: "✓ Opened", statusColor: "text-emerald-400", iconBg: "bg-blue-500/20", iconColor: "text-blue-400" },
    { icon: Linkedin, label: "LinkedIn connection", sub: "With note", status: "✓ Accepted", statusColor: "text-emerald-400", iconBg: "bg-sky-500/20", iconColor: "text-sky-400" },
    { icon: Phone, label: "Voice AI call", sub: "Friendly follow-up", status: "● In progress", statusColor: "text-blue-400", iconBg: "bg-purple-500/20", iconColor: "text-purple-400" },
  ];
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-5">
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i}>
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg ${step.iconBg} flex items-center justify-center shrink-0`}>
                <step.icon className={`w-4 h-4 ${step.iconColor}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white">{step.label}</p>
                <p className="text-xs text-white/50">{step.sub}</p>
              </div>
              <span className={`text-xs ${step.statusColor} shrink-0`}>{step.status}</span>
            </div>
            {i < steps.length - 1 && (
              <div className="border-l-2 border-white/10 ml-4 pl-7 py-1.5">
                <span className="text-xs text-white/30">Wait {i === 0 ? "2 days" : "1 day"}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ConvertDemo() {
  return (
    <div className="rounded-xl bg-[#0a0a0f] border border-white/10 p-5">
      <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
        <div className="w-9 h-9 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
          <Check className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="font-medium text-emerald-300 text-sm">Meeting Booked!</p>
          <p className="text-xs text-white/50">Sarah Chen • Tomorrow 2:00 PM AEST</p>
        </div>
      </div>
      <div className="space-y-3">
        <div className="p-3 rounded-lg bg-white/5">
          <p className="text-xs text-white/40 mb-2">What converted this lead:</p>
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">Case study mention</span>
            <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">3rd touchpoint</span>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">Morning send</span>
          </div>
        </div>
        <div className="p-3 rounded-lg bg-white/5">
          <p className="text-xs text-white/40 mb-1">Pipeline impact:</p>
          <p className="text-xl font-bold text-emerald-400">+$45,000</p>
        </div>
      </div>
    </div>
  );
}

const demoComponents: Record<string, React.FC> = {
  discover: DiscoverDemo,
  scout: ScoutDemo,
  score: ScoreDemo,
  reach: ReachDemo,
  convert: ConvertDemo,
};

export default function HowItWorksCarousel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const goToSlide = useCallback((index: number) => {
    if (index < 0) index = slides.length - 1;
    if (index >= slides.length) index = 0;
    setActiveIndex(index);
  }, []);

  const goNext = useCallback(() => goToSlide(activeIndex + 1), [activeIndex, goToSlide]);
  const goPrev = useCallback(() => goToSlide(activeIndex - 1), [activeIndex, goToSlide]);

  // Auto-advance
  useEffect(() => {
    if (isPaused) return;
    const timer = setInterval(goNext, 6000);
    return () => clearInterval(timer);
  }, [isPaused, goNext]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "ArrowRight") goNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goNext, goPrev]);

  return (
    <section
      id="how-it-works"
      className="py-20 px-6 overflow-hidden"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-blue-400 font-semibold text-sm uppercase tracking-wider mb-3">How It Works</p>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-white">From zero to booked meetings</h2>
          <p className="text-xl text-white/50">In days, not months.</p>
        </div>

        {/* Carousel Container */}
        <div ref={containerRef} className="relative">
          {/* Left Arrow */}
          <button
            onClick={goPrev}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 md:-translate-x-6 z-20 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 flex items-center justify-center transition-all duration-300 backdrop-blur-sm"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-6 h-6 text-white" />
          </button>

          {/* Right Arrow */}
          <button
            onClick={goNext}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 md:translate-x-6 z-20 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 flex items-center justify-center transition-all duration-300 backdrop-blur-sm"
            aria-label="Next slide"
          >
            <ChevronRight className="w-6 h-6 text-white" />
          </button>

          {/* Slides Container */}
          <div className="relative flex items-center justify-center">
            {slides.map((slide, index) => {
              const offset = index - activeIndex;
              const isActive = index === activeIndex;
              const isPrev = offset === -1 || (activeIndex === 0 && index === slides.length - 1);
              const isNext = offset === 1 || (activeIndex === slides.length - 1 && index === 0);
              const isVisible = isActive || isPrev || isNext;

              if (!isVisible) return null;

              const DemoComponent = demoComponents[slide.id];

              return (
                <div
                  key={slide.id}
                  className={`
                    transition-all duration-500 ease-out
                    ${isActive ? "relative z-10 opacity-100 scale-100" : "absolute z-0 opacity-40 scale-90 blur-[2px] pointer-events-none"}
                    ${isPrev ? "-translate-x-[85%]" : ""}
                    ${isNext ? "translate-x-[85%]" : ""}
                  `}
                  style={{
                    width: isActive ? "100%" : "100%",
                  }}
                >
                  <div className="rounded-2xl bg-[#12121a] border border-white/10 overflow-hidden">
                    <div className="p-6 md:p-10">
                      {/* Step Eyebrow Label */}
                      <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase text-center mb-6">
                        Step {parseInt(slide.number)} • {slide.id.charAt(0).toUpperCase() + slide.id.slice(1)}
                      </p>

                      <div className="grid md:grid-cols-2 gap-8 items-center">
                        {/* Left: Text Content */}
                        <div>
                          <span className={`text-xs px-3 py-1 rounded-full ${slide.badgeColor} mb-4 inline-block`}>
                            {slide.badge}
                          </span>
                          <h3 className="text-2xl md:text-3xl font-bold mb-4 text-white">{slide.title}</h3>
                          <p className="text-white/60 leading-relaxed mb-4">{slide.description}</p>
                          <p className="text-white/40 text-sm">{slide.subtext}</p>
                        </div>

                        {/* Right: Visual Demo */}
                        <div>
                          <DemoComponent />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Dot Indicators */}
          <div className="flex justify-center gap-2 mt-8">
            {slides.map((slide, index) => (
              <button
                key={slide.id}
                onClick={() => goToSlide(index)}
                className={`
                  h-2 rounded-full transition-all duration-300
                  ${activeIndex === index
                    ? "w-8 bg-gradient-to-r from-blue-500 to-purple-600"
                    : "w-2 bg-white/20 hover:bg-white/40"
                  }
                `}
                aria-label={`Go to slide ${index + 1}`}
              />
            ))}
          </div>

          {/* Step Counter */}
          <div className="text-center mt-4">
            <span className="text-white/40 text-sm">
              {slides[activeIndex].number} of 05 — {slides[activeIndex].id.charAt(0).toUpperCase() + slides[activeIndex].id.slice(1)}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
