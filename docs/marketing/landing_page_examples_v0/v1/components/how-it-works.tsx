"use client"

import { motion } from "framer-motion"
import { Database, Brain, Target, Zap, Calendar } from "lucide-react"

const steps = [
  {
    icon: Database,
    title: "Connect your data",
    description: "Link your CRM and define your ideal customer profile in minutes",
    number: "01",
  },
  {
    icon: Brain,
    title: "AI learns your market",
    description: "Our AI analyzes millions of companies to find perfect matches",
    number: "02",
  },
  {
    icon: Target,
    title: "Prospects are scored",
    description: "Each lead is ranked by conversion probability and deal value",
    number: "03",
  },
  {
    icon: Zap,
    title: "Outreach begins",
    description: "Personalized messages sent across email, LinkedIn, phone, and SMS",
    number: "04",
  },
  {
    icon: Calendar,
    title: "Meetings booked",
    description: "Interested prospects automatically scheduled on your calendar",
    number: "05",
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 md:py-32 bg-gradient-to-b from-white to-gray-50">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-balance mb-4">How it works</h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            From setup to your first booked meeting in less than 2 weeks
          </p>
        </motion.div>

        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-20 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-purple-600 to-blue-500 opacity-20" />

          <div className="grid md:grid-cols-5 gap-8 md:gap-4">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative"
              >
                <div className="flex flex-col items-center text-center">
                  {/* Icon container */}
                  <div className="relative mb-6">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all hover:scale-110 duration-300 z-10 relative">
                      <step.icon className="h-8 w-8" />
                    </div>
                    {/* Step number */}
                    <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-xs font-bold text-blue-500">
                      {step.number}
                    </div>
                  </div>

                  <h3 className="text-xl font-bold mb-2">{step.title}</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
