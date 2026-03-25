"use client";

import type { ChatMessage } from "@/lib/types";
import { CitationCard } from "./citation-card";
import { ConfidenceBadge } from "./confidence-badge";
import { User, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center flex-shrink-0 mt-1">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`rounded-2xl px-5 py-4 ${
            isUser
              ? "bg-[var(--primary)] text-white"
              : "bg-[var(--muted)] text-[var(--foreground)]"
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Tables
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3 rounded-lg border border-[var(--border)] -mx-1">
                      <table className="w-full text-xs border-collapse whitespace-nowrap">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-[var(--accent)]">
                      {children}
                    </thead>
                  ),
                  th: ({ children }) => (
                    <th className="px-2 py-1.5 text-left text-xs font-semibold border-b border-[var(--border)]">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-2 py-1.5 text-xs border-b border-[var(--border)]">
                      {children}
                    </td>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-[var(--accent)]/50 transition-colors">
                      {children}
                    </tr>
                  ),
                  // Typography
                  p: ({ children }) => (
                    <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-[var(--foreground)]">{children}</strong>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-base font-bold mt-4 mb-2">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-sm font-bold mt-3 mb-1">{children}</h3>
                  ),
                  // Lists
                  ul: ({ children }) => (
                    <ul className="list-disc pl-4 space-y-1 my-2 text-sm">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-4 space-y-1 my-2 text-sm">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-sm leading-relaxed">{children}</li>
                  ),
                  // Horizontal rule
                  hr: () => (
                    <hr className="my-3 border-[var(--border)]" />
                  ),
                  // Code (for section numbers etc.)
                  code: ({ children }) => (
                    <code className="bg-[var(--accent)] px-1.5 py-0.5 rounded text-xs font-mono">
                      {children}
                    </code>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
          {message.isStreaming && (
            <span className="inline-block w-2 h-4 bg-current animate-pulse ml-0.5" />
          )}
        </div>

        {/* Metadata row: confidence + assessment year */}
        {!isUser && message.confidence && (
          <div className="flex items-center gap-2 mt-2">
            <ConfidenceBadge confidence={message.confidence} />
            {message.assessment_year && (
              <span className="text-xs text-[var(--muted-foreground)]">
                AY {message.assessment_year}
              </span>
            )}
          </div>
        )}

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <span className="text-xs font-medium text-[var(--muted-foreground)]">
              Sources ({message.citations.length})
            </span>
            {message.citations.map((citation, i) => (
              <CitationCard key={i} citation={citation} index={i} />
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-[var(--muted)] flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4 text-[var(--muted-foreground)]" />
        </div>
      )}
    </div>
  );
}
