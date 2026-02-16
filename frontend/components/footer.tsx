import Image from "next/image";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-border/50 mt-auto border-t py-8">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 sm:flex-row sm:justify-between">
        <div className="flex items-center gap-3">
          <Image
            src="/logo-icon.svg"
            alt="Profound"
            width={20}
            height={20}
            className="h-4 w-auto opacity-50"
          />
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
        </div>
        <p className="text-muted-foreground text-sm">Profound</p>
      </div>
    </footer>
  );
}
