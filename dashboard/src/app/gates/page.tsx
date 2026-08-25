"use client";

import { useEffect, useState } from "react";
import type { QualityGate } from "@/lib/api";

export default function GatesPage() {
  const [gates, setGates] = useState<QualityGate[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/v1/quality-gates");
        if (res.ok) {
          const data = await res.json();
          setGates(Array.isArray(data) ? data : data.gates || []);
        }
      } catch {
        setGates([]);
      }
    }
    load();
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>Quality Gates</h1>
      {gates.length === 0 ? (
        <div
          style={{
            background: "#fff",
            padding: "40px",
            borderRadius: "8px",
            textAlign: "center",
            color: "#666",
          }}
        >
          No quality gates configured. Create one via the API.
        </div>
      ) : (
        <div style={{ display: "grid", gap: "16px" }}>
          {gates.map((gate) => (
            <div
              key={gate.gate_id}
              style={{
                background: "#fff",
                padding: "20px",
                borderRadius: "8px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <h3 style={{ margin: 0 }}>{gate.name}</h3>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: gate.enabled ? "#28a745" : "#6c757d",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                >
                  {gate.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Metric", "Threshold", "Direction"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 12px",
                          textAlign: "left",
                          borderBottom: "1px solid #dee2e6",
                          fontSize: "13px",
                          color: "#666",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(gate.thresholds).map(
                    ([metric, config]) => {
                      const cfg = config as Record<string, unknown>;
                      const value = cfg.value ?? "—";
                      const direction =
                        cfg.direction === "higher_is_better"
                          ? "Higher is better"
                          : "Lower is better";
                      return (
                        <tr key={metric}>
                          <td style={{ padding: "6px 12px", borderBottom: "1px solid #f1f3f5" }}>
                            {metric}
                          </td>
                          <td style={{ padding: "6px 12px", borderBottom: "1px solid #f1f3f5", fontWeight: "bold" }}>
                            {typeof value === "number" ? value.toFixed(4) : String(value)}
                          </td>
                          <td style={{ padding: "6px 12px", borderBottom: "1px solid #f1f3f5" }}>
                            {direction}
                          </td>
                        </tr>
                      );
                    }
                  )}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
