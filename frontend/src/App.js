import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from "recharts";

function App() {
  const [laps, setLaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDriver, setSelectedDriver] = useState("LEC");
  const [drivers, setDrivers] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8001/race-laps")
      .then((res) => res.json())
      .then((data) => {
        setLaps(data);
        const uniqueDrivers = [...new Set(data.map((d) => d.Driver))];
        setDrivers(uniqueDrivers);
        setLoading(false);
      });
  }, []);

  const filteredLaps = laps.filter((lap) => lap.Driver === selectedDriver);

  return (
    <div style={{ padding: "30px", fontFamily: "sans-serif" }}>
      <h1>🏎️ F1 Analytics Dashboard</h1>
      <h3>2024 Monaco Grand Prix</h3>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <div style={{ marginBottom: "20px" }}>
            <label style={{ marginRight: "10px", fontWeight: "bold" }}>
              Select Driver:
            </label>
            <select
              value={selectedDriver}
              onChange={(e) => setSelectedDriver(e.target.value)}
              style={{ padding: "6px", fontSize: "16px" }}
            >
              {drivers.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <h2>{selectedDriver} — Lap Time Chart</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={filteredLaps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="LapNumber" label={{ value: "Lap", position: "insideBottom", offset: -5 }} />
              <YAxis domain={["auto", "auto"]} label={{ value: "Lap Time (s)", angle: -90, position: "insideLeft" }} />
              <Tooltip formatter={(value) => `${value.toFixed(3)}s`} />
              <Legend />
              <Line type="monotone" dataKey="LapTimeSeconds" stroke="#e10600" dot={false} name="Lap Time" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>

          <h2 style={{ marginTop: "40px" }}>Raw Lap Data</h2>
          <table border="1" cellPadding="8" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>Driver</th>
                <th>Lap</th>
                <th>Lap Time (s)</th>
                <th>Compound</th>
                <th>Tyre Life</th>
              </tr>
            </thead>
            <tbody>
              {filteredLaps.map((lap, index) => (
                <tr key={index}>
                  <td>{lap.Driver}</td>
                  <td>{lap.LapNumber}</td>
                  <td>{lap.LapTimeSeconds?.toFixed(3)}</td>
                  <td>{lap.Compound}</td>
                  <td>{lap.TyreLife}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

export default App;