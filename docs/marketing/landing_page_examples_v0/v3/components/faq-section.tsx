"use client"

import { motion } from "framer-motion"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

// Wiebe's objection handling - answer in customer's voice
const faqs = [
  {
    question: "I've tried AI outbound tools before. They didn't work.",
    answer: "Most AI tools are built for US enterprise sales. They don't understand Australian compliance (ACMA, DNCR), Aussie business culture, or agency sales cycles. We're different: built from the ground up for Australian agencies. Also—most tools are email-only. We're 5 channels because the best channel varies by industry and prospect.",
  },
  {
    question: "What if my emails get flagged as spam?",
    answer: "We use dedicated infrastructure with built-in deliverability management: warm-up protocols, domain rotation, send-time optimization. But more importantly—our AI writes emails that sound human because they're based on YOUR brand voice, not generic templates. No templates = no spam triggers.",
  },
  {
    question: "Do I need to hire someone to manage this?",
    answer: "No. The whole point is that this runs while you focus on client work. After initial setup (which we do WITH you), it's 2-3 hours/week to review leads and respond to warm replies. Your calendar fills; you just show up and close.",
  },
  {
    question: "What happens after the founding period?",
    answer: "Your rate is locked forever. Literally. Even when pricing goes to $5,000+ for new customers, you stay at your founding rate. The only thing that changes is the feature set—which expands (and you get access to everything new).",
  },
  {
    question: "Is my data safe?",
    answer: "Yes. We're Australian Privacy Act compliant, have DNCR integration built-in, and have SOC 2 Type 2 on our Q2 2025 roadmap. You own your data. Always. We never sell or share prospect information with other clients.",
  },
  {
    question: "How is this different from hiring an SDR?",
    answer: "An SDR costs $60-80K/year base + commission. They work 40 hours/week, take holidays, and leave. Agency OS works 24/7, across 5 channels simultaneously, for a fraction of the cost. And it gets smarter over time—SDRs need to be retrained with every new hire.",
  },
  {
    question: "What if I want to cancel?",
    answer: "Cancel anytime. No lock-in contracts. No cancellation fees. We think if you have to trap customers, your product isn't good enough. We'd rather earn your business every month.",
  },
  {
    question: "How quickly can I see results?",
    answer: "Most agencies have their first campaign live within 48 hours of starting. First booked meetings typically come within 2 weeks. But remember—this is a system, not a sprint. The real power comes from compounding: your outreach gets smarter every week.",
  },
]

export function FAQSection() {
  return (
    <section className="py-20 md:py-28 bg-gray-50">
      <div className="max-w-3xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Questions? We've got answers.
          </h2>
          <p className="text-muted-foreground">
            Still not sure? Here's what other agency owners asked before joining.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <Accordion type="single" collapsible className="w-full space-y-4">
            {faqs.map((faq, index) => (
              <AccordionItem
                key={index}
                value={`item-${index}`}
                className="bg-white rounded-lg border border-gray-200 px-6 data-[state=open]:shadow-md transition-all"
              >
                <AccordionTrigger className="text-left font-semibold py-5 hover:no-underline">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground pb-5 leading-relaxed">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>

        {/* Still have questions CTA */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-center mt-12"
        >
          <p className="text-muted-foreground">
            Still have questions?{" "}
            <a href="mailto:hello@agencyos.ai" className="text-blue-600 hover:underline font-medium">
              Email us directly
            </a>
            {" "}— we reply within 24 hours.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
