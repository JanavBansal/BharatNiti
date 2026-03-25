"use client";

import { useSearchParams } from "next/navigation";
import { ChatContainer } from "@/components/chat/chat-container";
import { Suspense } from "react";

function ChatContent() {
  const searchParams = useSearchParams();
  const initialQuestion = searchParams.get("q") || undefined;

  return <ChatContainer initialQuestion={initialQuestion} />;
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatContent />
    </Suspense>
  );
}
