"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import { useChat } from "@/lib/hooks/use-chat";
import { MessageBubble } from "./message-bubble";
import { QuestionInput } from "./question-input";
import { SuggestedQuestions } from "./suggested-questions";
import { ChevronDown } from "lucide-react";
import { UserProfilePanel } from "./user-profile";

interface ChatContainerProps {
  initialQuestion?: string;
}

export function ChatContainer({ initialQuestion }: ChatContainerProps) {
  const { messages, isLoading, sendMessage, profile, setProfile } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isNearBottom, setIsNearBottom] = useState(true);

  const checkNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 120;
    setIsNearBottom(el.scrollHeight - el.scrollTop - el.clientHeight < threshold);
  }, []);

  // Auto-scroll only when near bottom
  useEffect(() => {
    if (isNearBottom) {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isNearBottom]);

  const scrollToBottom = () => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] relative">
      {/* Messages */}
      <div
        ref={scrollRef}
        onScroll={checkNearBottom}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-4"
      >
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <SuggestedQuestions onSelect={sendMessage} />
          ) : (
            messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}
        </div>
      </div>

      {/* Scroll to bottom button */}
      {!isNearBottom && messages.length > 0 && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-24 right-6 w-10 h-10 rounded-full bg-[var(--card)] border border-[var(--border)] shadow-lg flex items-center justify-center hover:bg-[var(--muted)] transition-all animate-fade-in-up"
          aria-label="Scroll to bottom"
        >
          <ChevronDown className="w-5 h-5 text-[var(--muted-foreground)]" />
        </button>
      )}

      {/* Input */}
      <div className="border-t border-[var(--border)] p-3 sm:p-4 bg-[var(--background)]">
        <div className="max-w-3xl mx-auto">
          <UserProfilePanel profile={profile} onChange={setProfile} />
          <QuestionInput
            onSubmit={sendMessage}
            disabled={isLoading}
            initialQuestion={initialQuestion}
          />
          <p className="text-xs text-[var(--muted-foreground)] mt-2 text-center">
            BharatNiti is a research tool, not a CA. Always verify with a professional.
          </p>
        </div>
      </div>
    </div>
  );
}
