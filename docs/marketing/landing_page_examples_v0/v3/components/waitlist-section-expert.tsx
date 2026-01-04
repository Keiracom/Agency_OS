"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Check, ArrowRight, Shield, Phone, Lock, MapPin } from "lucide-react"
import { motion } from "framer-motion"

export function WaitlistSection() {
  const [email, setEmail] = useState("")
  const [company, setCompany] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log("[Waitlist submission]:", { email, company })
    setSubmitted(true)
  }

  return (
    <section className="py-20 md:py-32 bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 text-white relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          
          {/* Left: Godin's enrollment copy */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
              20 agencies will build the future of agency growth.
            </h2>
            <p className="text-xl text-blue-100 mb-6">
              Will you be one of them?
            </p>
            <p className="text-gray-300 leading-relaxed mb-8">
              Most agencies will wait. Wait until it's proven. Wait until everyone has it. 
              Wait until competitive advantage disappears.
              <br/><br/>
              <span className="text-white font-medium">
                The agencies that win don't wait. They move first.
              </span>
            </p>

            {/* What founders get */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg mb-3">Founding members get:</h3>
              <div className="grid gap-3">
                {[
                  "50% off locked in forever",
                  "Direct line to product team",
                  "White-glove onboarding (done with you)",
                  "Founding Member badge & recognition",
                ].map((benefit, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Check className="h-3 w-3 text-green-400" />
                    </div>
                    <span className="text-gray-200">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Right: Form */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <Card className="p-8 bg-white text-gray-900 shadow-2xl">
              {!submitted ? (
                <>
                  <div className="text-center mb-6">
                    <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 border border-amber-200 px-4 py-2 text-sm mb-4">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
                      </span>
                      <span className="font-semibold text-amber-800">17 of 20 spots remaining</span>
                    </div>
                    <h3 className="text-2xl font-bold mb-2">
                      Claim your founding spot
                    </h3>
                    <p className="text-muted-foreground text-sm">
                      Start your 14-day free trial. No credit card required.
                    </p>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <Input
                        type="email"
                        placeholder="your.email@agency.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="h-12 text-base"
                      />
                    </div>
                    <div>
                      <Input
                        type="text"
                        placeholder="Your Agency Name"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        required
                        className="h-12 text-base"
                      />
                    </div>
                    <Button
                      type="submit"
                      size="lg"
                      className="w-full h-12 text-base font-semibold bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 shadow-lg"
                    >
                      Claim Your Founding Spot
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </form>

                  {/* Trust signals */}
                  <div className="mt-6 pt-6 border-t border-gray-100">
                    <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-green-500" />
                        <span>Australian Privacy Compliant</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-blue-500" />
                        <span>DNCR Integrated</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Lock className="h-4 w-4 text-purple-500" />
                        <span>Cancel Anytime</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-amber-500" />
                        <span>Built in Australia</span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
                    <Check className="h-10 w-10 text-green-600" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2">You're in!</h3>
                  <p className="text-muted-foreground mb-4">
                    Check your inbox at <span className="font-semibold text-gray-900">{email}</span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    We'll send your access details within 24 hours. Welcome to the founding team.
                  </p>
                </div>
              )}
            </Card>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
