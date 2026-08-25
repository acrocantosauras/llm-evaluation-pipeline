"use client";

import { useEffect, useState } from "react";
import type { EvaluationRun, MetricResult } from "@/lib/api";

function MetricBar({
  metric,
  score,
  passed,
}: {
  metric: string;
  score: number;
  passed: boolean | null;
}) {
  const color =
    passed === true ? "#28a745" : passed === false ? "#dc3545" : "#6c757d";
  return (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "4px",
          fontSize: "14px",
        }}
      >
        <span>{metric}</span>
        <span style={{ fontWeight: "bold", color }}>
          {score.toFixed(4)}
          {passed !== null && (
            <span style={{ marginLeft: "8px", fontSize: "12px" }}>
              {passed ? "✓ PASS" : "✗ FAIL"}
            </span>
          )}
        </span>
      </div>
      <div
        style={{
          height: "8px",
          background: "#e9ecef",
          borderRadius: "4px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(Math.max(score * 100, 0), 100)}%`,
            background: color,
            borderRadius: "4px",
            transition: "width 0.3s",
          }}
        />
      </div>
    </div>
  );
}

export default function RunDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const [run, setRun] = useState<EvaluationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/v1/runs/${params.id}`);
        if (!res.ok) throw new Error(`Run not found (${res.status})`);
        setRun(await res.json());
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load run");
      }
    }
    load();
  }, [params.id]);

  if (error) {
    return (
      <div
        style={{
          background: "#fff",
          padding: "40px",
          borderRadius: "8px",
          textAlign: "center",
          color: "#dc3545",
        }}
      >
        {error}
      </div>
    );
  }

  if (!run) {
    return (
      <div
        style={{
          background: "#fff",
          padding: "40px",
          borderRadius: "8px",
          textAlign: "center",
          color: "#666",
        }}
      >
        Loading...
      </div>
    );
  }

  const statusColor =
    run.status === "completed"
      ? "#28a745"
      : run.status === "failed"
        ? "#dc3545"
        : "#ffc107";

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>
        Run{" "}
        <code style={{ fontSize: "18px", color: "#666" }}>
          {run.run_id.slice(0, 12)}
        </code>
      </h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            background: "#fff",
            padding: "16px",
            borderRadius: "8px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ fontSize: "13px", color: "#666" }}>Status</div>
          <span
            style={{
              padding: "2px 8px",
              borderRadius: "4px",
              color: "#fff",
              background: statusColor,
              fontSize: "14px",
            }}
          >
            {run.status}
          </span>
        </div>
        <div
          style={{
            background: "#fff",
            padding: "16px",
            borderRadius: "8px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ fontSize: "13px", color: "#666" }}>Profile</div>
          <div style={{ fontSize: "18px", fontWeight: "bold" }}>
            {run.profile || "basic"}
          </div>
        </div>
        <div
          style={{
            background: "#fff",
            padding: "16px",
            borderRadius: "8px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ fontSize: "13px", color: "#666" }}>
            Composite Score
          </div>
          <div style={{ fontSize: "18px", fontWeight: "bold", color: "#0066cc" }}>
            {run.composite_score != null ? run.composite_score.toFixed(4) : "—"}
          </div>
        </div>
        <div
          style={{
            background: "#fff",
            padding: "16px",
            borderRadius: "8px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ fontSize: "13px", color: "#666" }}>Created</div>
          <div style={{ fontSize: "14px" }}>
            {new Date(run.created_at).toLocaleString()}
          </div>
        </div>
      </div>

      <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>Metric Results</h2>
      <div
        style={{
          background: "#fff",
          padding: "20px",
          borderRadius: "8px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          marginBottom: "24px",
        }}
      >
        {run.metric_results && run.metric_results.length > 0 ? (
          run.metric_results.map((mr: MetricResult) => (
            <MetricBar
              key={mr.metric}
              metric={mr.metric}
              score={mr.score}
              passed={mr.passed}
            />
          ))
        ) : (
          <div style={{ color: "#666" }}>No metric results available</div>
        )}
      </div>

      <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>Legacy Metrics</h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
        }}
      >
        {[
          { label: "Relevance", value: run.results.relevance?.toFixed(4) },
          { label: "Latency", value: run.results.latency_ms ? `${run.results.latency_ms.toFixed(0)}ms` : null },
          { label: "Est. Cost", value: run.results.estimated_cost ? `$${run.results.estimated_cost.toFixed(6)}` : null },
        ].map(({ label, value }) => (
          <div
            key={label}
            style={{
              background: "#fff",
              padding: "16px",
              borderRadius: "8px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            }}
          >
            <div style={{ fontSize: "13px", color: "#666" }}>{label}</div>
            <div style={{ fontSize: "20px", fontWeight: "bold" }}>
              {value || "—"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
