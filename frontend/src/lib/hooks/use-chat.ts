"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, Citation, UserProfile } from "@/lib/types";
import { askQuestion } from "@/lib/api/client";

function generateId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [profile, setProfile] = useState<UserProfile>({});

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
        },
        profile,
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
  }, [profile]);

  return { messages, isLoading, sendMessage, profile, setProfile };
}
