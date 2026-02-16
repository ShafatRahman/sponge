"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ModeToggle } from "@/components/mode-toggle";
import { getJobsService } from "@/lib/api/jobs-service";
import { ApiError } from "@/lib/models/errors";
import { normalizeUrl, isValidUrl } from "@/lib/utils/url-utils";
import type { JobMode } from "@/lib/models/job";

export function UrlInputForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<JobMode>("default");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const normalized = normalizeUrl(url);
    if (!isValidUrl(normalized)) {
      setError("Please enter a valid URL (e.g. example.com)");
      return;
    }

    setIsLoading(true);
    try {
      const service = getJobsService();
      const job = await service.create({ url: normalized, mode });
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setError(message);
      toast.error(message);
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-xl space-y-4">
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder="Enter a website URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="border-border/50 bg-card h-12 flex-1 text-base"
          disabled={isLoading}
          autoFocus
        />
        <Button type="submit" size="lg" disabled={isLoading || !url.trim()} className="h-12 px-8">
          {isLoading ? "Generating..." : "Generate"}
        </Button>
      </div>

      <ModeToggle mode={mode} onModeChange={setMode} disabled={isLoading} />

      {error && <p className="text-destructive text-center text-sm">{error}</p>}
    </form>
  );
}
