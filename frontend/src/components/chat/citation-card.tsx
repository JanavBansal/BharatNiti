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
      aria-expanded={expanded}
      aria-label={`Toggle citation for Section ${citation.section_number}`}
      className="w-full text-left border border-[var(--border)] border-l-2 border-l-[var(--primary)] rounded-lg p-3 hover:bg-[var(--muted)] transition-all duration-200"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <BookOpen className="w-4 h-4 text-[var(--primary)] flex-shrink-0" />
          <span className="text-sm font-medium truncate">
            Section {citation.section_number}
          </span>
          {citation.section_title && (
            <span className="text-xs text-[var(--muted-foreground)] truncate hidden sm:inline">
              — {citation.section_title}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-[var(--muted-foreground)] flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[var(--muted-foreground)] flex-shrink-0" />
        )}
      </div>
      {expanded && (
        <div className="mt-2 text-xs text-[var(--muted-foreground)] border-t border-[var(--border)] pt-2 animate-fade-in-up line-clamp-6">
          {citation.excerpt}
        </div>
      )}
    </button>
  );
}
