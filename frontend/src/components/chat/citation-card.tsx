"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import type { Citation } from "@/lib/types";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="w-full text-left border border-[var(--border)] rounded-lg p-3 hover:bg-[var(--muted)] transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[var(--primary)]" />
          <span className="text-sm font-medium">
            Section {citation.section_number}
          </span>
          {citation.section_title && (
            <span className="text-xs text-[var(--muted-foreground)]">
              — {citation.section_title}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-[var(--muted-foreground)]" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[var(--muted-foreground)]" />
        )}
      </div>
      {expanded && (
        <div className="mt-2 text-xs text-[var(--muted-foreground)] border-t border-[var(--border)] pt-2">
          {citation.excerpt}
        </div>
      )}
    </button>
  );
}
