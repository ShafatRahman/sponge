import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-border/50 mt-auto border-t py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 sm:flex-row sm:justify-between">
        <p className="text-muted-foreground text-sm">
          Built with the{" "}
          <Link
            href="https://llmstxt.org"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground underline underline-offset-4 transition-colors"
          >
            llms.txt spec
          </Link>
        </p>
        <p className="text-muted-foreground text-sm">sponge</p>
      </div>
    </footer>
  );
}
