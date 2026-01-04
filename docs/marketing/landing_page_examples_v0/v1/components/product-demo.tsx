"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Target, Award, Send, TrendingUp } from "lucide-react"

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

  const fullText =
    "Hi Marcus,\n\nI noticed TechFlow recently expanded into the Brisbane market. Congrats on the growth!\n\nI work with SaaS companies to streamline their client acquisition process. We've helped similar companies reduce their sales cycle by 40% while increasing qualified leads.\n\nWould you be open to a quick 15-minute call next week?"

  // Auto-rotate tabs
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

  // Activity feed animation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentActivity((prev) => (prev + 1) % activityFeed.length)
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  // Typing animation
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
          <TabsList className="grid w-full max-w-4xl mx-auto grid-cols-5 h-auto mb-12 glass glass-border p-1.5">
            {features.map((feature) => (
              <TabsTrigger
                key={feature.id}
                value={feature.id}
                className="flex flex-col items-center gap-2 py-4 data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-purple-600 data-[state=active]:text-white transition-all rounded-lg"
              >
                <feature.icon className="h-5 w-5" />
                <span className="text-xs md:text-sm font-medium hidden sm:inline">{feature.label}</span>
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
                {/* Feature description */}
                <div className="md:col-span-2 space-y-4">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-2xl md:text-3xl font-bold">{feature.title}</h3>
                  <p className="text-muted-foreground text-lg leading-relaxed">{feature.description}</p>

                  {/* Progress bars */}
                  <div className="space-y-4 pt-4">
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="font-medium">Lead Quality</span>
                        <span className="text-muted-foreground">96%</span>
                      </div>
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: "96%" }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, delay: 0.2 }}
                        className="h-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="font-medium">Response Rate</span>
                        <span className="text-muted-foreground">48%</span>
                      </div>
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: "48%" }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, delay: 0.4 }}
                        className="h-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="font-medium">Meeting Conversion</span>
                        <span className="text-muted-foreground">32%</span>
                      </div>
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: "32%" }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, delay: 0.6 }}
                        className="h-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
                      />
                    </div>
                  </div>
                </div>

                {/* Browser mockup */}
                <div className="md:col-span-3">
                  <div className="glass glass-border rounded-2xl overflow-hidden shadow-2xl">
                    {/* Browser chrome */}
                    <div className="bg-white border-b border-border px-4 py-3 flex items-center gap-2">
                      <div className="flex gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-400" />
                        <div className="w-3 h-3 rounded-full bg-yellow-400" />
                        <div className="w-3 h-3 rounded-full bg-green-400" />
                      </div>
                      <div className="flex-1 mx-4">
                        <div className="bg-gray-100 rounded-md px-3 py-1.5 text-xs text-muted-foreground">
                          app.agencyos.ai/dashboard
                        </div>
                      </div>
                    </div>

                    {/* Dashboard content */}
                    <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-6 min-h-[400px]">
                      {/* Activity feed */}
                      <div className="bg-white rounded-lg p-4 shadow-sm mb-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-sm">Live Activity</h4>
                          <span className="relative flex h-2 w-2">
                            <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-green-500" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                          </span>
                        </div>
                        <div className="space-y-3">
                          <AnimatePresence mode="wait">
                            <motion.div
                              key={currentActivity}
                              initial={{ opacity: 0, x: -20 }}
                              animate={{ opacity: 1, x: 0 }}
                              exit={{ opacity: 0, x: 20 }}
                              transition={{ duration: 0.3 }}
                              className="text-sm"
                            >
                              <div className="font-medium">{activityFeed[currentActivity].text}</div>
                              <div className="text-xs text-muted-foreground mt-1">
                                {activityFeed[currentActivity].time}
                              </div>
                            </motion.div>
                          </AnimatePresence>
                        </div>
                      </div>

                      {/* AI typing email */}
                      <div className="bg-white rounded-lg p-4 shadow-sm">
                        <div className="flex items-center gap-2 mb-3">
                          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                          <h4 className="font-semibold text-sm">AI Writing Email...</h4>
                        </div>
                        <div className="text-sm text-gray-700 font-mono whitespace-pre-wrap min-h-[200px]">
                          {typedText}
                          <span className="inline-block w-0.5 h-4 bg-blue-500 animate-pulse ml-0.5" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </section>
  )
}
