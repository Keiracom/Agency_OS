"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Target, Award, Send, TrendingUp, Mail, Check, Clock, Sparkles, BarChart3 } from "lucide-react"

const features = [
  {
    id: "discover",
    label: "Discover",
    icon: Search,
    title: "Find ideal clients automatically",
    description: "AI scans and identifies perfect-fit prospects from millions of companies",
  },
  {
    id: "scout",
    label: "Scout",
    icon: Target,
    title: "Deep research on every lead",
    description: "Gather intelligence on decision makers, tech stack, and buying signals",
  },
  {
    id: "score",
    label: "Score",
    icon: Award,
    title: "Prioritize high-value opportunities",
    description: "ML algorithms rank leads by conversion probability and deal size",
  },
  {
    id: "reach",
    label: "Reach",
    icon: Send,
    title: "Personalized multi-channel outreach",
    description: "AI-generated messages across email, LinkedIn, phone, and SMS",
  },
  {
    id: "convert",
    label: "Convert",
    icon: TrendingUp,
    title: "Book meetings on autopilot",
    description: "Automated follow-ups and calendar scheduling that never misses",
  },
]

const activityFeed = [
  { type: "discovery", text: "Found 15 new SaaS companies in Sydney", time: "2m ago" },
  { type: "outreach", text: "Sent personalized email to Marcus Chen at TechFlow", time: "5m ago" },
  { type: "response", text: "Sarah Williams replied - interested in demo", time: "12m ago" },
  { type: "meeting", text: "Meeting booked with Pixel Studios for Thursday", time: "18m ago" },
  { type: "discovery", text: "Identified 8 agencies exceeding $5M revenue", time: "25m ago" },
]

