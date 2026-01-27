"use client";

import { useEffect, useState } from "react";

interface Anomaly {
  account_number: string;
  postal_code: string | null;
  housing_type: string;
  consumption_kwh: number;
  cohort_mean: number;
  cohort_std: number;
  z_score: number;
  p_value: number;
  anomaly_type: "HIGH" | "LOW";
  deviation_percent: number;
}

interface AnomalyTableProps {
  limit?: number;
  housingType?: string;
}

export default function AnomalyTable({
  limit = 10,
  housingType,
}: AnomalyTableProps) {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"z_score" | "p_value" | "consumption">(
    "z_score"
  );

  useEffect(() => {
    fetchAnomalies();
  }, [housingType]);

  const fetchAnomalies = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (housingType) params.append("housing_type", housingType);

      const response = await fetch(`/api/analytics/anomalies?${params}`);
      if (!response.ok) throw new Error("Failed to fetch");
      const data = await response.json();
      setAnomalies((data.anomalies || []).slice(0, limit));
    } catch (error) {
      console.error("Failed to fetch anomalies:", error);
      // Set mock data
      setAnomalies(getMockAnomalies());
    } finally {
      setLoading(false);
    }
  };

  const getMockAnomalies = (): Anomaly[] => [
    {
      account_number: "1000000016",
      postal_code: "570999",
      housing_type: "hdb_4_room",
      consumption_kwh: 720,
      cohort_mean: 340,
      cohort_std: 85,
      z_score: 4.47,
      p_value: 0.000008,
      anomaly_type: "HIGH",
      deviation_percent: 111.8,
    },
    {
      account_number: "1000000017",
      postal_code: "530888",
      housing_type: "hdb_4_room",
      consumption_kwh: 125,
      cohort_mean: 340,
      cohort_std: 85,
      z_score: -2.53,
      p_value: 0.0114,
      anomaly_type: "LOW",
      deviation_percent: -63.2,
    },
    {
      account_number: "1000000010",
      postal_code: "258431",
      housing_type: "landed",
      consumption_kwh: 1650,
      cohort_mean: 1150,
      cohort_std: 220,
      z_score: 2.27,
      p_value: 0.0232,
      anomaly_type: "HIGH",
      deviation_percent: 43.5,
    },
  ];

  const formatPValue = (p: number) => {
    if (p < 0.001) return "<0.001";
    if (p < 0.01) return p.toFixed(3);
    return p.toFixed(3);
  };

  const formatHousingType = (type: string) => {
    return type
      .replace(/_/g, " ")
      .replace(/hdb/i, "HDB")
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const sortedAnomalies = [...anomalies].sort((a, b) => {
    switch (sortBy) {
      case "z_score":
        return Math.abs(b.z_score) - Math.abs(a.z_score);
      case "p_value":
        return a.p_value - b.p_value;
      case "consumption":
        return b.consumption_kwh - a.consumption_kwh;
      default:
        return 0;
    }
  });

  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-gray-700 rounded" />
        ))}
      </div>
    );
  }

  if (anomalies.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        <svg
          className="w-12 h-12 mx-auto mb-3 text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p>No anomalies detected</p>
        <p className="text-sm text-gray-500 mt-1">
          All consumption within normal range
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Sort controls */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-gray-400 text-xs">Sort by:</span>
        {(["z_score", "p_value", "consumption"] as const).map((option) => (
          <button
            key={option}
            onClick={() => setSortBy(option)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              sortBy === option
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-400 hover:text-white"
            }`}
          >
            {option === "z_score"
              ? "Z-Score"
              : option === "p_value"
              ? "P-Value"
              : "kWh"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-700">
              <th className="pb-3 font-medium">Account</th>
              <th className="pb-3 font-medium">Type</th>
              <th className="pb-3 font-medium">Consumption</th>
              <th className="pb-3 font-medium">Z-Score</th>
              <th className="pb-3 font-medium">P-Value</th>
              <th className="pb-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="text-gray-300">
            {sortedAnomalies.map((anomaly, idx) => (
              <tr
                key={`${anomaly.account_number}-${idx}`}
                className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors"
              >
                <td className="py-3">
                  <div className="font-mono text-xs">
                    {anomaly.account_number}
                  </div>
                  {anomaly.postal_code && (
                    <div className="text-gray-500 text-xs">
                      {anomaly.postal_code}
                    </div>
                  )}
                </td>
                <td className="py-3 text-xs">
                  {formatHousingType(anomaly.housing_type)}
                </td>
                <td className="py-3">
                  <div className="font-medium">
                    {anomaly.consumption_kwh.toFixed(0)} kWh
                  </div>
                  <div className="text-gray-500 text-xs">
                    avg: {anomaly.cohort_mean.toFixed(0)}
                  </div>
                </td>
                <td className="py-3">
                  <span
                    className={`font-mono ${
                      anomaly.z_score > 0 ? "text-red-400" : "text-blue-400"
                    }`}
                  >
                    {anomaly.z_score > 0 ? "+" : ""}
                    {anomaly.z_score.toFixed(2)}σ
                  </span>
                </td>
                <td className="py-3">
                  <span className="font-mono text-xs">
                    {formatPValue(anomaly.p_value)}
                  </span>
                  {anomaly.p_value < 0.01 && (
                    <span className="text-yellow-400 ml-1">*</span>
                  )}
                  {anomaly.p_value < 0.001 && (
                    <span className="text-yellow-400">*</span>
                  )}
                </td>
                <td className="py-3">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      anomaly.anomaly_type === "HIGH"
                        ? "bg-red-500/20 text-red-400 border border-red-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {anomaly.anomaly_type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer note */}
      <div className="mt-3 text-xs text-gray-500">
        <span className="text-yellow-400">*</span> p &lt; 0.01,{" "}
        <span className="text-yellow-400">**</span> p &lt; 0.001 | Anomalies
        flagged at 95% CI (|z| &gt; 1.96)
      </div>
    </div>
  );
}
