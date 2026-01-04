"use client"

import { useState, useEffect } from "react"
import { Mail, Linkedin, Phone, MessageSquare, ArrowRight } from "lucide-react"

interface Activity {
  id: number
  message: string
  icon: "mail" | "linkedin" | "phone" | "sms"
  color: "blue" | "green" | "purple"
}

const activities: Activity[] = [
  { id: 1, message: "Email opened by Sarah Williams", icon: "mail", color: "blue" },
  { id: 2, message: "Connection accepted: Marcus Chen", icon: "linkedin", color: "blue" },
  { id: 3, message: "Voice AI: Meeting booked with Pixel Studios", icon: "phone", color: "green" },
  { id: 4, message: "SMS delivered to James Cooper", icon: "sms", color: "purple" },
  { id: 5, message: "Email opened by David Taylor", icon: "mail", color: "blue" },
  { id: 6, message: "Connection accepted: Emma Wilson", icon: "linkedin", color: "blue" },
  { id: 7, message: "Voice AI: Meeting booked with Studio 42", icon: "phone", color: "green" },
  { id: 8, message: "SMS delivered to Sophie Martinez", icon: "sms", color: "purple" },
]

const iconMap = {
  mail: Mail,
  linkedin: Linkedin,
  phone: Phone,
  sms: MessageSquare,
}

const colorMap = {
  blue: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  green: "bg-green-500/20 text-green-400 border-green-500/30",
  purple: "bg-purple-500/20 text-purple-400 border-purple-500/30",
}

export default function AgencyOSHero() {
  const [visibleActivities, setVisibleActivities] = useState<Activity[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // Trigger animations on mount
    setIsVisible(true)

    // Initialize with first 5 activities
    setVisibleActivities(activities.slice(0, 5))

    // Rotate activities every 3 seconds
    const interval = setInterval(() => {
      setCurrentIndex((prev) => {
        const nextIndex = (prev + 1) % activities.length
        setVisibleActivities((current) => {
          const newActivity = activities[nextIndex]
          return [newActivity, ...current.slice(0, 4)]
        })
        return nextIndex
      })
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <section className="relative min-h-screen bg-[#0a0a0f] overflow-hidden">
      {/* Floating gradient orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/30 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/30 rounded-full blur-[120px] animate-float-delayed" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-blue-400/20 rounded-full blur-[100px] animate-pulse-slow" />
      </div>

      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 py-20 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left side - Main content */}
          <div className="space-y-8">
            {/* Urgency badge */}
            <div
              className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/5 backdrop-blur-[20px] transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: "0ms" }}
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
              <span className="text-sm text-white/90 font-medium">Only 17 of 20 founding spots remaining</span>
            </div>

            {/* Headline */}
            <h1
              className={`text-5xl lg:text-7xl font-bold leading-tight transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: "100ms" }}
            >
              <span className="bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
                Stop chasing clients.
                <br />
                Let them find you.
              </span>
            </h1>

            {/* Subheadline */}
            <p
              className={`text-xl lg:text-2xl text-white/70 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: "200ms" }}
            >
              Five channels. Fully automated. One platform.
            </p>

            {/* CTAs */}
            <div
              className={`flex flex-col sm:flex-row gap-4 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: "300ms" }}
            >
              <button className="group relative px-8 py-4 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold text-lg overflow-hidden transition-all hover:scale-105 hover:shadow-[0_0_40px_rgba(139,92,246,0.5)]">
                <span className="relative z-10">See It In Action</span>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-700 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button className="group flex items-center gap-2 px-8 py-4 text-white/90 font-semibold text-lg hover:text-white transition-colors">
                How it works
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          {/* Right side - Live activity feed */}
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
            style={{ transitionDelay: "400ms" }}
          >
            <div className="relative">
              {/* Glass card container */}
              <div className="rounded-lg border border-white/10 bg-white/5 backdrop-blur-[20px] p-4 space-y-3">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-semibold text-lg">Live Activity</h3>
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                    </span>
                    <span className="text-xs text-white/50">Live</span>
                  </div>
                </div>

                {/* Activity items */}
                <div className="space-y-2 min-h-[320px]">
                  {visibleActivities.map((activity, index) => {
                    const Icon = iconMap[activity.icon]
                    return (
                      <div
                        key={`${activity.id}-${index}`}
                        className="flex items-start gap-3 p-3 rounded-lg border border-white/10 bg-white/5 backdrop-blur-[20px] animate-slide-in"
                        style={{
                          animationDelay: index === 0 ? "0ms" : "0ms",
                          animationFillMode: "backwards",
                        }}
                      >
                        <div
                          className={`flex items-center justify-center w-10 h-10 rounded-lg border ${colorMap[activity.color]}`}
                        >
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-white/90 text-sm leading-relaxed">{activity.message}</p>
                          <p className="text-white/50 text-xs mt-1">Just now</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/20 to-purple-600/20 rounded-lg blur-xl -z-10" />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
