import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Quote, Star } from "lucide-react"

export function TestimonialsSection() {
  const testimonials = [
    {
      quote:
        "AgentFlow booked 47 qualified meetings in our first month. The AI prospecting is scary accurate—it's like having a team of SDRs working 24/7.",
      author: "Sarah Johnson",
      title: "Founder & CEO",
      company: "GrowthLab Marketing",
      avatar: "/professional-woman-headshot.png",
      initials: "SJ",
      rating: 5,
    },
    {
      quote:
        "We closed $280K in new business within 90 days. The ROI is insane and the time savings let us focus on what we do best—delivering results for clients.",
      author: "Michael Chen",
      title: "Managing Director",
      company: "Digital Dynamics",
      avatar: "/professional-man-headshot.png",
      initials: "MC",
      rating: 5,
    },
    {
      quote:
        "Replaced 3 full-time SDRs and actually improved our pipeline quality. The AI understands our ICP better than most humans. Game-changing for our agency.",
      author: "Emily Rodriguez",
      title: "VP of Growth",
      company: "Catalyst Agency",
      avatar: "/professional-woman-portrait.png",
      initials: "ER",
      rating: 5,
    },
  ]

  return (
    <section id="testimonials" className="py-20 md:py-32 bg-secondary/30">
      <div className="container mx-auto px-4 md:px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-balance mb-4">
            Real agencies. Real results.
          </h2>
          <p className="text-lg text-muted-foreground text-balance max-w-2xl mx-auto">
            Join hundreds of agencies already winning with AI-powered outreach
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <Card key={index} className="p-8 relative hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <Quote className="h-10 w-10 text-accent/20 mb-4" />
              <div className="flex gap-1 mb-4">
                {Array.from({ length: testimonial.rating }).map((_, i) => (
                  <Star key={i} className="h-4 w-4 fill-accent text-accent" />
                ))}
              </div>
              <blockquote className="text-foreground mb-6 leading-relaxed font-medium">{testimonial.quote}</blockquote>
              <div className="flex items-center gap-4">
                <Avatar className="h-12 w-12 border-2 border-primary/10">
                  <AvatarImage src={testimonial.avatar || "/placeholder.svg"} alt={testimonial.author} />
                  <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                    {testimonial.initials}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="font-semibold">{testimonial.author}</div>
                  <div className="text-sm text-muted-foreground">
                    {testimonial.title}, {testimonial.company}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
