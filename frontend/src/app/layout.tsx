import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NavBar } from "@/components/nav-bar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "BharatNiti — Indian Tax Law Assistant",
  description:
    "AI-powered research assistant for Indian tax law. Get cited answers from the Income Tax Act, GST Act, and more.",
  openGraph: {
    title: "BharatNiti — Indian Tax Law Assistant",
    description:
      "Get instant, cited answers on Indian tax law. Income Tax Act, GST, TDS rates, deductions and more.",
    siteName: "BharatNiti",
    type: "website",
    locale: "en_IN",
  },
  twitter: {
    card: "summary_large_image",
    title: "BharatNiti — Indian Tax Law Assistant",
    description:
      "AI-powered research assistant for Indian tax law with citations.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.className}>
      <body className="min-h-screen antialiased">
        <a href="#main-content" className="skip-to-content">
          Skip to main content
        </a>
        <NavBar />
        <div id="main-content">{children}</div>
      </body>
    </html>
  );
}
