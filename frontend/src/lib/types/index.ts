export interface Citation {
  section_number: string;
  section_title?: string;
  excerpt: string;
  document_title?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: "HIGH" | "MEDIUM" | "LOW";
  assessment_year?: string;
  isStreaming?: boolean;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  confidence: "HIGH" | "MEDIUM" | "LOW";
  assessment_year?: string;
  disclaimer: string;
  cached?: boolean;
}

export interface RateResult {
  rate_type: string;
  results: Record<string, unknown>[];
}

export interface SlabResult {
  income: number;
  regime: string;
  assessment_year: string;
  slabs: { range: string; rate: number; taxable_amount: number; tax: number }[];
  total_tax: number;
  rebate_87a: number;
  cess: number;
  total_liability: number;
  effective_rate: number;
}
