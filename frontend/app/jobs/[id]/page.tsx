"use client";

import { use, useEffect, useRef } from "react";
import { toast } from "sonner";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { GenerationProgress } from "@/components/generation-progress";
import { ResultPreview } from "@/components/result-preview";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useJobStream } from "@/lib/hooks/use-job-stream";
import { extractDomain } from "@/lib/utils/url-utils";
import Link from "next/link";

export default function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  const { data, error, isTimedOut } = useJobStream(jobId);
  const toastFiredRef = useRef(false);

  const isTerminal =
    data?.status === "completed" || data?.status === "failed" || data?.status === "cancelled";

  // Fire a toast once when an error or timeout occurs
  useEffect(() => {
    if (toastFiredRef.current) return;

    if (isTimedOut) {
      toast.warning("Job stalled", {
        description: "No progress for several minutes. A required API key may be missing.",
      });
      toastFiredRef.current = true;
    } else if (error || data?.status === "failed") {
      toast.error("Generation failed", {
        description: data?.error ?? error ?? "Something went wrong.",
      });
      toastFiredRef.current = true;
    }
  }, [isTimedOut, error, data?.status, data?.error]);

  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12">
        <div className="mx-auto max-w-4xl space-y-8">
          {/* Job header -- always visible */}
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">
              {data?.result ? "Generation complete" : "Generating llms.txt"}
            </h1>
            {data?.progress?.currentUrl && (
              <p className="text-muted-foreground text-sm">
                {extractDomain(data.progress.currentUrl)}
              </p>
            )}
          </div>

          {/* Timeout state */}
          {isTimedOut && (
            <Card className="border-warning/50">
              <CardHeader>
                <CardTitle className="text-warning">Job stalled</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  This job has not made progress for several minutes. This can happen when a
                  required API key is missing or an external service is unavailable.
                </p>
                <Button variant="outline" size="sm" className="mt-4" asChild>
                  <Link href="/">Try again</Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Error state */}
          {!isTimedOut && (error || data?.status === "failed") && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive">Generation failed</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">{data?.error ?? error}</p>
                <Button variant="outline" size="sm" className="mt-4" asChild>
                  <Link href="/">Try again</Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Progress -- show immediately, even before first SSE event */}
          {!isTerminal && !isTimedOut && !(error && !data) && (
            <Card className="border-border/50">
              <CardContent className="pt-6">
                <GenerationProgress
                  status={data?.status ?? "pending"}
                  progress={data?.progress ?? null}
                />
              </CardContent>
            </Card>
          )}

          {/* Result */}
          {data?.result && <ResultPreview result={data.result} />}

          {/* Back link */}
          {isTerminal && (
            <div className="text-center">
              <Button asChild>
                <Link href="/">Generate another</Link>
              </Button>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
