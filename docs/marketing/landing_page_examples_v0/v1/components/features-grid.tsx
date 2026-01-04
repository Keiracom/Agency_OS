"use client"

import { motion } from "framer-motion"
import { MapPin, Brain, Award } from "lucide-react"
import { Card } from "@/components/ui/card"

const features = [
  {
    icon: MapPin,
    title: "Australian-first",
    description:
      "Built specifically for Australian agencies targeting local businesses. Understands Aussie market dynamics, time zones, and business culture.",
    gradient: "from-blue-500 to-cyan-500",
  },
  {
    icon: Brain,
    title: "Conversion Intelligence",
    description:
      "ML models trained on 10M+ successful agency-client relationships. Predicts which prospects will convert before you reach out.",
    gradient: "from-purple-500 to-pink-500",
  },
  {
    icon: Award,
    title: "Agency Lead Score™",
    description:
      "Proprietary scoring system that ranks leads by budget size, decision timeline, and agency fit. Focus only on deals worth your time.",
    gradient: "from-orange-500 to-red-500",
  },
]

export function FeaturesGrid() {
  return (
    <section className="py-20 md:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-balance mb-4">Why we're different</h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Purpose-built for Australian marketing agencies who are serious about growth
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="p-8 h-full hover:shadow-xl transition-all duration-300 hover:-translate-y-2 glass glass-border">
                <div
                  className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center text-white mb-6 shadow-lg`}
                >
                  <feature.icon className="h-7 w-7" />
                </div>
                <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
