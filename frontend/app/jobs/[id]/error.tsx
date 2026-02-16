"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

/**
 * Error boundary for the job detail page.
 * Catches errors from useJobStream or rendering and shows a clean fallback.
 */
export default function JobError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <>
      <Header />
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <Card className="border-destructive/50 w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load job</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground text-sm">
              We were unable to load the generation results. The job may still be running in the
              background.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" size="sm" onClick={reset}>
                Retry
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/">Start over</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </>
  );
}
