"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Target, Zap, BarChart3, Users } from "lucide-react"

export function ProductDemo() {
  const [activeTab, setActiveTab] = useState("prospecting")

  const features = [
    {
      id: "prospecting",
      label: "AI Prospecting",
      icon: Target,
      title: "Find Your Perfect Clients Automatically",
      description:
        "Our AI scans millions of companies daily, identifying perfect-fit prospects based on your ideal customer profile. No more cold calling random lists—only qualified leads that actually convert.",
      stats: [
        { label: "Companies Scanned", value: "15M+" },
        { label: "Match Accuracy", value: "96%" },
        { label: "Time Saved", value: "25hrs/wk" },
      ],
    },
    {
      id: "outreach",
      label: "Smart Outreach",
      icon: Zap,
      title: "Personalized Messages That Convert",
      description:
        "Generate hyper-personalized outreach at scale. Our AI researches each prospect and crafts compelling messages that sound human, not robotic. Watch your response rates soar.",
      stats: [
        { label: "Response Rate", value: "48%" },
        { label: "Messages Sent", value: "100K+" },
        { label: "Meetings Booked", value: "42%" },
      ],
    },
    {
      id: "analytics",
      label: "Analytics",
      icon: BarChart3,
      title: "Know What's Working in Real-Time",
      description:
        "Track every interaction, optimize every campaign. Get instant insights into what messages resonate, which prospects engage, and where to focus your energy for maximum ROI.",
      stats: [
        { label: "Pipeline Value", value: "$3.2M" },
        { label: "Win Rate", value: "32%" },
        { label: "Average ROI", value: "580%" },
      ],
    },
    {
      id: "enrichment",
      label: "Data Intelligence",
      icon: Users,
      title: "Complete Intel on Every Prospect",
      description:
        "Automatically gather verified contact details, company tech stack, funding status, and decision-maker insights. Enter every conversation armed with the information you need to close.",
      stats: [
        { label: "Data Points", value: "75+" },
        { label: "Email Accuracy", value: "98%" },
        { label: "Updated Daily", value: "Yes" },
      ],
    },
  ]

  return (
    <section id="product" className="py-20 md:py-32 bg-gradient-to-b from-background to-secondary/20">
      <div className="container mx-auto px-4 md:px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-balance mb-4">
            The complete client acquisition engine
          </h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Everything you need to transform cold outreach into closed deals
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-3xl mx-auto grid-cols-2 md:grid-cols-4 h-auto mb-12 bg-muted/50 p-1">
            {features.map((feature) => (
              <TabsTrigger
                key={feature.id}
                value={feature.id}
                className="flex flex-col items-center gap-2 py-4 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-md transition-all"
              >
                <feature.icon className="h-5 w-5" />
                <span className="text-xs md:text-sm font-medium">{feature.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {features.map((feature) => (
            <TabsContent key={feature.id} value={feature.id} className="mt-0 animate-fade-in">
              <Card className="p-8 md:p-12 shadow-lg hover:shadow-xl transition-shadow duration-300">
                <div className="grid md:grid-cols-2 gap-12 items-center">
                  <div>
                    <h3 className="text-2xl md:text-3xl font-bold mb-4 text-balance">{feature.title}</h3>
                    <p className="text-muted-foreground text-lg mb-8 leading-relaxed">{feature.description}</p>
                    <div className="grid grid-cols-3 gap-6">
                      {feature.stats.map((stat) => (
                        <div key={stat.label}>
                          <div className="text-2xl md:text-3xl font-bold text-primary mb-1">{stat.value}</div>
                          <div className="text-xs text-muted-foreground leading-tight">{stat.label}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="aspect-video rounded-lg bg-gradient-to-br from-primary/10 to-accent/10 border border-border overflow-hidden shadow-md">
                    <img
                      src={`/.jpg?height=400&width=600&query=${feature.label.toLowerCase()}+dashboard+interface+data`}
                      alt={`${feature.label} interface`}
                      className="w-full h-full object-cover opacity-80"
                    />
                  </div>
                </div>
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </section>
  )
}
