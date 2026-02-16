"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AuthService } from "@/lib/api/auth-service";

export function Header() {
  const router = useRouter();
  const [isSignedIn, setIsSignedIn] = useState(false);

  useEffect(() => {
    const auth = new AuthService();

    auth.getSession().then((session) => {
      setIsSignedIn(!!session);
    });

    const subscription = auth.onAuthStateChange((session) => {
      setIsSignedIn(!!session);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  async function handleSignOut() {
    const auth = new AuthService();
    await auth.signOut();
    router.push("/");
  }

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
          {isSignedIn ? (
            <Button size="sm" variant="outline" onClick={handleSignOut}>
              Sign out
            </Button>
          ) : (
            <Button size="sm" asChild>
              <Link href="/auth/login">Sign in</Link>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
