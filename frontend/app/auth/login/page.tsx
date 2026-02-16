"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { AuthService } from "@/lib/api/auth-service";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const auth = new AuthService();
    const result = isLogin
      ? await auth.signInWithEmail(email, password)
      : await auth.signUp(email, password);

    setIsLoading(false);

    if (result.error) {
      setError(result.error);
    } else {
      router.push("/");
    }
  }

  async function handleOAuth(provider: "google" | "github") {
    const auth = new AuthService();
    await auth.signInWithOAuth(provider);
  }

  return (
    <>
      <Header />
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <Card className="border-border/50 w-full max-w-sm">
          <CardHeader className="text-center">
            <CardTitle>{isLogin ? "Sign in" : "Create account"}</CardTitle>
            <p className="text-muted-foreground text-sm">
              {isLogin
                ? "Sign in to save your generated files"
                : "Create an account for higher rate limits"}
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Button variant="outline" onClick={() => handleOAuth("github")} className="w-full">
                Continue with GitHub
              </Button>
              <Button variant="outline" onClick={() => handleOAuth("google")} className="w-full">
                Continue with Google
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <Separator className="flex-1" />
              <span className="text-muted-foreground text-xs">or</span>
              <Separator className="flex-1" />
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
              {error && <p className="text-destructive text-sm">{error}</p>}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Loading..." : isLogin ? "Sign in" : "Create account"}
              </Button>
            </form>

            <p className="text-muted-foreground text-center text-sm">
              {isLogin ? "No account?" : "Already have one?"}{" "}
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-primary underline-offset-4 hover:underline"
              >
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </p>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </>
  );
}
