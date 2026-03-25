"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
  initialQuestion?: string;
}

export function QuestionInput({
  onSubmit,
  disabled,
  initialQuestion,
}: QuestionInputProps) {
  const [value, setValue] = useState(initialQuestion || "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
    }
  }, [value]);

  useEffect(() => {
    if (initialQuestion) {
      onSubmit(initialQuestion);
      setValue("");
    }
  }, []);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSubmit(trimmed);
      setValue("");
    }
  };

  return (
    <div className="border border-[var(--border)] rounded-xl bg-[var(--card)] flex items-end gap-2 p-3 focus-within:ring-2 focus-within:ring-[var(--ring)] focus-within:border-[var(--primary)] transition-all duration-200">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Ask a tax law question..."
        disabled={disabled}
        rows={1}
        aria-label="Tax law question input"
        className="flex-1 resize-none bg-transparent border-none outline-none text-sm placeholder:text-[var(--muted-foreground)] disabled:opacity-50 focus:outline-none"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="p-2.5 rounded-lg bg-gradient-to-r from-[var(--gradient-start)] to-[var(--gradient-end)] text-white disabled:opacity-40 hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-150"
      >
        {disabled ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}
