"use client";

import { useEffect, useState } from "react";
import type { EvaluationRun, Baseline } from "@/lib/api";

interface OverviewData {
  runs: EvaluationRun[];
  baselines: Baseline[];
  health: string;
  error: string | null;
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: "8px",
        padding: "20px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        minWidth: "180px",
      }}
    >
      <div style={{ fontSize: "13px", color: "#666", marginBottom: "4px" }}>
        {label}
      </div>
      <div
        style={{
          fontSize: "28px",
          fontWeight: "bold",
          color: color || "#1a1a2e",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function RunRow({ run }: { run: EvaluationRun }) {
  const statusColor =
    run.status === "completed"
      ? "#28a745"
      : run.status === "failed"
        ? "#dc3545"
        : "#ffc107";
  return (
    <tr>
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
            background: statusColor,
            fontSize: "12px",
          }}
        >
          {run.status}
        </span>
      </td>
      <td
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #eee",
          fontWeight: "bold",
        }}
      >
        {run.composite_score != null ? run.composite_score.toFixed(3) : "—"}
      </td>
      <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
        {run.results.relevance != null ? run.results.relevance.toFixed(3) : "—"}
      </td>
      <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
        {run.results.latency_ms != null ? `${run.results.latency_ms.toFixed(0)}ms` : "—"}
      </td>
      <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
        {run.is_baseline ? "⭐" : ""}
      </td>
    </tr>
  );
}

export default function OverviewPage() {
  const [data, setData] = useState<OverviewData>({
    runs: [],
    baselines: [],
    health: "unknown",
    error: null,
  });

  useEffect(() => {
    async function load() {
      try {
        const [runsRes, baselinesRes, healthRes] = await Promise.allSettled([
          fetch("/api/v1/runs?offset=0&limit=50").then((r) => r.json()),
          fetch("/api/v1/baselines").then((r) => r.json()),
          fetch("/health").then((r) => r.json()),
        ]);
        setData({
          runs: runsRes.status === "fulfilled" ? runsRes.value.runs || [] : [],
          baselines:
            baselinesRes.status === "fulfilled"
              ? Array.isArray(baselinesRes.value)
                ? baselinesRes.value
                : baselinesRes.value.baselines || []
              : [],
          health:
            healthRes.status === "fulfilled"
              ? healthRes.value.status || "unknown"
              : "unreachable",
          error: null,
        });
      } catch (e: unknown) {
        setData((prev) => ({
          ...prev,
          error: e instanceof Error ? e.message : "Failed to load",
        }));
      }
    }
    load();
  }, []);

  const completedRuns = data.runs.filter((r) => r.status === "completed");
  const avgRelevance =
    completedRuns.length > 0
      ? completedRuns.reduce((sum, r) => sum + (r.results.relevance || 0), 0) /
        completedRuns.length
      : null;
  const avgLatency =
    completedRuns.length > 0
      ? completedRuns.reduce((sum, r) => sum + (r.results.latency_ms || 0), 0) /
        completedRuns.length
      : null;
  const totalCost = completedRuns.reduce(
    (sum, r) => sum + (r.results.estimated_cost || 0),
    0
  );

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "20px" }}>
        Evaluation Overview
      </h1>

      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          marginBottom: "24px",
        }}
      >
        <StatCard label="Total Runs" value={data.runs.length} />
        <StatCard
          label="Completed"
          value={completedRuns.length}
          color="#28a745"
        />
        <StatCard
          label="Avg Relevance"
          value={avgRelevance != null ? avgRelevance.toFixed(3) : "—"}
          color="#0066cc"
        />
        <StatCard
          label="Avg Latency"
          value={avgLatency != null ? `${avgLatency.toFixed(0)}ms` : "—"}
        />
        <StatCard
          label="Total Cost"
          value={`$${totalCost.toFixed(4)}`}
        />
        <StatCard
          label="Baselines"
          value={data.baselines.length}
          color="#ffc107"
        />
        <StatCard
          label="API Health"
          value={data.health}
          color={data.health === "healthy" ? "#28a745" : "#dc3545"}
        />
      </div>

      <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>Recent Runs</h2>
      {data.error && (
        <div
          style={{
            background: "#fff3cd",
            padding: "12px",
            borderRadius: "8px",
            marginBottom: "12px",
          }}
        >
          {data.error}
        </div>
      )}
      {data.runs.length === 0 ? (
        <div
          style={{
            background: "#fff",
            padding: "40px",
            borderRadius: "8px",
            textAlign: "center",
            color: "#666",
          }}
        >
          No evaluation runs yet. Submit an evaluation to get started.
        </div>
      ) : (
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
              {["Run ID", "Time", "Profile", "Status", "Composite", "Relevance", "Latency", "Baseline"].map(
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
            {data.runs.slice(0, 20).map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
