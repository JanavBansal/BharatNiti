"use client";

import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <div className="w-16 h-16 rounded-full bg-[var(--destructive)]/10 flex items-center justify-center mb-6">
        <AlertTriangle className="w-8 h-8 text-[var(--destructive)]" />
      </div>
      <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
      <p className="text-[var(--muted-foreground)] mb-6 max-w-md">
        An unexpected error occurred. Please try again or go back to the home page.
      </p>
      <button
        onClick={reset}
        className="px-5 py-2.5 text-sm font-medium rounded-lg bg-gradient-to-r from-[var(--gradient-start)] to-[var(--gradient-end)] text-white hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-150"
      >
        Try again
      </button>
    </main>
  );
}
