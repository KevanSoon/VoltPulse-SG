"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

// Mock monthly consumption data
const MONTHLY_DATA = [
  { month: "Jan", consumption: 385, average: 400 },
  { month: "Feb", consumption: 362, average: 400 },
  { month: "Mar", consumption: 410, average: 400 },
  { month: "Apr", consumption: 445, average: 400 },
  { month: "May", consumption: 478, average: 400 },
  { month: "Jun", consumption: 520, average: 400 },
  { month: "Jul", consumption: 535, average: 400 },
  { month: "Aug", consumption: 498, average: 400 },
  { month: "Sep", consumption: 456, average: 400 },
  { month: "Oct", consumption: 412, average: 400 },
  { month: "Nov", consumption: 378, average: 400 },
  { month: "Dec", consumption: 395, average: 400 },
];

function getBarColor(consumption: number, average: number): string {
  if (consumption <= average * 0.9) return "#22c55e"; // green - good
  if (consumption <= average * 1.1) return "#eab308"; // yellow - average
  return "#ef4444"; // red - high
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const diff = data.consumption - data.average;
    const diffPercent = ((diff / data.average) * 100).toFixed(1);

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
        <p className="font-semibold text-gray-900">{label}</p>
        <p className="text-gray-600 text-sm mt-1">
          Consumption: <span className="font-medium text-gray-900">{data.consumption} kWh</span>
        </p>
        <p className="text-gray-600 text-sm">
          National Avg: <span className="font-medium">{data.average} kWh</span>
        </p>
        <p className={`text-sm mt-1 font-medium ${diff > 0 ? "text-red-600" : "text-green-600"}`}>
          {diff > 0 ? "+" : ""}{diff} kWh ({diff > 0 ? "+" : ""}{diffPercent}%)
        </p>
      </div>
    );
  }
  return null;
}

export default function MonthlyConsumptionChart() {
  // Calculate yearly stats
  const totalConsumption = MONTHLY_DATA.reduce((sum, d) => sum + d.consumption, 0);
  const avgMonthly = Math.round(totalConsumption / 12);
  const highestMonth = MONTHLY_DATA.reduce((max, d) => d.consumption > max.consumption ? d : max);
  const lowestMonth = MONTHLY_DATA.reduce((min, d) => d.consumption < min.consumption ? d : min);

  return (
    <div className="space-y-4">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={MONTHLY_DATA}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="month"
              stroke="#6b7280"
              tick={{ fontSize: 12, fill: "#6b7280" }}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 12, fill: "#6b7280" }}
              label={{
                value: "kWh",
                angle: -90,
                position: "insideLeft",
                fill: "#6b7280",
                fontSize: 12,
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={400}
              stroke="#9ca3af"
              strokeDasharray="5 5"
              label={{ value: "Avg", position: "right", fill: "#9ca3af", fontSize: 11 }}
            />
            <Bar
              dataKey="consumption"
              radius={[4, 4, 0, 0]}
              fill="#22c55e"
              // Dynamic coloring based on consumption vs average
              shape={(props: any) => {
                const { x, y, width, height, consumption, average } = props;
                const color = getBarColor(consumption, average);
                return (
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={color}
                    rx={4}
                    ry={4}
                  />
                );
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span>Below Average</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-yellow-500" />
          <span>Average</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span>Above Average</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-gray-400" style={{ borderStyle: "dashed" }} />
          <span>National Avg (400 kWh)</span>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Yearly Total</p>
          <p className="text-lg font-bold text-gray-900">{totalConsumption.toLocaleString()} kWh</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Lowest Month</p>
          <p className="text-lg font-bold text-green-600">{lowestMonth.month}</p>
          <p className="text-xs text-gray-500">{lowestMonth.consumption} kWh</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Highest Month</p>
          <p className="text-lg font-bold text-red-600">{highestMonth.month}</p>
          <p className="text-xs text-gray-500">{highestMonth.consumption} kWh</p>
        </div>
      </div>
    </div>
  );
}
