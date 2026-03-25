import type { Citation, SlabResult } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

export async function askQuestion(
  question: string,
  conversationId?: string,
  onToken?: (token: string) => void,
  onMetadata?: (metadata: {
    citations: Citation[];
    confidence: "HIGH" | "MEDIUM" | "LOW";
    assessment_year?: string;
    disclaimer: string;
  }) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  // SSE parser state
  let currentEvent = "";
  let dataLines: string[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        // New event starting — flush previous if any
        if (currentEvent && dataLines.length > 0) {
          handleSSEEvent(currentEvent, dataLines.join("\n"), onToken, onMetadata);
        }
        currentEvent = line.slice(7).trim();
        dataLines = [];
      } else if (line.startsWith("data: ")) {
        dataLines.push(line.slice(6));
      } else if (line === "" && currentEvent) {
        // Empty line = end of SSE event
        if (dataLines.length > 0) {
          handleSSEEvent(currentEvent, dataLines.join("\n"), onToken, onMetadata);
        }
        currentEvent = "";
        dataLines = [];
      }
    }
  }

  // Flush any remaining event
  if (currentEvent && dataLines.length > 0) {
    handleSSEEvent(currentEvent, dataLines.join("\n"), onToken, onMetadata);
  }
}

function handleSSEEvent(
  eventType: string,
  data: string,
  onToken?: (token: string) => void,
  onMetadata?: (metadata: {
    citations: Citation[];
    confidence: "HIGH" | "MEDIUM" | "LOW";
    assessment_year?: string;
    disclaimer: string;
  }) => void
) {
  if (eventType === "answer" && onToken) {
    // Full answer — send as a single chunk to preserve markdown formatting
    onToken(data);
  } else if (eventType === "token" && onToken) {
    // Streaming token
    onToken(data);
  } else if (eventType === "metadata" && onMetadata) {
    try {
      const metadata = JSON.parse(data);
      onMetadata(metadata);
    } catch {
      // Ignore malformed metadata
    }
  }
}

export async function lookupTDSRate(
  section?: string,
  pan: boolean = true
): Promise<{ rate_type: string; results: Record<string, unknown>[] }> {
  const params = new URLSearchParams();
  if (section) params.set("section", section);
  params.set("pan", String(pan));
  const res = await fetch(`${API_BASE}/api/v1/rates/tds?${params}`);
  return res.json();
}

export async function lookupGSTRate(
  category?: string
): Promise<{ rate_type: string; results: Record<string, unknown>[] }> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  const res = await fetch(`${API_BASE}/api/v1/rates/gst?${params}`);
  return res.json();
}

export async function calculateIncomeTax(
  income: number,
  regime: string = "new",
  assessmentYear: string = "2025-26"
): Promise<SlabResult> {
  const params = new URLSearchParams({
    income: String(income),
    regime,
    assessment_year: assessmentYear,
  });
  const res = await fetch(`${API_BASE}/api/v1/rates/income-tax?${params}`);
  return res.json();
}
