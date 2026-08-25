"use client";

import { useEffect, useState } from "react";
import type { Baseline } from "@/lib/api";

export default function BaselinesPage() {
  const [baselines, setBaselines] = useState<Baseline[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/v1/baselines");
        if (res.ok) {
          const data = await res.json();
          setBaselines(Array.isArray(data) ? data : data.baselines || []);
        }
      } catch {
        setBaselines([]);
      }
    }
    load();
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>Baselines</h1>
      {baselines.length === 0 ? (
        <div
          style={{
            background: "#fff",
            padding: "40px",
            borderRadius: "8px",
            textAlign: "center",
            color: "#666",
          }}
        >
          No baselines configured. Create one via the API.
        </div>
      ) : (
        <div
          style={{
            background: "#fff",
            borderRadius: "8px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            overflow: "hidden",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f1f3f5" }}>
                {["Name", "Description", "Run ID", "Created"].map((h) => (
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
                ))}
              </tr>
            </thead>
            <tbody>
              {baselines.map((b) => (
                <tr key={b.baseline_id}>
                  <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                    ⭐ {b.name}
                  </td>
                  <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                    {b.description || "—"}
                  </td>
                  <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                    <a href={`/runs/${b.run_id}`} style={{ color: "#0066cc" }}>
                      {b.run_id.slice(0, 8)}
                    </a>
                  </td>
                  <td style={{ padding: "8px 12px", borderBottom: "1px solid #eee" }}>
                    {new Date(b.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
