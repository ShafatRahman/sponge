"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { toast } from "sonner";
import Link from "next/link";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/**
 * Global error boundary for the Next.js App Router.
 * Catches unhandled React errors and renders a user-friendly fallback
 * instead of a blank page or raw error output.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
    toast.error("Something went wrong", {
      description: "An unexpected error occurred. Please try again.",
    });
  }, [error]);

  return (
    <>
      <Header />
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <Card className="border-destructive/50 w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Something went wrong</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground text-sm">
              An unexpected error occurred. This has been logged and we will look into it.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" size="sm" onClick={reset}>
                Try again
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/">Go home</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </>
  );
}
