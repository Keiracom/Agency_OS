export function LogosSection() {
  const logos = [
    { name: "WebFlow", width: 120 },
    { name: "Notion", width: 100 },
    { name: "Figma", width: 90 },
    { name: "Slack", width: 110 },
    { name: "Airtable", width: 120 },
    { name: "Monday", width: 110 },
  ]

  return (
    <section className="py-16 border-y border-border/50 bg-secondary/20">
      <div className="container mx-auto px-4 md:px-6">
        <p className="text-center text-sm font-medium text-muted-foreground mb-10 tracking-wide uppercase">
          Trusted by 500+ agencies across 40+ countries
        </p>
        <div className="flex flex-wrap items-center justify-center gap-12 md:gap-16">
          {logos.map((logo) => (
            <div
              key={logo.name}
              className="h-8 flex items-center justify-center opacity-40 hover:opacity-100 transition-all duration-300"
              style={{ width: logo.width }}
            >
              <div className="text-lg font-bold text-foreground tracking-tight">{logo.name}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
