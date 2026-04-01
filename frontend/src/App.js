import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from "recharts";

// ─── Tire compound colors (official F1 colors) ──────────────────────────────
const COMPOUND_COLORS = {
  SOFT: "#e10600",
  MEDIUM: "#ffd700",
  HARD: "#ffffff",
  INTERMEDIATE: "#39b54a",
  WET: "#0067ff",
};

// ─── Each driver gets a chart line color ────────────────────────────────────
const DRIVER_COLORS = [
  "#e10600", "#00d2be", "#ff8700", "#dc0000",
  "#0600ef", "#005aff", "#900000", "#ffffff",
  "#2293d1", "#37bedd", "#b6babd", "#c92d4b",
  "#006f62", "#0090ff", "#1e6176", "#f596c8",
  "#358c75", "#b6babd", "#fd4bc7", "#d3ab17",
];

// ─── Small card component ────────────────────────────────────────────────────
function StatCard({ label, value, sub }) {
  return (
    <div style={{
      background: "#1a1a1a",
      border: "1px solid #333",
      borderRadius: 8,
      padding: "14px 20px",
      minWidth: 140,
    }}>
      <div style={{ color: "#888", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
        {label}
      </div>
      <div style={{ color: "#fff", fontSize: 22, fontWeight: 700, marginTop: 4 }}>
        {value}
      </div>
      {sub && <div style={{ color: "#666", fontSize: 12, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ─── Custom tooltip for the chart ────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#1a1a1a",
      border: "1px solid #444",
      borderRadius: 6,
      padding: "10px 14px",
      fontSize: 13,
    }}>
      <div style={{ color: "#aaa", marginBottom: 6 }}>Lap {label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: <strong>{p.value?.toFixed(3)}s</strong>
        </div>
      ))}
    </div>
  );
}

// ─── Compound badge ──────────────────────────────────────────────────────────
function CompoundBadge({ compound }) {
  const bg = COMPOUND_COLORS[compound] ?? "#555";
  const textColor = compound === "HARD" ? "#000" : compound === "MEDIUM" ? "#000" : "#fff";
  return (
    <span style={{
      background: bg,
      color: textColor,
      fontSize: 10,
      fontWeight: 700,
      padding: "2px 7px",
      borderRadius: 4,
      letterSpacing: 0.5,
    }}>
      {compound ?? "—"}
    </span>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────
export default function App() {
  const [laps, setLaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Multi-select: which drivers to show on chart
  const [selectedDrivers, setSelectedDrivers] = useState([]);

  // Table: single driver detail view
  const [tableDriver, setTableDriver] = useState(null);

  // All unique driver codes in the data
  const [allDrivers, setAllDrivers] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8001/race-laps")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setLaps(data);
        const drivers = [...new Set(data.map((d) => d.Driver))].sort();
        setAllDrivers(drivers);
        // Default: show first 3 drivers on chart
        setSelectedDrivers(drivers.slice(0, 3));
        setTableDriver(drivers[0]);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Toggle a driver in the multi-select list
  function toggleDriver(driver) {
    setSelectedDrivers((prev) =>
      prev.includes(driver) ? prev.filter((d) => d !== driver) : [...prev, driver]
    );
  }

  // Stats for the table driver
  const tableLaps = laps.filter((l) => l.Driver === tableDriver);
  const validTimes = tableLaps.map((l) => l.LapTimeSeconds).filter(Boolean);
  const fastestLap = validTimes.length ? Math.min(...validTimes) : null;
  const avgLap = validTimes.length
    ? (validTimes.reduce((a, b) => a + b, 0) / validTimes.length).toFixed(3)
    : null;

  // Build chart data: one object per lap number, with a key per selected driver
  // Each lap number gets { LapNumber: 5, VER: 74.21, LEC: 75.03, ... }
  const chartData = React.useMemo(() => {
    if (!selectedDrivers.length) return [];
    const lapMap = {};
    laps
      .filter((l) => selectedDrivers.includes(l.Driver))
      .forEach((l) => {
        const ln = l.LapNumber;
        if (!lapMap[ln]) lapMap[ln] = { LapNumber: ln };
        lapMap[ln][l.Driver] = l.LapTimeSeconds;
      });
    return Object.values(lapMap).sort((a, b) => a.LapNumber - b.LapNumber);
  }, [laps, selectedDrivers]);

  // ─── Styles ────────────────────────────────────────────────────────────────
  const styles = {
    app: {
      minHeight: "100vh",
      background: "#0f0f0f",
      color: "#fff",
      fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
      padding: "0 0 60px",
    },
    header: {
      background: "#111",
      borderBottom: "3px solid #e10600",
      padding: "18px 32px",
      display: "flex",
      alignItems: "center",
      gap: 16,
    },
    redBar: {
      width: 5,
      height: 36,
      background: "#e10600",
      borderRadius: 2,
    },
    section: {
      maxWidth: 1200,
      margin: "0 auto",
      padding: "32px 32px 0",
    },
    sectionTitle: {
      color: "#e10600",
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: 2,
      textTransform: "uppercase",
      marginBottom: 16,
    },
    statsRow: {
      display: "flex",
      gap: 12,
      flexWrap: "wrap",
      marginBottom: 32,
    },
    driverGrid: {
      display: "flex",
      flexWrap: "wrap",
      gap: 8,
      marginBottom: 24,
    },
    driverBtn: (active, color) => ({
      padding: "6px 14px",
      border: `2px solid ${active ? color : "#333"}`,
      borderRadius: 20,
      background: active ? color + "22" : "transparent",
      color: active ? color : "#888",
      cursor: "pointer",
      fontSize: 13,
      fontWeight: 600,
      transition: "all 0.15s",
    }),
    chartBox: {
      background: "#141414",
      border: "1px solid #222",
      borderRadius: 10,
      padding: "24px 12px 12px",
      marginBottom: 40,
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
      fontSize: 13,
    },
    th: {
      color: "#888",
      fontWeight: 600,
      fontSize: 11,
      letterSpacing: 1,
      textTransform: "uppercase",
      padding: "10px 14px",
      borderBottom: "1px solid #222",
      textAlign: "left",
    },
    td: {
      padding: "9px 14px",
      borderBottom: "1px solid #1a1a1a",
      color: "#ccc",
    },
  };

  // ─── Render ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ ...styles.app, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#e10600", fontSize: 32, marginBottom: 12 }}>🏎️</div>
          <div style={{ color: "#666" }}>Loading race data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ ...styles.app, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#e10600" }}>Error: {error}</div>
      </div>
    );
  }

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.redBar} />
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>
            F1 Analytics Dashboard
          </div>
          <div style={{ color: "#666", fontSize: 13, marginTop: 2 }}>
            2024 Monaco Grand Prix · Race
          </div>
        </div>
      </div>

      <div style={styles.section}>

        {/* ── Stats Cards ── */}
        <div style={styles.sectionTitle}>Race Overview</div>
        <div style={styles.statsRow}>
          <StatCard label="Total Laps in Data" value={laps.length} />
          <StatCard label="Drivers" value={allDrivers.length} />
          {fastestLap && (
            <StatCard
              label={`Fastest Lap · ${tableDriver}`}
              value={`${fastestLap.toFixed(3)}s`}
              sub="Viewing selected driver below"
            />
          )}
          {avgLap && (
            <StatCard
              label={`Avg Lap · ${tableDriver}`}
              value={`${avgLap}s`}
            />
          )}
        </div>

        {/* ── Multi-Driver Comparison Chart ── */}
        <div style={styles.sectionTitle}>Lap Time Comparison</div>
        <p style={{ color: "#666", fontSize: 13, marginBottom: 16, marginTop: -8 }}>
          Select up to 5 drivers to compare on the chart
        </p>

        {/* Driver toggle buttons */}
        <div style={styles.driverGrid}>
          {allDrivers.map((driver, i) => {
            const color = DRIVER_COLORS[i % DRIVER_COLORS.length];
            const active = selectedDrivers.includes(driver);
            return (
              <button
                key={driver}
                style={styles.driverBtn(active, color)}
                onClick={() => toggleDriver(driver)}
              >
                {driver}
              </button>
            );
          })}
        </div>

        <div style={styles.chartBox}>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" />
              <XAxis
                dataKey="LapNumber"
                stroke="#555"
                tick={{ fill: "#888", fontSize: 12 }}
                label={{ value: "Lap Number", position: "insideBottom", offset: -10, fill: "#666", fontSize: 12 }}
              />
              <YAxis
                stroke="#555"
                tick={{ fill: "#888", fontSize: 12 }}
                domain={["auto", "auto"]}
                label={{ value: "Lap Time (s)", angle: -90, position: "insideLeft", fill: "#666", fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ color: "#888", fontSize: 12, paddingTop: 12 }}
              />
              {selectedDrivers.map((driver, i) => (
                <Line
                  key={driver}
                  type="monotone"
                  dataKey={driver}
                  stroke={DRIVER_COLORS[allDrivers.indexOf(driver) % DRIVER_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  connectNulls={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* ── Per-Driver Detail Table ── */}
        <div style={styles.sectionTitle}>Driver Lap Detail</div>

        {/* Single driver selector for table */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
          {allDrivers.map((driver, i) => {
            const color = DRIVER_COLORS[i % DRIVER_COLORS.length];
            return (
              <button
                key={driver}
                style={styles.driverBtn(tableDriver === driver, color)}
                onClick={() => setTableDriver(driver)}
              >
                {driver}
              </button>
            );
          })}
        </div>

        {/* Table */}
        <div style={{ background: "#141414", border: "1px solid #222", borderRadius: 10, overflow: "hidden" }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Lap</th>
                <th style={styles.th}>Lap Time (s)</th>
                <th style={styles.th}>Compound</th>
                <th style={styles.th}>Tyre Life</th>
                <th style={styles.th}>Δ Fastest</th>
              </tr>
            </thead>
            <tbody>
              {tableLaps.map((lap, i) => {
                const delta = fastestLap ? (lap.LapTimeSeconds - fastestLap).toFixed(3) : null;
                const isFastest = lap.LapTimeSeconds === fastestLap;
                return (
                  <tr
                    key={i}
                    style={{
                      background: isFastest ? "#e1060012" : "transparent",
                      transition: "background 0.1s",
                    }}
                  >
                    <td style={styles.td}>{lap.LapNumber}</td>
                    <td style={{
                      ...styles.td,
                      color: isFastest ? "#e10600" : "#ccc",
                      fontWeight: isFastest ? 700 : 400,
                      fontFamily: "monospace",
                    }}>
                      {lap.LapTimeSeconds?.toFixed(3)}s
                      {isFastest && <span style={{ marginLeft: 8, fontSize: 10, color: "#e10600" }}>▼ FASTEST</span>}
                    </td>
                    <td style={styles.td}>
                      <CompoundBadge compound={lap.Compound} />
                    </td>
                    <td style={{ ...styles.td, color: "#888" }}>
                      {lap.TyreLife} laps
                    </td>
                    <td style={{
                      ...styles.td,
                      color: isFastest ? "#e10600" : "#555",
                      fontFamily: "monospace",
                      fontSize: 12,
                    }}>
                      {isFastest ? "—" : `+${delta}s`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}