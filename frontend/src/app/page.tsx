import { Search, BookOpen, Shield, Zap, Scale, Calculator } from "lucide-react";

const SUGGESTED_QUESTIONS = [
  "What deductions are available under Section 80C?",
  "What is the TDS rate on professional fees?",
  "How is capital gains tax calculated on property sale?",
  "What are the GST rates for restaurant services?",
  "What is the income tax slab for AY 2025-26 under new regime?",
  "When is advance tax due for self-employed individuals?",
];

const FEATURES = [
  {
    icon: BookOpen,
    title: "Grounded in Law",
    description: "Answers cite specific sections from the Income Tax Act and GST Act",
  },
  {
    icon: Shield,
    title: "Confidence Scoring",
    description: "Every answer rated HIGH/MEDIUM/LOW so you know when to consult a CA",
  },
  {
    icon: Zap,
    title: "Instant Rate Lookup",
    description: "TDS rates, GST rates, and income tax slabs from structured data",
  },
  {
    icon: Scale,
    title: "Current Law",
    description: "Based on the latest amendments and CBDT circulars",
  },
  {
    icon: Calculator,
    title: "Tax Calculator",
    description: "Calculate income tax liability under old and new regimes",
  },
  {
    icon: Search,
    title: "Smart Search",
    description: "Understands tax terminology and finds the right provisions",
  },
];

export default function Home() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Indian Tax Law, <span className="text-[var(--primary)]">Answered</span>
        </h1>
        <p className="text-lg text-[var(--muted-foreground)] max-w-2xl mx-auto">
          Ask questions about the Income Tax Act, GST, TDS rates, and more. Get
          cited answers grounded in actual legislation.
        </p>
      </div>

      {/* Search Bar */}
      <div className="mb-12">
        <a href="/chat">
          <div className="flex items-center gap-3 border border-[var(--border)] rounded-xl px-5 py-4 hover:border-[var(--primary)] transition-colors cursor-pointer bg-[var(--card)]">
            <Search className="w-5 h-5 text-[var(--muted-foreground)]" />
            <span className="text-[var(--muted-foreground)]">
              Ask a tax law question...
            </span>
          </div>
        </a>
      </div>

      {/* Suggested Questions */}
      <div className="mb-16">
        <h2 className="text-sm font-medium text-[var(--muted-foreground)] mb-3">
          Popular Questions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {SUGGESTED_QUESTIONS.map((q, i) => (
            <a
              key={i}
              href={`/chat?q=${encodeURIComponent(q)}`}
              className="text-sm px-4 py-3 rounded-lg border border-[var(--border)] hover:bg-[var(--accent)] hover:border-[var(--primary)] transition-colors bg-[var(--card)]"
            >
              {q}
            </a>
          ))}
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {FEATURES.map((feature, i) => (
          <div
            key={i}
            className="p-5 rounded-xl border border-[var(--border)] bg-[var(--card)]"
          >
            <feature.icon className="w-8 h-8 text-[var(--primary)] mb-3" />
            <h3 className="font-semibold mb-1">{feature.title}</h3>
            <p className="text-sm text-[var(--muted-foreground)]">
              {feature.description}
            </p>
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="mt-16 text-center text-xs text-[var(--muted-foreground)] border-t border-[var(--border)] pt-6">
        caAI is a tax law research tool, not a substitute for professional tax
        advice. Always consult a Chartered Accountant for financial decisions.
      </div>
    </main>
  );
}
