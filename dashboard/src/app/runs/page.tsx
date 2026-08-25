"use client";

import { useEffect, useState } from "react";
import type { EvaluationRun } from "@/lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const size = 20;

  useEffect(() => {
    async function load() {
      try {
        const offset = (page - 1) * size;
        const res = await fetch(`/api/v1/runs?offset=${offset}&limit=${size}`);
        if (res.ok) {
          const data = await res.json();
          setRuns(data.runs || []);
          setTotal(data.total || 0);
        }
      } catch {
        setRuns([]);
      }
    }
    load();
  }, [page]);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>Evaluation Runs</h1>
      <p style={{ color: "#666", marginBottom: "16px" }}>
        Total: {total} runs | Page {page}
      </p>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          background: "#fff",
          borderRadius: "8px",
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <thead>
          <tr style={{ background: "#f1f3f5" }}>
            {["Run ID", "Time", "Profile", "Status", "Composite", "Relevance", "Latency", "Cost", "Baseline"].map(
              (h) => (
                <th
                  key={h}
                  style={{
                    padding: "10px 12px",
                    textAlign: "left",
                    fontSize: "13px",
                    color: "#666",
                    borderBottom: "2px solid #dee2e6",
                  }}
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.run_id}>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                <a href={`/runs/${run.run_id}`} style={{ color: "#0066cc" }}>
                  {run.run_id.slice(0, 8)}
                </a>
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {new Date(run.created_at).toLocaleString()}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {run.profile || "basic"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: "4px",
                    color: "#fff",
                    background:
                      run.status === "completed"
                        ? "#28a745"
                        : run.status === "failed"
                          ? "#dc3545"
                          : "#ffc107",
                    fontSize: "12px",
                  }}
                >
                  {run.status}
                </span>
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                {run.composite_score != null ? run.composite_score.toFixed(3) : "—"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {run.results.relevance != null ? run.results.relevance.toFixed(3) : "—"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {run.results.latency_ms != null ? `${run.results.latency_ms.toFixed(0)}ms` : "—"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {run.results.estimated_cost != null ? `$${run.results.estimated_cost.toFixed(6)}` : "—"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {run.is_baseline ? "⭐" : ""}
              </td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td
                colSpan={9}
                style={{
                  padding: "40px",
                  textAlign: "center",
                  color: "#666",
                }}
              >
                No runs found
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          style={{
            padding: "8px 16px",
            border: "1px solid #dee2e6",
            borderRadius: "4px",
            background: page === 1 ? "#f8f9fa" : "#fff",
            cursor: page === 1 ? "default" : "pointer",
          }}
        >
          Previous
        </button>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={runs.length < size}
          style={{
            padding: "8px 16px",
            border: "1px solid #dee2e6",
            borderRadius: "4px",
            background: runs.length < size ? "#f8f9fa" : "#fff",
            cursor: runs.length < size ? "default" : "pointer",
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
