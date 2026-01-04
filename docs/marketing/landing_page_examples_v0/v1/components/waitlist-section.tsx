"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Check, Sparkles } from "lucide-react"

export function WaitlistSection() {
  const [email, setEmail] = useState("")
  const [company, setCompany] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log("[v0] Waitlist submission:", { email, company })
    setSubmitted(true)
  }

  return (
    <section className="py-20 md:py-32 bg-gradient-to-br from-primary via-primary to-primary/90 text-primary-foreground relative overflow-hidden">
      <div className="absolute inset-0 bg-grid-white/[0.05] bg-[size:32px_32px]" />
      <div className="absolute inset-0 bg-gradient-to-t from-primary/50 to-transparent" />

      <div className="container mx-auto px-4 md:px-6 relative">
        <Card className="max-w-3xl mx-auto p-8 md:p-12 bg-background text-foreground shadow-2xl border-2 border-border/50">
          {!submitted ? (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
                <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-balance mb-4">
                  Get exclusive early access
                </h2>
                <p className="text-lg text-muted-foreground text-balance">
                  Join 800+ agencies already on the list. Be first to access new AI features and get priority onboarding
                  support.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
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
                </div>
                <Button
                  type="submit"
                  size="lg"
                  className="w-full h-12 text-base font-semibold shadow-lg hover:shadow-xl transition-all"
                >
                  Claim Your Spot
                </Button>
                <p className="text-xs text-center text-muted-foreground">
                  No spam, ever. Unsubscribe anytime. Read our Privacy Policy.
                </p>
              </form>
            </>
          ) : (
            <div className="text-center py-8">
              <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6 animate-fade-in">
                <Check className="h-10 w-10 text-primary" />
              </div>
              <h3 className="text-3xl font-bold mb-3">Welcome to the future!</h3>
              <p className="text-muted-foreground text-lg mb-6">
                Check your inbox at <span className="font-semibold text-foreground">{email}</span> for next steps.
              </p>
              <p className="text-sm text-muted-foreground">We'll send you early access details within 24 hours.</p>
            </div>
          )}
        </Card>
      </div>
    </section>
  )
}
