"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import Link from "next/link";

function useAuthError(): string | null {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check for error in URL hash (OAuth error flow)
    const hash = window.location.hash;
    if (hash.includes("error")) {
      const params = new URLSearchParams(hash.substring(1));
      const desc = params.get("error_description") ?? "Authentication failed. Please try again.";
      // Use a microtask to avoid synchronous setState in effect
      queueMicrotask(() => setError(desc));
    }
  }, []);

  return error;
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const hashError = useAuthError();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const supabase = getSupabaseClient();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        router.push("/");
      }
    });

    // Timeout: if no auth event fires within 10s, show error
    const timeout = setTimeout(() => {
      setTimedOut(true);
    }, 10000);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, [router]);

  const error = hashError ?? (timedOut ? "Authentication timed out. Please try again." : null);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-destructive text-sm">{error}</p>
        <Button variant="outline" size="sm" asChild>
          <Link href="/auth/login">Back to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Completing sign in...</p>
    </div>
  );
}
