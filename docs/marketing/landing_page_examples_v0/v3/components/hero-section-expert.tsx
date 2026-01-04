"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Play, ArrowRight } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 md:pt-40 md:pb-32">
      {/* Floating gradient orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          className="absolute top-20 left-10 w-96 h-96 bg-gradient-to-r from-blue-400/30 to-purple-500/30 rounded-full blur-3xl"
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.3 }}
          className="absolute top-40 right-10 w-96 h-96 bg-gradient-to-r from-purple-400/20 to-blue-500/20 rounded-full blur-3xl"
          style={{ animation: "float 25s ease-in-out infinite" }}
        />
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="flex flex-col items-center text-center">
          
          {/* Urgency badge - Brunson's scarcity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm mb-8"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
            </span>
            <span className="font-semibold text-amber-800">
              Founding Offer: 17 of 20 spots remaining
            </span>
          </motion.div>

          {/* Headline - Ogilvy's clarity principle */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-balance mb-6 max-w-5xl"
          >
            Turn strangers into signed clients{" "}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              while you sleep.
            </span>
          </motion.h1>

          {/* Audience qualifier - Godin's tribe signal */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-6"
          >
            For Australian marketing agencies only
          </motion.p>

          {/* Subheadline - Wiebe's voice-of-customer */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg md:text-xl text-muted-foreground text-balance mb-10 max-w-3xl leading-relaxed"
          >
            You started an agency to do great work—not to spend 60% of your time chasing leads. 
            Agency OS finds, qualifies, and books meetings with ideal clients across 5 channels. 
            <span className="text-foreground font-medium"> You just show up and close.</span>
          </motion.p>

          {/* CTAs - Brunson's ownership language */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col items-center gap-4 mb-4"
          >
            <Button
              size="lg"
              className="text-lg px-10 h-14 bg-gradient-to-r from-blue-600 to-purple-600 text-white border-0 hover:opacity-90 shadow-xl hover:shadow-2xl transition-all group"
            >
              Claim Your Founding Spot
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button size="lg" variant="ghost" className="text-base h-12 group text-muted-foreground">
              <Play className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform" />
              Watch the 2-Minute Demo
            </Button>
          </motion.div>

          {/* Trust signals - Ogilvy's proof */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground mb-16"
          >
            <span>✓ Lock in 50% off for life</span>
            <span>✓ No credit card required</span>
            <span>✓ 14-day free trial</span>
          </motion.div>

          {/* Hero visual */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="w-full max-w-6xl"
          >
            <div className="relative w-full aspect-video rounded-2xl overflow-hidden shadow-2xl border border-gray-200 bg-white group hover:shadow-blue-500/20 transition-all duration-500">
              {/* Browser chrome */}
              <div className="absolute top-0 left-0 right-0 h-10 bg-gray-100 border-b border-gray-200 flex items-center px-4 gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>
                <div className="flex-1 mx-4">
                  <div className="bg-white rounded px-3 py-1 text-xs text-gray-500 max-w-md mx-auto flex items-center gap-2">
                    <span className="text-green-500">🔒</span>
                    app.agencyos.ai/dashboard
                  </div>
                </div>
              </div>
              
              {/* Dashboard preview placeholder */}
              <div className="pt-10 h-full bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
                <div className="absolute inset-0 pt-10 flex items-center justify-center backdrop-blur-[1px]">
                  <div className="h-20 w-20 rounded-full bg-white/90 border border-gray-200 flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform duration-300 cursor-pointer">
                    <Play className="h-10 w-10 text-blue-600 ml-1" fill="currentColor" />
                  </div>
                </div>
                <img
                  src="/modern-dashboard.png"
                  alt="Agency OS Dashboard"
                  className="w-full h-full object-cover opacity-60"
                />
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
