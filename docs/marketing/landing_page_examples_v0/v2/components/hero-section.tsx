import { Button } from "@/components/ui/button"
import { Play } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden py-20 md:py-32">
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex flex-col items-center text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-sm mb-8 animate-fade-in">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
            </span>
            <span className="text-muted-foreground font-medium">Powered by Advanced AI</span>
          </div>

          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight text-balance mb-6 max-w-5xl animate-fade-in-up">
            Close more clients without lifting a finger
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground text-balance mb-10 max-w-3xl leading-relaxed animate-fade-in-up">
            The AI-powered platform that finds, qualifies, and books meetings with your perfect clients—while you sleep.
            Built for ambitious marketing agencies ready to scale.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4 mb-16 animate-fade-in-up">
            <Button size="lg" className="text-base px-8 h-12 shadow-lg hover:shadow-xl transition-all">
              Start Free Trial
            </Button>
            <Button size="lg" variant="outline" className="text-base h-12 bg-transparent group">
              <Play className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform" />
              Watch Demo
            </Button>
          </div>

          <div className="w-full max-w-5xl aspect-video rounded-xl border-2 border-border/50 bg-gradient-to-br from-primary/5 via-background to-accent/5 overflow-hidden shadow-2xl animate-fade-in-up group hover:shadow-accent/20 transition-all duration-500">
            <div className="relative w-full h-full flex items-center justify-center">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-accent/10" />
              <div className="absolute inset-0 flex items-center justify-center backdrop-blur-[1px]">
                <div className="h-20 w-20 rounded-full bg-background/90 backdrop-blur-sm flex items-center justify-center shadow-xl border border-border group-hover:scale-110 transition-transform duration-300">
                  <Play className="h-10 w-10 text-primary ml-1" />
                </div>
              </div>
              <img
                src="/modern-ai-dashboard-interface-analytics.jpg"
                alt="Product demo video"
                className="w-full h-full object-cover opacity-40"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
