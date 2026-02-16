import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <Header />
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <Card className="border-border/50 w-full max-w-md">
          <CardHeader>
            <CardTitle>Page not found</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground text-sm">
              The page you are looking for does not exist or has been moved.
            </p>
            <Button variant="outline" size="sm" asChild>
              <Link href="/">Go home</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </>
  );
}
