"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Check, Sparkles, ArrowRight, Star } from "lucide-react"
import { motion } from "framer-motion"

export function PricingSection() {
  const plans = [
    {
      name: "Ignition",
      price: "$1,250",
      originalPrice: "$2,500",
      period: "/month",
      description: "For agencies testing systematic outreach for the first time",
      features: [
        "2,000 AI-qualified prospects/month",
        "Email + LinkedIn automation",
        "Basic Conversion Intelligence",
        "Standard support (24hr response)",
        "ICP setup assistance",
      ],
      cta: "Start Free Trial",
      popular: false,
      savings: "Save $15,000/year",
    },
    {
      name: "Velocity",
      price: "$2,500",
      originalPrice: "$5,000",
      period: "/month",
      description: "Growth-focused agencies ready to scale pipeline",
      features: [
        "5,000 AI-qualified prospects/month",
        "Full 5-channel outreach",
        "Advanced Conversion Intelligence",
        "Priority support + Slack channel",
        "Dedicated success manager",
        "Weekly performance insights",
        "Custom messaging templates",
      ],
      cta: "Claim Your Spot",
      popular: true,
      savings: "Save $30,000/year",
    },
    {
      name: "Dominance",
      price: "$3,750",
      originalPrice: "$7,500",
      period: "/month",
      description: "Agencies building a client acquisition machine",
      features: [
        "Unlimited prospects",
        "All channels + white-label options",
        "Custom AI model training",
        "API access for integrations",
        "Quarterly strategy sessions",
        "Dedicated account team",
        "Custom SLAs & contracts",
      ],
      cta: "Talk to Us",
      popular: false,
      savings: "Save $45,000/year",
    },
  ]

  return (
    <section id="pricing" className="py-20 md:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-6"
        >
          {/* Founding badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 px-4 py-2 text-sm mb-6">
            <Sparkles className="h-4 w-4 text-amber-600" />
            <span className="font-semibold text-amber-800">Founding Member Pricing — 17 of 20 spots left</span>
          </div>
          
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-balance mb-4">
            Lock in 50% off. Forever.
          </h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Founding members keep their rate for life—even when we raise prices. 
            No contracts. Cancel anytime.
          </p>
        </motion.div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mt-12">
          {plans.map((plan, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card
                className={`p-8 relative h-full flex flex-col transition-all duration-300 ${
                  plan.popular 
                    ? "border-2 border-blue-500 shadow-xl shadow-blue-500/10 scale-105" 
                    : "border-gray-200 hover:shadow-lg hover:-translate-y-1"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-1.5 rounded-full text-sm font-semibold shadow-lg flex items-center gap-1">
                    <Star className="h-3.5 w-3.5 fill-current" />
                    Most Popular
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                  <p className="text-muted-foreground text-sm mb-4">{plan.description}</p>
                  
                  {/* Price */}
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-5xl font-bold tracking-tight">{plan.price}</span>
                    <span className="text-muted-foreground text-lg">{plan.period}</span>
                  </div>
                  
                  {/* Original price strikethrough */}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground line-through text-sm">
                      Was {plan.originalPrice}/month
                    </span>
                    <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded">
                      {plan.savings}
                    </span>
                  </div>
                </div>

                <ul className="space-y-3 mb-8 flex-grow">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-start gap-3">
                      <Check className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                      <span className="text-sm leading-relaxed">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className={`w-full shadow-md hover:shadow-lg transition-all h-12 text-base font-semibold ${
                    plan.popular 
                      ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:opacity-90" 
                      : ""
                  }`}
                  variant={plan.popular ? "default" : "outline"}
                  size="lg"
                >
                  {plan.cta}
                  {plan.popular && <ArrowRight className="ml-2 h-4 w-4" />}
                </Button>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* ROI Math - Brunson's bridge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto mt-16 text-center"
        >
          <Card className="p-8 bg-gradient-to-br from-blue-50 to-purple-50 border-blue-100">
            <h3 className="text-xl font-bold mb-4">The ROI Math</h3>
            <p className="text-3xl font-bold text-blue-600 mb-3">
              Close ONE new client → Pay for an entire year
            </p>
            <p className="text-muted-foreground">
              At $2,500/month with a typical agency retainer of $5,000/month, 
              one new client covers more than 2 years of Agency OS.
            </p>
            <p className="mt-4 text-sm font-medium text-gray-700">
              The question isn't "Can I afford Agency OS?"<br/>
              <span className="text-blue-600">The question is "Can I afford NOT to have a system?"</span>
            </p>
          </Card>
        </motion.div>

        {/* Trust signals */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex flex-wrap justify-center gap-x-8 gap-y-3 mt-12 text-sm text-muted-foreground"
        >
          <span>🔒 Australian Privacy Act Compliant</span>
          <span>📱 DNCR Integration Built-In</span>
          <span>💳 Cancel Anytime—No Lock-In</span>
          <span>🇦🇺 Built for Australian Agencies</span>
        </motion.div>
      </div>
    </section>
  )
}
