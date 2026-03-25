import { useState } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000"; // FastAPI backend

export default function App() {
  const [output, setOutput] = useState("");
  const [year, setYear] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFetch = async (endpoint) => {
    setLoading(true);
    setOutput("");
    try {
      const res = await axios.get(`${API_BASE}${endpoint}`);
      setOutput(JSON.stringify(res.data, null, 2));
    } catch (err) {
      setOutput(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 p-6">
      <h1 className="text-3xl font-bold mb-6 text-center">HC's IESO API</h1>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Demand Now */}
        <div className="bg-white p-4 rounded-2xl shadow">
          <h2 className="text-xl font-semibold mb-2">Current Demand</h2>
          <button
            onClick={() => handleFetch("/demand/now")}
            className="bg-amber-500 text-white px-3 py-1 rounded"
          >
            Get Current Demand
          </button>
        </div>

        {/* Yearly Demand */}
        <div className="bg-white p-4 rounded-2xl shadow">
          <h2 className="text-xl font-semibold mb-2">Demand by Year</h2>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="Enter year (2003–2025)"
            className="border rounded px-2 py-1 mr-2"
          />
          <button
            onClick={() => handleFetch(`/demand/${year}`)}
            className="bg-amber-500 text-white px-3 py-1 rounded"
          >
            Fetch
          </button>
        </div>

        {/* Supply */}
        <div className="bg-white p-4 rounded-2xl shadow">
          <h2 className="text-xl font-semibold mb-2">Supply Data</h2>
          <button
            onClick={() => handleFetch("/api/supply")}
            className="bg-red-700 text-white px-3 py-1 rounded"
          >
            Get Supply
          </button>
        </div>

        {/* Zonal Prices */}
        <div className="bg-white p-4 rounded-2xl shadow">
          <h2 className="text-xl font-semibold mb-2">Zonal Pricing</h2>
          <button
            onClick={() => handleFetch("/price/zonal")}
            className="bg-rose-900 text-white px-3 py-1 rounded"
          >
            Get Prices
          </button>
        </div>
      </div>

      {/* Output */}
      <div className="mt-6 bg-white p-4 rounded-2xl shadow">
        <h2 className="text-xl font-semibold mb-2">Output</h2>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <pre className="text-sm whitespace-pre-wrap">{output}</pre>
        )}
      </div>
    </div>
  );
}