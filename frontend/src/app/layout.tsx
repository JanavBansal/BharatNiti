import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "caAI — Indian Tax Law Assistant",
  description:
    "AI-powered research assistant for Indian tax law. Get cited answers from the Income Tax Act, GST Act, and more.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <nav className="border-b border-[var(--border)] px-6 py-3 flex items-center justify-between">
          <a href="/" className="text-xl font-bold text-[var(--primary)]">
            caAI
          </a>
          <div className="flex gap-4 text-sm">
            <a
              href="/chat"
              className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
            >
              Ask a Question
            </a>
            <a
              href="/rates"
              className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
            >
              Rate Lookup
            </a>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
