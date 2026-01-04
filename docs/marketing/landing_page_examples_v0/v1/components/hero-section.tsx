"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Play } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 md:pt-40 md:pb-32">
      {/* Floating gradient orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          className="absolute top-20 left-10 w-96 h-96 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full blur-3xl opacity-20 animate-float"
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.3 }}
          className="absolute top-40 right-10 w-96 h-96 bg-gradient-to-r from-purple-400 to-blue-500 rounded-full blur-3xl opacity-20"
          style={{ animation: "float 25s ease-in-out infinite" }}
        />
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="flex flex-col items-center text-center">
          {/* Urgency badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-border glass glass-border px-4 py-2 text-sm mb-8"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-blue-500" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
            </span>
            <span className="font-medium">17 of 20 founding spots left</span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-balance mb-6 max-w-5xl"
          >
            Stop chasing clients.{" "}
            <span className="bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
              Let them find you.
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg md:text-xl text-muted-foreground text-balance mb-10 max-w-3xl leading-relaxed"
          >
            5-channel AI automation finds, qualifies, and books meetings with your ideal clients. Built exclusively for
            Australian marketing agencies.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center gap-4 mb-16"
          >
            <Button
              size="lg"
              className="text-base px-8 h-12 bg-gradient-to-r from-blue-500 to-purple-600 text-white border-0 hover:opacity-90 shadow-lg hover:shadow-xl transition-all"
            >
              Join the Waitlist
            </Button>
            <Button size="lg" variant="ghost" className="text-base h-12 group">
              <Play className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform" />
              Watch Demo (2 min)
            </Button>
          </motion.div>

          {/* Video placeholder */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="w-full max-w-6xl"
          >
            <div className="relative w-full aspect-video rounded-2xl glass glass-border overflow-hidden shadow-2xl group hover:shadow-blue-500/20 transition-all duration-500">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-600/10" />
              <div className="absolute inset-0 flex items-center justify-center backdrop-blur-[1px]">
                <div className="h-20 w-20 rounded-full glass glass-border flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform duration-300 cursor-pointer">
                  <Play className="h-10 w-10 text-blue-500 ml-1" fill="currentColor" />
                </div>
              </div>
              <div className="w-full h-full bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center text-muted-foreground">
                <img
                  src="/modern-dashboard.png"
                  alt="Product demo"
                  className="w-full h-full object-cover opacity-50"
                />
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
