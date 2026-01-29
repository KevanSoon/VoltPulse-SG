"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from "recharts";

interface MonthlyDataPoint {
  month: string;
  consumption_kwh: number;
  is_after_intervention: boolean;
}

interface InterventionData {
  intervention_id: string;
  intervention_type: string;
  intervention_date: string;
  before_avg_kwh: number;
  after_avg_kwh: number;
  consumption_change_percent: number;
  is_significant: boolean;
  p_value: number;
  monthly_data: MonthlyDataPoint[];
}

export default function InterventionTracker() {
  const [interventions, setInterventions] = useState<InterventionData[]>([]);
  const [selectedIntervention, setSelectedIntervention] =
    useState<InterventionData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInterventions();
  }, []);

  const fetchInterventions = async () => {
    setLoading(true);
    try {
      // In a real app, this would fetch from the API
      // For now, use mock data to demonstrate the component
      setInterventions(getMockInterventions());
      setSelectedIntervention(getMockInterventions()[0]);
    } catch (error) {
      console.error("Failed to fetch interventions:", error);
    } finally {
      setLoading(false);
    }
  };

  const getMockInterventions = (): InterventionData[] => [
    {
      intervention_id: "int_001",
      intervention_type: "led_retrofit",
      intervention_date: "2024-06-15",
      before_avg_kwh: 450,
      after_avg_kwh: 380,
      consumption_change_percent: -15.6,
      is_significant: true,
      p_value: 0.023,
      monthly_data: [
        { month: "2024-03", consumption_kwh: 465, is_after_intervention: false },
        { month: "2024-04", consumption_kwh: 442, is_after_intervention: false },
        { month: "2024-05", consumption_kwh: 458, is_after_intervention: false },
        { month: "2024-06", consumption_kwh: 430, is_after_intervention: false },
        { month: "2024-07", consumption_kwh: 395, is_after_intervention: true },
        { month: "2024-08", consumption_kwh: 378, is_after_intervention: true },
        { month: "2024-09", consumption_kwh: 372, is_after_intervention: true },
      ],
    },
    {
      intervention_id: "int_002",
      intervention_type: "cool_paint",
      intervention_date: "2024-04-01",
      before_avg_kwh: 520,
      after_avg_kwh: 465,
      consumption_change_percent: -10.6,
      is_significant: true,
      p_value: 0.041,
      monthly_data: [
        { month: "2024-01", consumption_kwh: 535, is_after_intervention: false },
        { month: "2024-02", consumption_kwh: 510, is_after_intervention: false },
        { month: "2024-03", consumption_kwh: 528, is_after_intervention: false },
        { month: "2024-04", consumption_kwh: 490, is_after_intervention: true },
        { month: "2024-05", consumption_kwh: 468, is_after_intervention: true },
        { month: "2024-06", consumption_kwh: 455, is_after_intervention: true },
      ],
    },
    {
      intervention_id: "int_003",
      intervention_type: "aircon_upgrade",
      intervention_date: "2024-05-20",
      before_avg_kwh: 380,
      after_avg_kwh: 355,
      consumption_change_percent: -6.6,
      is_significant: false,
      p_value: 0.12,
      monthly_data: [
        { month: "2024-02", consumption_kwh: 375, is_after_intervention: false },
        { month: "2024-03", consumption_kwh: 392, is_after_intervention: false },
        { month: "2024-04", consumption_kwh: 378, is_after_intervention: false },
        { month: "2024-05", consumption_kwh: 368, is_after_intervention: false },
        { month: "2024-06", consumption_kwh: 358, is_after_intervention: true },
        { month: "2024-07", consumption_kwh: 352, is_after_intervention: true },
      ],
    },
  ];

  const formatInterventionType = (type: string): string => {
    const mapping: Record<string, string> = {
      cool_paint: "Cool Paint",
      led_retrofit: "LED Retrofit",
      solar_panel: "Solar Panel",
      aircon_upgrade: "A/C Upgrade",
      insulation: "Insulation",
      smart_meter: "Smart Meter",
    };
    return mapping[type] || type.replace(/_/g, " ");
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white border border-teal-200 rounded-lg p-3 shadow-xl">
          <p className="text-slate-800 font-medium">{label}</p>
          <p className="text-slate-600 text-sm">
            Consumption:{" "}
            <span className="text-slate-800 font-medium">
              {data.consumption_kwh} kWh
            </span>
          </p>
          <p
            className={`text-xs mt-1 ${
              data.is_after_intervention ? "text-teal-600" : "text-slate-500"
            }`}
          >
            {data.is_after_intervention ? "After intervention" : "Before intervention"}
          </p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!selectedIntervention) {
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
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p>No interventions recorded yet</p>
        <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Record New Intervention
        </button>
      </div>
    );
  }

  const savings = selectedIntervention.before_avg_kwh - selectedIntervention.after_avg_kwh;
  const annualSavingsKwh = savings * 12;
  const annualSavingsSgd = annualSavingsKwh * 0.30; // Estimated rate

  return (
    <div className="space-y-4">
      {/* Intervention Selector */}
      <div className="flex items-center gap-2 flex-wrap">
        {interventions.map((intervention) => (
          <button
            key={intervention.intervention_id}
            onClick={() => setSelectedIntervention(intervention)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              selectedIntervention?.intervention_id === intervention.intervention_id
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            <span>{formatInterventionType(intervention.intervention_type)}</span>
            {intervention.is_significant && (
              <span className="w-2 h-2 bg-teal-400 rounded-full" title="Significant" />
            )}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={selectedIntervention.monthly_data}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="month"
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
            />
            <YAxis
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
              domain={["auto", "auto"]}
              label={{
                value: "kWh",
                angle: -90,
                position: "insideLeft",
                fill: "#9CA3AF",
                fontSize: 12,
              }}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Before average reference line */}
            <ReferenceLine
              y={selectedIntervention.before_avg_kwh}
              stroke="#FCD34D"
              strokeDasharray="5 5"
              strokeWidth={1.5}
            />

            {/* After average reference line */}
            <ReferenceLine
              y={selectedIntervention.after_avg_kwh}
              stroke="#34D399"
              strokeDasharray="5 5"
              strokeWidth={1.5}
            />

            {/* Intervention date vertical line */}
            <ReferenceLine
              x={selectedIntervention.intervention_date.substring(0, 7)}
              stroke="#EF4444"
              strokeDasharray="3 3"
              strokeWidth={2}
            />

            <Line
              type="monotone"
              dataKey="consumption_kwh"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={5}
                    fill={payload.is_after_intervention ? "#34D399" : "#3B82F6"}
                    stroke="#fff"
                    strokeWidth={2}
                  />
                );
              }}
              activeDot={{ r: 7, strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-red-500" style={{ borderStyle: "dashed" }} />
          <span>Intervention Date</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-yellow-400" />
          <span>Before Avg</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-teal-400" />
          <span>After Avg</span>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-teal-50 border border-teal-100 rounded-lg p-3">
          <p className="text-slate-500 text-xs">Before Average</p>
          <p className="text-xl font-bold text-yellow-600">
            {selectedIntervention.before_avg_kwh.toFixed(0)} kWh
          </p>
        </div>
        <div className="bg-teal-50 border border-teal-100 rounded-lg p-3">
          <p className="text-slate-500 text-xs">After Average</p>
          <p className="text-xl font-bold text-teal-600">
            {selectedIntervention.after_avg_kwh.toFixed(0)} kWh
          </p>
        </div>
        <div className="bg-teal-50 border border-teal-100 rounded-lg p-3">
          <p className="text-slate-500 text-xs">Change</p>
          <p
            className={`text-xl font-bold ${
              selectedIntervention.consumption_change_percent < 0
                ? "text-teal-600"
                : "text-red-500"
            }`}
          >
            {selectedIntervention.consumption_change_percent > 0 ? "+" : ""}
            {selectedIntervention.consumption_change_percent.toFixed(1)}%
          </p>
        </div>
        <div className="bg-teal-50 border border-teal-100 rounded-lg p-3">
          <p className="text-slate-500 text-xs">Statistical Significance</p>
          <p
            className={`text-lg font-bold ${
              selectedIntervention.is_significant
                ? "text-teal-600"
                : "text-slate-500"
            }`}
          >
            {selectedIntervention.is_significant ? (
              <>
                Yes <span className="text-sm font-normal">(p={selectedIntervention.p_value.toFixed(3)})</span>
              </>
            ) : (
              <>
                No <span className="text-sm font-normal">(p={selectedIntervention.p_value.toFixed(2)})</span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Projected savings */}
      {savings > 0 && selectedIntervention.is_significant && (
        <div className="bg-teal-500/10 border border-teal-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg
              className="w-5 h-5 text-teal-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-teal-400 font-medium">
              Statistically Significant Improvement
            </span>
          </div>
          <p className="text-gray-300 text-sm">
            Projected annual savings:{" "}
            <span className="text-white font-medium">
              {annualSavingsKwh.toFixed(0)} kWh
            </span>{" "}
            (~
            <span className="text-teal-400 font-medium">
              S${annualSavingsSgd.toFixed(0)}
            </span>
            /year)
          </p>
        </div>
      )}
    </div>
  );
}
