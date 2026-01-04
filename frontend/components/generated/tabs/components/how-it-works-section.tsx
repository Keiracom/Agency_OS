"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { Search, Eye, BarChart3, Rocket, Calendar } from "lucide-react"

interface Step {
  id: string
  number: string
  title: string
  label: string
  description: string
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
    title: "ICP extracted from your website in 5 minutes",
    label: "Discover",
    description:
      "Just enter your website URL. Our AI analyzes your existing clients, case studies, and messaging to understand exactly who you serve best.",
    icon: Search,
  },
  {
    id: "find",
    number: "02",
    title: "AI scouts Australian businesses showing buying signals",
    label: "Find",
    description:
      "Our AI continuously monitors the Australian market for businesses matching your ICP. We look for hiring patterns, tech stack changes, funding announcements.",
    icon: Eye,
  },
  {
    id: "score",
    number: "03",
    title: "ALS Score™ ranks by budget, timeline, and fit",
    label: "Score",
    description:
      "Every lead gets an Agency Lead Score (ALS) from 0-100. Focus only on Hot leads (85+) that are ready to close.",
    icon: BarChart3,
  },
  {
    id: "reach",
    number: "04",
    title: "5-channel outreach: Email, SMS, LinkedIn, Voice, Mail",
    label: "Reach",
    description:
      "True multi-channel engagement. LinkedIn warms them up, email provides value, voice AI books the meeting.",
    icon: Rocket,
  },
  {
    id: "convert",
    number: "05",
    title: "Meetings booked on your calendar. Automatically.",
    label: "Convert",
    description: "When a lead is ready, our AI handles the booking conversation. You just show up and close.",
    icon: Calendar,
  },
]

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

    return () => {
      if (sectionRef.current) {
        observer.unobserve(sectionRef.current)
      }
    }
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

    // Clear existing pause timeout
    if (pauseTimeoutRef.current) {
      clearTimeout(pauseTimeoutRef.current)
    }

    // Resume after 10 seconds
    pauseTimeoutRef.current = setTimeout(() => {
      setIsPaused(false)
    }, 10000)
  }

  const handleMouseEnter = () => {
    setIsPaused(true)
    if (pauseTimeoutRef.current) {
      clearTimeout(pauseTimeoutRef.current)
    }
  }

  const handleMouseLeave = () => {
    // Resume after 10 seconds
    pauseTimeoutRef.current = setTimeout(() => {
      setIsPaused(false)
    }, 10000)
  }

  const activeStepData = steps[activeStep]
  const Icon = activeStepData.icon

  return (
    <section
      ref={sectionRef}
      className="w-full py-16 px-4"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-3">How It Works</h2>
          <p className="text-white/70 text-lg">From discovery to closed deals in 5 simple steps</p>
        </div>

        {/* Tab Bar */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center gap-1 p-1 rounded-lg bg-white/5 backdrop-blur-[20px] border border-white/10">
            {steps.map((step, index) => (
              <button
                key={step.id}
                onClick={() => handleTabClick(index)}
                className={`
                  relative px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-300
                  ${activeStep === index ? "text-white" : "text-white/50 hover:text-white/70"}
                `}
              >
                {step.label}
                {activeStep === index && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Progress Indicators */}
        <div className="flex justify-center gap-2 mb-10">
          {steps.map((_, index) => (
            <button
              key={index}
              onClick={() => handleTabClick(index)}
              className={`
                w-2 h-2 rounded-full transition-all duration-300
                ${
                  activeStep === index
                    ? "bg-gradient-to-r from-blue-500 to-purple-600 w-8"
                    : "bg-white/20 hover:bg-white/30"
                }
              `}
              aria-label={`Go to step ${index + 1}`}
            />
          ))}
        </div>

        {/* Content Area */}
        <div className="relative overflow-hidden">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`
                transition-all duration-300
                ${
                  activeStep === index
                    ? "opacity-100 translate-x-0 relative"
                    : "opacity-0 translate-x-4 absolute inset-0 pointer-events-none"
                }
              `}
            >
              <div className="bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-lg p-8 md:p-10">
                <div className="flex items-start gap-6">
                  {/* Step Number Badge */}
                  <div className="flex-shrink-0">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <span className="text-white font-bold text-xl">{step.number}</span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-start gap-4 mb-4">
                      <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="text-2xl font-bold text-white leading-tight flex-1">{step.title}</h3>
                    </div>
                    <p className="text-white/70 text-lg leading-relaxed">{step.description}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Auto-rotate indicator */}
        {autoRotate && !isPaused && isInView && (
          <div className="text-center mt-6">
            <p className="text-white/30 text-xs">Auto-advancing</p>
          </div>
        )}
      </div>
    </section>
  )
}
