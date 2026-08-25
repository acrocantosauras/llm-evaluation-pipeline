"use client";

import { useEffect, useState } from "react";

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Record<string, string[]>>({});

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/v1/profiles");
        if (res.ok) {
          const data = await res.json();
          setProfiles(data.profiles || {});
        }
      } catch {
        setProfiles({});
      }
    }
    load();
  }, []);

  const profileColors: Record<string, string> = {
    basic: "#6c757d",
    rag: "#007bff",
    rag_strict: "#fd7e14",
    judge: "#6f42c1",
  };

  return (
    <div>
      <h1 style={{ fontSize: "24px", marginBottom: "16px" }}>Evaluation Profiles</h1>
      <p style={{ color: "#666", marginBottom: "16px" }}>
        Profiles define which evaluators run during an evaluation. Choose a
        profile based on your quality requirements and cost constraints.
      </p>
      {Object.keys(profiles).length === 0 ? (
        <div
          style={{
            background: "#fff",
            padding: "40px",
            borderRadius: "8px",
            textAlign: "center",
            color: "#666",
          }}
        >
          No profiles available.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
          {Object.entries(profiles).map(([name, evaluators]) => (
            <div
              key={name}
              style={{
                background: "#fff",
                borderRadius: "8px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "16px 20px",
                  background: profileColors[name] || "#6c757d",
                  color: "#fff",
                }}
              >
                <h3 style={{ margin: 0, textTransform: "capitalize" }}>{name}</h3>
              </div>
              <div style={{ padding: "16px 20px" }}>
                <div style={{ fontSize: "13px", color: "#666", marginBottom: "8px" }}>
                  {evaluators.length} evaluator{evaluators.length !== 1 ? "s" : ""}:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {evaluators.map((ev) => (
                    <span
                      key={ev}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "12px",
                        background: "#e9ecef",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                    >
                      {ev}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
