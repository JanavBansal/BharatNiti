"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, Citation } from "@/lib/types";
import { askQuestion } from "@/lib/api/client";

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return generateId();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (question: string) => {
    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: question,
    };

    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsLoading(true);

    try {
      await askQuestion(
        question,
        undefined,
        // onToken
        (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
              };
            }
            return updated;
          });
        },
        // onMetadata
        (metadata) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                citations: metadata.citations,
                confidence: metadata.confidence,
                assessment_year: metadata.assessment_year,
                isStreaming: false,
              };
            }
            return updated;
          });
        }
      );
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.role === "assistant") {
          updated[updated.length - 1] = {
            ...last,
            content:
              "Sorry, something went wrong. Please try again or rephrase your question.",
            confidence: "LOW",
            isStreaming: false,
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, sendMessage };
}
