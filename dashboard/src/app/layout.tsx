import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LLM Evaluation Dashboard",
  description: "Production-grade LLM Evaluation & Quality-Gate Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          padding: 0,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          background: "#f8f9fa",
          color: "#212529",
        }}
      >
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            gap: "24px",
            padding: "12px 24px",
            background: "#1a1a2e",
            color: "#fff",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          }}
        >
          <strong style={{ fontSize: "18px" }}>🔍 LLM Eval</strong>
          <a href="/" style={{ color: "#e0e0e0", textDecoration: "none" }}>
            Overview
          </a>
          <a
            href="/runs"
            style={{ color: "#e0e0e0", textDecoration: "none" }}
          >
            Runs
          </a>
          <a
            href="/jobs"
            style={{ color: "#e0e0e0", textDecoration: "none" }}
          >
            Jobs
          </a>
          <a
            href="/gates"
            style={{ color: "#e0e0e0", textDecoration: "none" }}
          >
            Quality Gates
          </a>
          <a
            href="/baselines"
            style={{ color: "#e0e0e0", textDecoration: "none" }}
          >
            Baselines
          </a>
          <a
            href="/profiles"
            style={{ color: "#e0e0e0", textDecoration: "none" }}
          >
            Profiles
          </a>
        </nav>
        <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
