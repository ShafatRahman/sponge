"use client";

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="border-border/50 bg-background/80 sticky top-0 z-50 border-b backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/logo-wordmark.svg"
            alt="Profound"
            width={120}
            height={20}
            className="h-5 w-auto"
            priority
          />
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="https://llmstxt.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            Spec
          </Link>
          <Link
            href="https://github.com/ShafatRahman/sponge"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            GitHub
          </Link>
          <Button size="sm" asChild>
            <Link href="/auth/login">Sign in</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
