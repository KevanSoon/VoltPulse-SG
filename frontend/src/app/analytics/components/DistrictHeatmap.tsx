"use client";

import { useEffect, useState } from "react";

interface HeatmapPoint {
  postal_district: string;
  district_name?: string;
  latitude: number;
  longitude: number;
  consumption_kwh: number;
  intensity: number;
  household_count: number;
}

interface DistrictHeatmapProps {
  dateRange?: { start: Date; end: Date } | null;
}

export default function DistrictHeatmap({ dateRange }: DistrictHeatmapProps) {
  const [heatmapData, setHeatmapData] = useState<HeatmapPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDistrict, setSelectedDistrict] = useState<HeatmapPoint | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHeatmapData();
  }, [dateRange]);

  const fetchHeatmapData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (dateRange?.start)
        params.append("start_date", dateRange.start.toISOString().split("T")[0]);
      if (dateRange?.end)
        params.append("end_date", dateRange.end.toISOString().split("T")[0]);

      const response = await fetch(`/api/analytics/districts/heatmap?${params}`);
      if (!response.ok) {
        throw new Error("Failed to fetch heatmap data");
      }
      const data = await response.json();
      setHeatmapData(data.heatmap_points || []);
    } catch (err) {
      console.error("Failed to fetch heatmap data:", err);
      setError("Unable to load heatmap data");
      // Set mock data for demonstration
      setHeatmapData(getMockHeatmapData());
    } finally {
      setLoading(false);
    }
  };

  const getMockHeatmapData = (): HeatmapPoint[] => [
    { postal_district: "01", district_name: "CBD", latitude: 1.2819, longitude: 103.8511, consumption_kwh: 520, intensity: 0.85, household_count: 45 },
    { postal_district: "03", district_name: "Queenstown", latitude: 1.2897, longitude: 103.8067, consumption_kwh: 380, intensity: 0.62, household_count: 120 },
    { postal_district: "12", district_name: "Toa Payoh", latitude: 1.3350, longitude: 103.8550, consumption_kwh: 320, intensity: 0.52, household_count: 180 },
    { postal_district: "20", district_name: "Bishan", latitude: 1.3650, longitude: 103.8500, consumption_kwh: 340, intensity: 0.55, household_count: 150 },
    { postal_district: "22", district_name: "Jurong", latitude: 1.3350, longitude: 103.7050, consumption_kwh: 290, intensity: 0.47, household_count: 200 },
    { postal_district: "27", district_name: "Yishun", latitude: 1.4300, longitude: 103.8350, consumption_kwh: 310, intensity: 0.50, household_count: 220 },
    { postal_district: "18", district_name: "Tampines", latitude: 1.3550, longitude: 103.9450, consumption_kwh: 350, intensity: 0.57, household_count: 190 },
    { postal_district: "55", district_name: "Sengkang", latitude: 1.3900, longitude: 103.8950, consumption_kwh: 300, intensity: 0.49, household_count: 210 },
    { postal_district: "10", district_name: "Bukit Timah", latitude: 1.3055, longitude: 103.8200, consumption_kwh: 580, intensity: 0.95, household_count: 35 },
  ];

  const getColor = (intensity: number) => {
    if (intensity < 0.33) return "rgba(34, 197, 94, 0.7)"; // Green
    if (intensity < 0.66) return "rgba(234, 179, 8, 0.7)"; // Yellow
    return "rgba(239, 68, 68, 0.7)"; // Red
  };

  const getBorderColor = (intensity: number) => {
    if (intensity < 0.33) return "rgb(34, 197, 94)";
    if (intensity < 0.66) return "rgb(234, 179, 8)";
    return "rgb(239, 68, 68)";
  };

  // Convert lat/lng to SVG coordinates (simplified projection for Singapore)
  const toSvgCoords = (lat: number, lng: number) => {
    // Singapore bounds approximately: lat 1.15-1.47, lng 103.6-104.05
    const minLat = 1.15, maxLat = 1.47;
    const minLng = 103.6, maxLng = 104.05;

    const x = ((lng - minLng) / (maxLng - minLng)) * 100;
    const y = 100 - ((lat - minLat) / (maxLat - minLat)) * 100;

    return { x, y };
  };

  if (loading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="relative">
      {/* SVG Map Container */}
      <div className="relative h-80 bg-slate-100 rounded-lg overflow-hidden border border-slate-200">
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Background grid */}
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path
                d="M 10 0 L 0 0 0 10"
                fill="none"
                stroke="rgba(75, 85, 99, 0.3)"
                strokeWidth="0.2"
              />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid)" />

          {/* Singapore outline (simplified) */}
          <path
            d="M 20 70 Q 25 65 35 60 Q 45 55 55 52 Q 65 50 75 48 Q 85 50 88 55 Q 90 60 85 65 Q 80 72 70 75 Q 60 78 50 77 Q 40 76 30 74 Q 25 73 20 70 Z"
            fill="rgba(55, 65, 81, 0.5)"
            stroke="rgba(107, 114, 128, 0.5)"
            strokeWidth="0.5"
          />

          {/* Heatmap circles */}
          {heatmapData.map((point) => {
            const { x, y } = toSvgCoords(point.latitude, point.longitude);
            const radius = 2 + point.intensity * 4;

            return (
              <g key={point.postal_district}>
                {/* Glow effect */}
                <circle
                  cx={x}
                  cy={y}
                  r={radius + 1.5}
                  fill={getColor(point.intensity)}
                  opacity={0.3}
                />
                {/* Main circle */}
                <circle
                  cx={x}
                  cy={y}
                  r={radius}
                  fill={getColor(point.intensity)}
                  stroke={getBorderColor(point.intensity)}
                  strokeWidth="0.3"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(point)}
                />
                {/* District label */}
                <text
                  x={x}
                  y={y + 0.5}
                  textAnchor="middle"
                  fontSize="2"
                  fill="white"
                  fontWeight="bold"
                  className="pointer-events-none"
                >
                  {point.postal_district}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-white/95 border border-slate-200 rounded-lg p-3 backdrop-blur-sm">
          <p className="text-xs text-slate-600 mb-2 font-medium">
            Consumption Intensity
          </p>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-teal-500/70" />
              <span className="text-xs text-slate-700">Low</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
              <span className="text-xs text-slate-700">Medium</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-red-500/70" />
              <span className="text-xs text-slate-700">High</span>
            </div>
          </div>
        </div>

        {/* Selected District Info */}
        {selectedDistrict && (
          <div className="absolute top-3 right-3 bg-white/95 border border-slate-200 rounded-lg p-4 backdrop-blur-sm max-w-xs">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-slate-800 font-semibold">
                District {selectedDistrict.postal_district}
              </h4>
              <button
                onClick={() => setSelectedDistrict(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {selectedDistrict.district_name && (
              <p className="text-slate-500 text-sm mb-2">
                {selectedDistrict.district_name}
              </p>
            )}
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Avg. Consumption:</span>
                <span className="text-slate-800 font-medium">
                  {selectedDistrict.consumption_kwh.toFixed(0)} kWh
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Households:</span>
                <span className="text-slate-800 font-medium">
                  {selectedDistrict.household_count}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Intensity:</span>
                <span className={`font-medium ${
                  selectedDistrict.intensity > 0.66 ? "text-red-500" :
                  selectedDistrict.intensity > 0.33 ? "text-yellow-500" : "text-teal-600"
                }`}>
                  {(selectedDistrict.intensity * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* District list below map */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
        {heatmapData.slice(0, 8).map((point) => (
          <button
            key={point.postal_district}
            onClick={() => setSelectedDistrict(point)}
            className={`p-2 rounded-lg text-left transition-colors ${
              selectedDistrict?.postal_district === point.postal_district
                ? "bg-teal-100 border border-teal-400"
                : "bg-white border border-slate-200 hover:border-teal-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: getBorderColor(point.intensity) }}
              />
              <span className="text-slate-800 text-sm font-medium">
                D{point.postal_district}
              </span>
            </div>
            <p className="text-slate-500 text-xs mt-1 truncate">
              {point.consumption_kwh.toFixed(0)} kWh avg
            </p>
          </button>
        ))}
      </div>

      {error && (
        <p className="text-yellow-500 text-xs mt-2 text-center">
          {error} - Showing demo data
        </p>
      )}
    </div>
  );
}
