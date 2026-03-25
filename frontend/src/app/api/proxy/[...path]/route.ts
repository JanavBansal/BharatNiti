import { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(request.url);
  const backendUrl = `${BACKEND_URL}/${path.join("/")}${url.search}`;

  const response = await fetch(backendUrl, {
    headers: { "Content-Type": "application/json" },
  });

  return new Response(response.body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const body = await request.text();
  const backendUrl = `${BACKEND_URL}/${path.join("/")}`;

  const response = await fetch(backendUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  // For SSE responses, stream them through
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("text/event-stream")) {
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  return new Response(response.body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
