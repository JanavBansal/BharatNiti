"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

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

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
    }
  }, [value]);

  // Auto-submit initial question
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
    <div className="border border-[var(--border)] rounded-xl bg-[var(--card)] flex items-end gap-2 p-3">
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
        className="flex-1 resize-none bg-transparent border-none outline-none text-sm placeholder:text-[var(--muted-foreground)] disabled:opacity-50"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className="p-2 rounded-lg bg-[var(--primary)] text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  );
}