export function ProductDemo() {
  const [activeTab, setActiveTab] = useState("discover")
  const [currentActivity, setCurrentActivity] = useState(0)
  const [typedText, setTypedText] = useState("")
  const [isTyping, setIsTyping] = useState(true)
  const [hoveredTab, setHoveredTab] = useState<string | null>(null)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [showSparkles, setShowSparkles] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTab((current) => {
        const currentIndex = features.findIndex((f) => f.id === current)
        const nextIndex = (currentIndex + 1) % features.length
        return features[nextIndex].id
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentActivity((prev) => (prev + 1) % activityFeed.length)
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!isTyping) return

    let currentIndex = 0
    const interval = setInterval(() => {
      if (currentIndex <= fullText.length) {
        setTypedText(fullText.slice(0, currentIndex))
        currentIndex++
      } else {
        setIsTyping(false)
        setTimeout(() => {
          setTypedText("")
          setIsTyping(true)
        }, 3000)
      }
    }, 50)

    return () => clearInterval(interval)
  }, [isTyping])

  const fullText =
    "Hi Marcus,\n\nI noticed TechFlow recently expanded into the Brisbane market. Congrats on the growth!\n\nI work with SaaS companies to streamline their client acquisition process. We've helped similar companies reduce their sales cycle by 40% while increasing qualified leads.\n\nWould you be open to a quick 15-minute call next week?"

  useEffect(() => {
    setShowSparkles(true)
    const timer = setTimeout(() => setShowSparkles(false), 1000)
    return () => clearTimeout(timer)
  }, [activeTab])

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    setMousePosition({ x, y })
  }

  return (
    <section id="features" className="py-20 md:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-balance mb-4">
            Your AI-powered acquisition engine
          </h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Watch as Agency OS finds, qualifies, and books meetings with your ideal clients across 5 channels
          </p>
        </motion.div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-4xl mx-auto grid-cols-5 h-auto mb-12 glass glass-border p-1.5 relative">
            {features.map((feature, index) => (
              <TabsTrigger
                key={feature.id}
                value={feature.id}
                onMouseEnter={() => setHoveredTab(feature.id)}
                onMouseLeave={() => setHoveredTab(null)}
                className="flex flex-col items-center gap-2 py-4 data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-purple-600 data-[state=active]:text-white transition-all rounded-lg relative overflow-hidden group"
              >
                {activeTab === feature.id && (
                  <motion.div
                    initial={{ x: "-100%" }}
                    animate={{ x: "200%" }}
                    transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 3 }}
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  />
                )}

                <motion.div
                  animate={{
                    scale: activeTab === feature.id ? [1, 1.2, 1] : 1,
                  }}
                  transition={{ duration: 0.3 }}
                >
                  <feature.icon className="h-5 w-5 relative z-10" />
                </motion.div>

                <span className="text-xs md:text-sm font-medium hidden sm:inline relative z-10">{feature.label}</span>

                {hoveredTab === feature.id && activeTab !== feature.id && (
                  <motion.div
                    layoutId="hover-indicator"
                    className="absolute inset-0 bg-gray-100 rounded-lg"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  />
                )}
              </TabsTrigger>
            ))}
          </TabsList>

          {features.map((feature) => (
            <TabsContent key={feature.id} value={feature.id} className="mt-0">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="grid md:grid-cols-5 gap-8 items-start"
              >
                <motion.div
                  className="md:col-span-2 space-y-4"
                  initial="hidden"
                  animate="visible"
                  variants={{
                    hidden: { opacity: 0 },
                    visible: {
                      opacity: 1,
                      transition: {
                        staggerChildren: 0.1,
                      },
                    },
                  }}
                >
                  <motion.div
                    variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                    className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white relative overflow-hidden"
                  >
                    <feature.icon className="h-6 w-6 relative z-10" />
                    <motion.div
                      animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                      transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                      className="absolute inset-0 bg-white rounded-xl"
                    />
                  </motion.div>

                  <motion.h3
                    variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                    className="text-2xl md:text-3xl font-bold"
                  >
                    {feature.title}
                  </motion.h3>

                  <motion.p
                    variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                    className="text-muted-foreground text-lg leading-relaxed"
                  >
                    {feature.description}
                  </motion.p>

                  <motion.div
                    variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                    className="space-y-4 pt-4"
                  >
                    {[
                      { label: "Lead Quality", value: 96, color: "from-emerald-500 to-teal-600" },
                      { label: "Response Rate", value: 48, color: "from-blue-500 to-cyan-600" },
                      { label: "Meeting Conversion", value: 32, color: "from-purple-500 to-pink-600" },
                    ].map((metric, i) => (
                      <motion.div key={metric.label}>
                        <div className="flex justify-between text-sm mb-2">
                          <span className="font-medium">{metric.label}</span>
                          <motion.span
                            className="text-muted-foreground font-mono"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.5 + i * 0.2 }}
                          >
                            {metric.value}%
                          </motion.span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${metric.value}%` }}
                            transition={{ duration: 1.2, delay: 0.3 + i * 0.2, ease: "easeOut" }}
                            className={`h-full bg-gradient-to-r ${metric.color} rounded-full relative`}
                          >
                            <motion.div
                              animate={{ x: ["0%", "200%"] }}
                              transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, repeatDelay: 2 }}
                              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent"
                            />
                          </motion.div>
                        </div>
                      </motion.div>
                    ))}
                  </motion.div>
                </motion.div>

                <motion.div
                  className="md:col-span-3"
                  onMouseMove={handleMouseMove}
                  style={{
                    transformStyle: "preserve-3d",
                    perspective: "1000px",
                  }}
                >
                  <motion.div
                    className="glass glass-border rounded-2xl overflow-hidden shadow-2xl relative"
                    animate={{
                      rotateX: mousePosition.y * 5,
                      rotateY: mousePosition.x * 5,
                    }}
                    transition={{ type: "spring", stiffness: 100, damping: 20 }}
                  >
                    <AnimatePresence>
                      {showSparkles && (
                        <>
                          {[...Array(6)].map((_, i) => (
                            <motion.div
                              key={i}
                              initial={{
                                opacity: 0,
                                scale: 0,
                                x: Math.random() * 100 + "%",
                                y: Math.random() * 100 + "%",
                              }}
                              animate={{
                                opacity: [0, 1, 0],
                                scale: [0, 1.5, 0],
                                rotate: [0, 180, 360],
                              }}
                              exit={{ opacity: 0 }}
                              transition={{ duration: 1, delay: i * 0.1 }}
                              className="absolute pointer-events-none"
                            >
                              <Sparkles className="h-4 w-4 text-blue-500" />
                            </motion.div>
                          ))}
                        </>
                      )}
                    </AnimatePresence>

                    <div className="bg-white border-b border-border px-4 py-3 flex items-center gap-2">
                      <div className="flex gap-2">
                        <motion.div className="w-3 h-3 rounded-full bg-red-400" whileHover={{ scale: 1.2 }} />
                        <motion.div className="w-3 h-3 rounded-full bg-yellow-400" whileHover={{ scale: 1.2 }} />
                        <motion.div className="w-3 h-3 rounded-full bg-green-400" whileHover={{ scale: 1.2 }} />
                      </div>
                      <div className="flex-1 mx-4">
                        <div className="bg-gray-100 rounded-md px-3 py-1.5 text-xs text-muted-foreground flex items-center gap-2">
                          <span className="text-green-500">🔒</span>
                          app.agencyos.ai/dashboard
                        </div>
                      </div>
                    </div>

                    <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-6 min-h-[400px]">
                      <motion.div
                        className="bg-white rounded-lg p-4 shadow-sm mb-4 relative overflow-hidden"
                        whileHover={{ scale: 1.02 }}
                        transition={{ type: "spring", stiffness: 300 }}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-600/20 opacity-0 group-hover:opacity-100 transition-opacity" />

                        <div className="flex items-center justify-between mb-3 relative z-10">
                          <h4 className="font-semibold text-sm flex items-center gap-2">
                            <BarChart3 className="h-4 w-4 text-blue-500" />
                            Live Activity
                          </h4>
                          <span className="relative flex h-2 w-2">
                            <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-green-500" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                          </span>
                        </div>

                        <div className="space-y-3 relative z-10">
                          <AnimatePresence mode="wait">
                            <motion.div
                              key={currentActivity}
                              initial={{ opacity: 0, x: -20, scale: 0.95 }}
                              animate={{ opacity: 1, x: 0, scale: 1 }}
                              exit={{ opacity: 0, x: 20, scale: 0.95 }}
                              transition={{ duration: 0.3 }}
                              className="text-sm bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded-lg border border-blue-100"
                            >
                              <div className="font-medium flex items-center gap-2">
                                <Check className="h-4 w-4 text-green-500" />
                                {activityFeed[currentActivity].text}
                              </div>
                              <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {activityFeed[currentActivity].time}
                              </div>
                            </motion.div>
                          </AnimatePresence>
                        </div>
                      </motion.div>

                      <motion.div
                        className="bg-white rounded-lg p-4 shadow-sm relative overflow-hidden"
                        whileHover={{ scale: 1.02 }}
                        transition={{ type: "spring", stiffness: 300 }}
                      >
                        <div className="flex items-center gap-2 mb-3 relative z-10">
                          <motion.div
                            className="w-2 h-2 rounded-full bg-blue-500"
                            animate={{ scale: [1, 1.3, 1] }}
                            transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
                          />
                          <h4 className="font-semibold text-sm flex items-center gap-2">
                            <Mail className="h-4 w-4 text-blue-500" />
                            AI Writing Email...
                          </h4>
                          <motion.div
                            animate={{ opacity: [0.5, 1, 0.5] }}
                            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                            className="ml-auto text-xs text-muted-foreground"
                          >
                            Personalizing...
                          </motion.div>
                        </div>

                        <div className="text-sm text-gray-700 font-mono whitespace-pre-wrap min-h-[200px] relative z-10">
                          {typedText}
                          <motion.span
                            className="inline-block w-0.5 h-4 bg-blue-500 ml-0.5"
                            animate={{ opacity: [1, 0, 1] }}
                            transition={{ duration: 0.8, repeat: Number.POSITIVE_INFINITY }}
                          />
                        </div>

                        <motion.div
                          animate={{
                            backgroundPosition: ["0% 0%", "100% 100%"],
                          }}
                          transition={{ duration: 10, repeat: Number.POSITIVE_INFINITY, repeatType: "reverse" }}
                          className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-transparent to-purple-50/50 opacity-30"
                          style={{ backgroundSize: "200% 200%" }}
                        />
                      </motion.div>
                    </div>
                  </motion.div>
                </motion.div>
              </motion.div>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </section>
  )
}
