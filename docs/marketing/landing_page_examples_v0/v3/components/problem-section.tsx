"use client"

import { motion } from "framer-motion"
import { Card } from "@/components/ui/card"
import { Clock, Mail, Linkedin, TrendingDown, Users } from "lucide-react"

// Schwartz's awareness bridge - meet them where they ARE
const painPoints = [
  {
    icon: TrendingDown,
    title: "The feast-or-famine cycle",
    description: "One month you're drowning in work. Next month, crickets. You know you need consistent outreach, but who has time when you're delivering for current clients?",
  },
  {
    icon: Mail,
    title: "The cold email graveyard",
    description: "You've tried Apollo. Instantly. Lemlist. Maybe even hired an SDR. Open rates tanked. Responses dried up. Your domain got flagged. $2,000/month down the drain.",
  },
  {
    icon: Linkedin,
    title: "The LinkedIn hamster wheel",
    description: "Connect. Wait. Follow up. Get ignored. Repeat 50 times for one meeting. There has to be a better way.",
  },
  {
    icon: Users,
    title: 'The "we should do more marketing" meeting',
    description: "Every quarter, same conversation. Same good intentions. Same zero execution. Because everyone's too busy doing client work to do your OWN marketing.",
  },
]

export function ProblemSection() {
  return (
    <section className="py-20 md:py-28 bg-gray-50">
      <div className="max-w-6xl mx-auto px-6">
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-balance mb-4">
            Sound familiar?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every growing agency hits these walls. The question is whether you keep hitting them—or build a system to break through.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {painPoints.map((point, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="p-6 h-full hover:shadow-lg transition-all duration-300 border-gray-200 bg-white">
                <div className="flex gap-4">
                  <div className="shrink-0">
                    <div className="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center">
                      <point.icon className="h-6 w-6 text-red-500" />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold mb-2 text-gray-900">{point.title}</h3>
                    <p className="text-muted-foreground leading-relaxed">{point.description}</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Transition to solution - Schwartz's mechanism tease */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center mt-16"
        >
          <p className="text-xl text-muted-foreground">
            What if there was a system that handled all of this{" "}
            <span className="text-foreground font-semibold">while you focused on what you do best?</span>
          </p>
        </motion.div>
      </div>
    </section>
  )
}
