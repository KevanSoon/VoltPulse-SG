"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ErrorBar,
} from "recharts";

interface CohortStats {
  housing_type: string;
  sample_size: number;
  mean_kwh: number;
  std_dev_kwh: number;
  ci_lower: number;
  ci_upper: number;
}

interface ChartData {
  name: string;
  mean: number;
  errorLower: number;
  errorUpper: number;
  samples: number;
  fullName: string;
}

export default function CohortChart() {
  const [cohortData, setCohortData] = useState<CohortStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCohortStats();
  }, []);

  const fetchCohortStats = async () => {
    try {
      const response = await fetch("/api/analytics/anomalies/cohorts");
      if (!response.ok) throw new Error("Failed to fetch");
      const data = await response.json();
      setCohortData(data);
    } catch (error) {
      console.error("Failed to fetch cohort stats:", error);
      // Set mock data
      setCohortData(getMockCohortData());
    } finally {
      setLoading(false);
    }
  };

  const getMockCohortData = (): CohortStats[] => [
    { housing_type: "hdb_3_room", sample_size: 45, mean_kwh: 265, std_dev_kwh: 55, ci_lower: 157, ci_upper: 373 },
    { housing_type: "hdb_4_room", sample_size: 78, mean_kwh: 340, std_dev_kwh: 85, ci_lower: 173, ci_upper: 507 },
    { housing_type: "hdb_5_room", sample_size: 32, mean_kwh: 420, std_dev_kwh: 95, ci_lower: 234, ci_upper: 606 },
    { housing_type: "condo", sample_size: 25, mean_kwh: 480, std_dev_kwh: 120, ci_lower: 245, ci_upper: 715 },
    { housing_type: "landed", sample_size: 12, mean_kwh: 1150, std_dev_kwh: 280, ci_lower: 601, ci_upper: 1699 },
  ];

  const formatHousingType = (type: string): string => {
    const mapping: Record<string, string> = {
      hdb_1_2_room: "HDB 1-2R",
      hdb_3_room: "HDB 3R",
      hdb_4_room: "HDB 4R",
      hdb_5_room: "HDB 5R",
      hdb_executive: "HDB Exec",
      condo: "Condo",
      landed: "Landed",
      commercial: "Commercial",
      unknown: "Unknown",
    };
    return mapping[type] || type;
  };

  const getBarColor = (mean: number): string => {
    if (mean < 300) return "#22c55e"; // Green
    if (mean < 500) return "#eab308"; // Yellow
    return "#ef4444"; // Red
  };

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  // Transform data for Recharts
  const chartData: ChartData[] = cohortData.map((cohort) => ({
    name: formatHousingType(cohort.housing_type),
    fullName: cohort.housing_type,
    mean: cohort.mean_kwh,
    errorLower: cohort.mean_kwh - cohort.ci_lower,
    errorUpper: cohort.ci_upper - cohort.mean_kwh,
    samples: cohort.sample_size,
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const cohort = cohortData.find(
        (c) => formatHousingType(c.housing_type) === data.name
      );

      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-xl">
          <p className="text-white font-semibold mb-2">{data.name}</p>
          <div className="space-y-1 text-sm">
            <p className="text-gray-300">
              Mean: <span className="text-white font-medium">{data.mean.toFixed(0)} kWh</span>
            </p>
            {cohort && (
              <>
                <p className="text-gray-300">
                  Std Dev: <span className="text-white">{cohort.std_dev_kwh.toFixed(0)} kWh</span>
                </p>
                <p className="text-gray-300">
                  95% CI: <span className="text-blue-400">[{cohort.ci_lower.toFixed(0)}, {cohort.ci_upper.toFixed(0)}]</span>
                </p>
                <p className="text-gray-300">
                  Samples: <span className="text-white">{cohort.sample_size}</span>
                </p>
              </>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="name"
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              axisLine={{ stroke: "#4B5563" }}
            />
            <YAxis
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              axisLine={{ stroke: "#4B5563" }}
              label={{
                value: "Mean kWh",
                angle: -90,
                position: "insideLeft",
                fill: "#9CA3AF",
                fontSize: 12,
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="mean" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.mean)} />
              ))}
              <ErrorBar
                dataKey="errorUpper"
                width={6}
                strokeWidth={2}
                stroke="#60A5FA"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend and explanation */}
      <div className="mt-4 flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500" />
            <span className="text-gray-400">&lt;300 kWh</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-yellow-500" />
            <span className="text-gray-400">300-500 kWh</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-red-500" />
            <span className="text-gray-400">&gt;500 kWh</span>
          </div>
        </div>
        <div className="flex items-center gap-1 text-gray-500">
          <div className="w-4 h-0.5 bg-blue-400" />
          <span>95% CI (1.96σ)</span>
        </div>
      </div>

      {/* Stats summary */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        {cohortData.slice(0, 3).map((cohort) => (
          <div
            key={cohort.housing_type}
            className="bg-gray-700/30 rounded-lg p-2 text-center"
          >
            <p className="text-white font-medium text-sm">
              {formatHousingType(cohort.housing_type)}
            </p>
            <p className="text-gray-400 text-xs">
              n={cohort.sample_size}, μ={cohort.mean_kwh.toFixed(0)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
