import { UrlInputForm } from "@/components/url-input-form";

export function HeroSection() {
  return (
    <section className="flex flex-col items-center justify-center px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
          Generate your <span className="accent-text">llms.txt</span>
        </h1>
        <p className="text-muted-foreground mx-auto mt-4 max-w-xl text-lg">
          Create a spec-compliant llms.txt file for any website. Help AI systems understand your
          content structure in seconds.
        </p>
      </div>

      <div className="mt-10 w-full">
        <UrlInputForm />
      </div>
    </section>
  );
}
