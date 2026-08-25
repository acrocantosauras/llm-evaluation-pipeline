"use client";

import { useEffect, useState } from "react";
import type { EvaluationJob } from "@/lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<EvaluationJob[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/v1/jobs?offset=0&limit=50");
        if (res.ok) {
          const data = await res.json();
          setJobs(data.jobs || []);
        }
      } catch {
        setJobs([]);
      }
    }
    load();
  }, []);

  const statusColor = (status: string) =>
    ({
      queued: "#6c757d",
      running: "#007bff",
      completed: "#28a745",
      failed: "#dc3545",
      cancelled: "#ffc107",
    })[status] || "#6c757d";

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>Evaluation Jobs</h1>
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
            {["Job ID", "Status", "Created", "Progress", "Failed", "Error"].map(
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
          {jobs.map((job) => (
            <tr key={job.job_id}>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {job.job_id.slice(0, 8)}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: "4px",
                    color: "#fff",
                    background: statusColor(job.status),
                    fontSize: "12px",
                  }}
                >
                  {job.status}
                </span>
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {new Date(job.created_at).toLocaleString()}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {job.progress
                  ? `${job.progress.completed}/${job.progress.total}`
                  : "—"}
              </td>
              <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                {job.progress && job.progress.failed > 0 ? (
                  <span style={{ color: "#dc3545" }}>{job.progress.failed}</span>
                ) : (
                  "0"
                )}
              </td>
              <td
                style={{
                  padding: "8px 12px",
                  borderBottom: "1px solid #eee",
                  maxWidth: "300px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {job.error_message || "—"}
              </td>
            </tr>
          ))}
          {jobs.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: "40px", textAlign: "center", color: "#666" }}>
                No jobs found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
