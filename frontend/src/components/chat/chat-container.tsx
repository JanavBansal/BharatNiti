"use client";

import { useRef, useEffect } from "react";
import { useChat } from "@/lib/hooks/use-chat";
import { MessageBubble } from "./message-bubble";
import { QuestionInput } from "./question-input";
import { SuggestedQuestions } from "./suggested-questions";

interface ChatContainerProps {
  initialQuestion?: string;
}

export function ChatContainer({ initialQuestion }: ChatContainerProps) {
  const { messages, isLoading, sendMessage } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-57px)]">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
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

      {/* Input */}
      <div className="border-t border-[var(--border)] p-4">
        <div className="max-w-3xl mx-auto">
          <QuestionInput
            onSubmit={sendMessage}
            disabled={isLoading}
            initialQuestion={initialQuestion}
          />
          <p className="text-xs text-[var(--muted-foreground)] mt-2 text-center">
            caAI is a research tool, not a CA. Always verify with a professional.
          </p>
        </div>
      </div>
    </div>
  );
}
