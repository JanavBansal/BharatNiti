import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "BharatNiti — Indian Tax Law Assistant";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%)",
          fontFamily: "system-ui",
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            background: "linear-gradient(135deg, #3b82f6, #a78bfa)",
            backgroundClip: "text",
            color: "transparent",
            marginBottom: 16,
          }}
        >
          BharatNiti
        </div>
        <div
          style={{
            fontSize: 32,
            color: "#a3a3a3",
            fontWeight: 400,
          }}
        >
          Indian Tax Law, Answered
        </div>
        <div
          style={{
            fontSize: 18,
            color: "#737373",
            marginTop: 24,
            maxWidth: 600,
            textAlign: "center",
          }}
        >
          AI-powered answers with citations from the Income Tax Act, GST Act, and more
        </div>
      </div>
    ),
    { ...size }
  );
}
