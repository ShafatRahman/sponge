import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    title: "Spec compliant",
    description:
      "Generates llms.txt files that follow the llmstxt.org specification. Structured sections, proper markdown formatting.",
  },
  {
    title: "Two modes",
    description:
      "Standard mode generates an AI-enhanced index. Detailed mode adds full page content for a comprehensive llms-full.txt.",
  },
  {
    title: "Automatic categorization",
    description:
      "Pages are intelligently grouped into Documentation, API Reference, Guides, Blog, and more based on URL patterns.",
  },
  {
    title: "Smart discovery",
    description:
      "Discovers pages via sitemaps, robots.txt, and BFS crawling. Respects rate limits and crawl delays.",
  },
];

export function FeaturesSection() {
  return (
    <section className="border-border/50 border-t px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-8 text-center text-2xl font-semibold tracking-tight">How it works</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {features.map((feature) => (
            <Card
              key={feature.title}
              className="border-border/50 bg-card/50 hover:bg-card transition-colors"
            >
              <CardContent className="pt-6">
                <h3 className="mb-2 font-medium">{feature.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
