import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Check } from "lucide-react"

export function PricingSection() {
  const plans = [
    {
      name: "Starter",
      price: "$299",
      description: "For agencies testing AI outreach",
      features: [
        "2,000 AI-qualified prospects/mo",
        "Automated email sequences",
        "Basic CRM integration",
        "Performance analytics",
        "Email & chat support",
      ],
      cta: "Start 14-Day Trial",
      popular: false,
    },
    {
      name: "Growth",
      price: "$799",
      description: "For agencies ready to scale fast",
      features: [
        "10,000 AI-qualified prospects/mo",
        "Multi-channel outreach (email + LinkedIn)",
        "Advanced AI personalization",
        "Real-time analytics dashboard",
        "Priority support + Slack channel",
        "Custom integrations",
        "Dedicated success manager",
      ],
      cta: "Start 14-Day Trial",
      popular: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      description: "For agencies dominating their market",
      features: [
        "Unlimited prospects & outreach",
        "White-label platform",
        "Custom AI model training",
        "Advanced API access",
        "Dedicated account team",
        "24/7 priority support",
        "Custom SLAs & contracts",
      ],
      cta: "Talk to Sales",
      popular: false,
    },
  ]

  return (
    <section id="pricing" className="py-20 md:py-32 bg-gradient-to-b from-background to-secondary/30">
      <div className="container mx-auto px-4 md:px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-balance mb-4">
            Pricing that scales with you
          </h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Start free for 14 days. No credit card required. Cancel anytime.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <Card
              key={index}
              className={`p-8 relative transition-all duration-300 ${plan.popular ? "border-2 border-primary shadow-xl scale-105 hover:shadow-2xl" : "hover:shadow-lg hover:-translate-y-1"}`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground px-6 py-1.5 rounded-full text-sm font-semibold shadow-lg">
                  Most Popular
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <p className="text-muted-foreground text-sm mb-4">{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold tracking-tight">{plan.price}</span>
                  {plan.price !== "Custom" && <span className="text-muted-foreground text-lg">/mo</span>}
                </div>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-start gap-3">
                    <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                    <span className="text-sm leading-relaxed">{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                className="w-full shadow-md hover:shadow-lg transition-all"
                variant={plan.popular ? "default" : "outline"}
                size="lg"
              >
                {plan.cta}
              </Button>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
