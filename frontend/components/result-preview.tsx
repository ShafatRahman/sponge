"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { JobResult } from "@/lib/models/job";

interface ResultPreviewProps {
  result: JobResult;
}

export function ResultPreview({ result }: ResultPreviewProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(result.llmsTxt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload() {
    const blob = new Blob([result.llmsTxt], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "llms.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex flex-wrap gap-3">
        <Badge variant="secondary">{result.pagesProcessed} pages processed</Badge>
        {result.pagesFailed > 0 && <Badge variant="destructive">{result.pagesFailed} failed</Badge>}
        <Badge variant="secondary">{result.generationTimeSeconds.toFixed(1)}s</Badge>
        {result.llmCallsMade > 0 && (
          <Badge variant="secondary">{result.llmCallsMade} LLM calls</Badge>
        )}
      </div>

      {/* Content preview */}
      <Card className="code-block border-border/50">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-muted-foreground text-sm font-medium">llms.txt</CardTitle>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleCopy}>
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              Download
            </Button>
          </div>
        </CardHeader>
        <Separator className="opacity-50" />
        <CardContent className="pt-4">
          <pre className="text-foreground/90 max-h-[500px] overflow-auto font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {result.llmsTxt}
          </pre>
        </CardContent>
      </Card>

      {/* llms-full.txt download link */}
      {result.llmsFullTxtUrl && (
        <Card className="border-border/50">
          <CardContent className="flex items-center justify-between py-4">
            <div>
              <p className="font-medium">llms-full.txt</p>
              <p className="text-muted-foreground text-sm">
                Expanded version with full page content
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <a href={result.llmsFullTxtUrl} target="_blank" rel="noopener noreferrer">
                Download
              </a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
