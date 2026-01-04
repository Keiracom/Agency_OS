"use client"

import { useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"

const stats = [
  { value: 35, suffix: "%+", label: "Open rate" },
  { value: 12, suffix: "%", label: "Reply rate" },
  { value: 14, suffix: " days", label: "To first meeting", prefix: "<" },
  { value: 5, suffix: " channels", label: "Automated outreach" },
]

function AnimatedStat({
  value,
  suffix,
  label,
  prefix = "",
}: { value: number; suffix: string; label: string; prefix?: string }) {
  const [count, setCount] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.5 },
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isVisible) return

    let startTime: number
    const duration = 2000
    const startValue = 0

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime
      const progress = Math.min((currentTime - startTime) / duration, 1)

      const easeOutQuart = 1 - Math.pow(1 - progress, 4)
      setCount(Math.floor(easeOutQuart * value))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [isVisible, value])

  return (
    <div ref={ref} className="flex flex-col items-center">
      <div className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
        {prefix}
        {count}
        {suffix}
      </div>
      <div className="text-sm text-muted-foreground mt-1">{label}</div>
    </div>
  )
}

export function SocialProofStrip() {
  return (
    <section className="py-16 border-y border-border bg-white/50">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12"
        >
          {stats.map((stat, index) => (
            <AnimatedStat key={index} {...stat} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}
