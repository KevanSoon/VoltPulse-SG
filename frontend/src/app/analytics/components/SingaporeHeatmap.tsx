"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

// Singapore district consumption data (hardcoded for now)
const SINGAPORE_CONSUMPTION_DATA = [
  { name: "Raffles Place", lat: 1.2830, lng: 103.8513, consumption: 850, district: "01" },
  { name: "Tanjong Pagar", lat: 1.2763, lng: 103.8445, consumption: 720, district: "02" },
  { name: "Queenstown", lat: 1.2942, lng: 103.7861, consumption: 480, district: "03" },
  { name: "Telok Blangah", lat: 1.2707, lng: 103.8090, consumption: 520, district: "04" },
  { name: "Pasir Panjang", lat: 1.2763, lng: 103.7689, consumption: 390, district: "05" },
  { name: "City Hall", lat: 1.2931, lng: 103.8520, consumption: 780, district: "06" },
  { name: "Beach Road", lat: 1.3012, lng: 103.8637, consumption: 650, district: "07" },
  { name: "Little India", lat: 1.3066, lng: 103.8518, consumption: 580, district: "08" },
  { name: "Orchard", lat: 1.3048, lng: 103.8318, consumption: 920, district: "09" },
  { name: "Tanglin", lat: 1.3058, lng: 103.8140, consumption: 680, district: "10" },
  { name: "Novena", lat: 1.3205, lng: 103.8439, consumption: 510, district: "11" },
  { name: "Toa Payoh", lat: 1.3343, lng: 103.8563, consumption: 420, district: "12" },
  { name: "Macpherson", lat: 1.3284, lng: 103.8899, consumption: 380, district: "13" },
  { name: "Geylang", lat: 1.3201, lng: 103.8918, consumption: 450, district: "14" },
  { name: "East Coast", lat: 1.3025, lng: 103.9123, consumption: 620, district: "15" },
  { name: "Bedok", lat: 1.3236, lng: 103.9273, consumption: 350, district: "16" },
  { name: "Changi", lat: 1.3644, lng: 103.9915, consumption: 290, district: "17" },
  { name: "Tampines", lat: 1.3496, lng: 103.9568, consumption: 380, district: "18" },
  { name: "Serangoon", lat: 1.3554, lng: 103.8679, consumption: 410, district: "19" },
  { name: "Bishan", lat: 1.3526, lng: 103.8352, consumption: 440, district: "20" },
  { name: "Clementi", lat: 1.3162, lng: 103.7649, consumption: 360, district: "21" },
  { name: "Jurong", lat: 1.3329, lng: 103.7436, consumption: 550, district: "22" },
  { name: "Bukit Batok", lat: 1.3590, lng: 103.7637, consumption: 390, district: "23" },
  { name: "Woodlands", lat: 1.4382, lng: 103.7890, consumption: 340, district: "25" },
  { name: "Yishun", lat: 1.4304, lng: 103.8354, consumption: 370, district: "27" },
  { name: "Seletar", lat: 1.4049, lng: 103.8679, consumption: 280, district: "28" },
];

interface HeatmapProps {
  dateRange?: { start: Date; end: Date } | null;
}

// Dynamic import for Leaflet components to avoid SSR issues
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
);

const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
);

const CircleMarker = dynamic(
  () => import("react-leaflet").then((mod) => mod.CircleMarker),
  { ssr: false }
);

const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false }
);

function HeatmapLegend() {
  return (
    <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
      <p className="text-xs font-medium text-gray-700 mb-2">Consumption Level</p>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-green-500"></div>
          <span className="text-xs text-gray-600">Low (&lt;400 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
          <span className="text-xs text-gray-600">Medium (400-600 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-orange-500"></div>
          <span className="text-xs text-gray-600">High (600-800 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-red-500"></div>
          <span className="text-xs text-gray-600">Very High (&gt;800 kWh)</span>
        </div>
      </div>
    </div>
  );
}

function getConsumptionColor(consumption: number): string {
  if (consumption < 400) return "#22c55e"; // green-500
  if (consumption < 600) return "#eab308"; // yellow-500
  if (consumption < 800) return "#f97316"; // orange-500
  return "#ef4444"; // red-500
}

function getConsumptionRadius(consumption: number): number {
  // Scale radius based on consumption (min 8, max 25)
  return Math.min(25, Math.max(8, consumption / 40));
}

export default function SingaporeHeatmap({ dateRange }: HeatmapProps) {
  const [mounted, setMounted] = useState(false);
  const [selectedDistrict, setSelectedDistrict] = useState<typeof SINGAPORE_CONSUMPTION_DATA[0] | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="h-[400px] bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  // Calculate stats
  const avgConsumption = Math.round(
    SINGAPORE_CONSUMPTION_DATA.reduce((sum, d) => sum + d.consumption, 0) / SINGAPORE_CONSUMPTION_DATA.length
  );
  const maxConsumption = Math.max(...SINGAPORE_CONSUMPTION_DATA.map(d => d.consumption));
  const minConsumption = Math.min(...SINGAPORE_CONSUMPTION_DATA.map(d => d.consumption));

  return (
    <div className="space-y-4">
      <div className="relative h-[400px] rounded-lg overflow-hidden border border-gray-200">
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
        <MapContainer
          center={[1.3521, 103.8198]}
          zoom={11}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {SINGAPORE_CONSUMPTION_DATA.map((location) => (
            <CircleMarker
              key={location.district}
              center={[location.lat, location.lng]}
              radius={getConsumptionRadius(location.consumption)}
              pathOptions={{
                fillColor: getConsumptionColor(location.consumption),
                fillOpacity: 0.7,
                color: getConsumptionColor(location.consumption),
                weight: 2,
              }}
              eventHandlers={{
                click: () => setSelectedDistrict(location),
              }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold text-gray-900">{location.name}</p>
                  <p className="text-gray-600">District {location.district}</p>
                  <p className="text-gray-900 font-medium mt-1">
                    {location.consumption} kWh/month
                  </p>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
        <HeatmapLegend />
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Lowest</p>
          <p className="text-lg font-bold text-green-600">{minConsumption} kWh</p>
          <p className="text-xs text-gray-500">
            {SINGAPORE_CONSUMPTION_DATA.find(d => d.consumption === minConsumption)?.name}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Average</p>
          <p className="text-lg font-bold text-gray-700">{avgConsumption} kWh</p>
          <p className="text-xs text-gray-500">Across all districts</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Highest</p>
          <p className="text-lg font-bold text-red-600">{maxConsumption} kWh</p>
          <p className="text-xs text-gray-500">
            {SINGAPORE_CONSUMPTION_DATA.find(d => d.consumption === maxConsumption)?.name}
          </p>
        </div>
      </div>

      {/* Selected District Details */}
      {selectedDistrict && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-semibold text-gray-900">{selectedDistrict.name}</h4>
              <p className="text-sm text-gray-500">District {selectedDistrict.district}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{selectedDistrict.consumption} kWh</p>
              <p className="text-sm text-gray-500">Monthly avg</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: getConsumptionColor(selectedDistrict.consumption) }}
            />
            <span className="text-sm text-gray-600">
              {selectedDistrict.consumption < 400
                ? "Below average consumption"
                : selectedDistrict.consumption < 600
                ? "Average consumption"
                : selectedDistrict.consumption < 800
                ? "Above average consumption"
                : "High consumption area"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
