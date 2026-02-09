"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import type { FeatureCollection } from "geojson";
import type L from "leaflet";

interface PlanningAreaProperties {
  OBJECTID_1: number;
  PLN_AREA_N: string;
  REGION_N: string;
  TOTAL: number;
  ONE_TO_TWO_RM: number;
  THREE_RM: number;
  FOUR_RM: number;
  FIVE_RM_EXEC_FLATS: number;
}

interface SelectedArea {
  name: string;
  region: string;
  total: number;
  oneToTwoRm: number;
  threeRm: number;
  fourRm: number;
  fiveRmExec: number;
}

export interface HeatmapDataPoint {
  name: string;
  lat: number;
  lng: number;
  consumption: number;
  district: string;
  household_count?: number;
}

interface HeatmapProps {
  dateRange?: { start: Date; end: Date } | null;
  fullHeight?: boolean;
  data?: HeatmapDataPoint[];
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

const GeoJSONLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.GeoJSON),
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

function titleCase(str: string): string {
  return str
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getConsumptionColor(consumption: number): string {
  if (consumption === 0) return "#d1d5db"; // gray-300 for non-residential
  if (consumption < 300) return "#14b8a6"; // teal-500
  if (consumption < 350) return "#22c55e"; // green-500
  if (consumption < 400) return "#eab308"; // yellow-500
  if (consumption < 450) return "#f97316"; // orange-500
  return "#ef4444"; // red-500
}

function HeatmapLegend() {
  return (
    <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
      <p className="text-xs font-medium text-gray-700 mb-2">
        Avg Monthly Household Consumption (kWh)
      </p>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#d1d5db" }} />
          <span className="text-xs text-gray-600">No data</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#14b8a6" }} />
          <span className="text-xs text-gray-600">Low (&lt;300 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#22c55e" }} />
          <span className="text-xs text-gray-600">Below Avg (300-350 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#eab308" }} />
          <span className="text-xs text-gray-600">Average (350-400 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#f97316" }} />
          <span className="text-xs text-gray-600">Above Avg (400-450 kWh)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#ef4444" }} />
          <span className="text-xs text-gray-600">High (&gt;450 kWh)</span>
        </div>
      </div>
    </div>
  );
}

export default function SingaporeHeatmap({ dateRange, fullHeight = false, data }: HeatmapProps) {
  const [mounted, setMounted] = useState(false);
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null);
  const [geoLoading, setGeoLoading] = useState(true);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [selectedArea, setSelectedArea] = useState<SelectedArea | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch GeoJSON data from data.gov.sg API
  useEffect(() => {
    let cancelled = false;

    async function fetchGeoJSON() {
      setGeoLoading(true);
      setGeoError(null);

      try {
        const datasetId = "d_634194a40f36e5bc11a942ab0164fa9d";
        const pollUrl =
          "https://api-open.data.gov.sg/v1/public/api/datasets/" +
          datasetId +
          "/poll-download";

        const pollResponse = await fetch(pollUrl);
        if (!pollResponse.ok) throw new Error("Failed to fetch poll-download data");

        const pollJson = await pollResponse.json();
        if (pollJson.code !== 0 || !pollJson.data?.url) {
          throw new Error(pollJson.errMsg || "Invalid poll response");
        }

        const dataResponse = await fetch(pollJson.data.url);
        if (!dataResponse.ok) throw new Error("Failed to fetch GeoJSON data");

        const featureCollection = await dataResponse.json();

        if (!cancelled) {
          setGeoData(featureCollection as FeatureCollection);
        }
      } catch (err) {
        console.error("GeoJSON fetch error:", err);
        if (!cancelled) {
          setGeoError("Failed to load planning area data");
        }
      } finally {
        if (!cancelled) {
          setGeoLoading(false);
        }
      }
    }

    fetchGeoJSON();

    return () => {
      cancelled = true;
    };
  }, []);

  const useGeoJSONMode = !data;

  // Compute stats from GeoJSON data
  const residentialFeatures = geoData
    ? geoData.features.filter(
        (f) => (f.properties as PlanningAreaProperties).TOTAL > 0
      )
    : [];

  const geoAvg =
    residentialFeatures.length > 0
      ? Math.round(
          residentialFeatures.reduce(
            (sum, f) => sum + (f.properties as PlanningAreaProperties).TOTAL,
            0
          ) / residentialFeatures.length
        )
      : 0;

  const geoMaxFeature =
    residentialFeatures.length > 0
      ? residentialFeatures.reduce((max, f) =>
          (f.properties as PlanningAreaProperties).TOTAL >
          (max.properties as PlanningAreaProperties).TOTAL
            ? f
            : max
        )
      : null;

  const geoMinFeature =
    residentialFeatures.length > 0
      ? residentialFeatures.reduce((min, f) =>
          (f.properties as PlanningAreaProperties).TOTAL <
          (min.properties as PlanningAreaProperties).TOTAL
            ? f
            : min
        )
      : null;

  const geoMax = geoMaxFeature
    ? (geoMaxFeature.properties as PlanningAreaProperties).TOTAL
    : 0;
  const geoMin = geoMinFeature
    ? (geoMinFeature.properties as PlanningAreaProperties).TOTAL
    : 0;
  const geoMaxName = geoMaxFeature
    ? titleCase((geoMaxFeature.properties as PlanningAreaProperties).PLN_AREA_N)
    : "";
  const geoMinName = geoMinFeature
    ? titleCase((geoMinFeature.properties as PlanningAreaProperties).PLN_AREA_N)
    : "";

  // Fallback stats for data prop mode
  const mapData: HeatmapDataPoint[] = data || [];
  const dataAvg = mapData.length > 0
    ? Math.round(mapData.reduce((sum, d) => sum + d.consumption, 0) / mapData.length)
    : 0;
  const dataMax = mapData.length > 0 ? Math.max(...mapData.map((d) => d.consumption)) : 0;
  const dataMin = mapData.length > 0 ? Math.min(...mapData.map((d) => d.consumption)) : 0;

  const onEachFeature = useCallback(
    (feature: GeoJSON.Feature, layer: L.Layer) => {
      const props = feature.properties as PlanningAreaProperties;
      const name = props.PLN_AREA_N;
      const total = props.TOTAL;

      layer.bindTooltip(
        `<strong>${titleCase(name)}</strong><br/>${
          total > 0 ? `${total} kWh/month` : "No residential data"
        }`,
        { sticky: true }
      );

      layer.on("click", () => {
        setSelectedArea({
          name: titleCase(name),
          region: titleCase(props.REGION_N),
          total: props.TOTAL,
          oneToTwoRm: props.ONE_TO_TWO_RM,
          threeRm: props.THREE_RM,
          fourRm: props.FOUR_RM,
          fiveRmExec: props.FIVE_RM_EXEC_FLATS,
        });
      });

      layer.on("mouseover", () => {
        (layer as L.Path).setStyle({
          weight: 3,
          fillOpacity: total > 0 ? 0.8 : 0.3,
        });
      });
      layer.on("mouseout", () => {
        (layer as L.Path).setStyle({
          weight: 1,
          fillOpacity: total > 0 ? 0.6 : 0.15,
        });
      });
    },
    []
  );

  if (!mounted) {
    return (
      <div
        className={`${
          fullHeight ? "h-full" : "h-[400px]"
        } bg-gray-100 rounded-lg flex items-center justify-center`}
      >
        <div className="animate-spin w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const mapContent = (
    <>
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossOrigin=""
      />
      <MapContainer
        key="singapore-heatmap"
        center={[1.3521, 103.8198]}
        zoom={11}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
      >
        <TileLayer
          key="osm-tile-layer"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {/* GeoJSON polygon mode (default) */}
        {useGeoJSONMode && geoData && (
          <GeoJSONLayer
            key="geojson-layer"
            data={geoData}
            style={(feature) => {
              const total =
                (feature?.properties as PlanningAreaProperties)?.TOTAL ?? 0;
              return {
                fillColor: getConsumptionColor(total),
                fillOpacity: total > 0 ? 0.6 : 0.15,
                color: "#374151",
                weight: 1,
                opacity: 0.8,
              };
            }}
            onEachFeature={onEachFeature}
          />
        )}
        {/* CircleMarker mode (when data prop is provided) */}
        {!useGeoJSONMode &&
          mapData.map((location, index) => (
            <CircleMarker
              key={`district-${location.district}-${index}`}
              center={[location.lat, location.lng]}
              radius={Math.min(25, Math.max(8, location.consumption / 40))}
              pathOptions={{
                fillColor: getConsumptionColor(location.consumption),
                fillOpacity: 0.7,
                color: getConsumptionColor(location.consumption),
                weight: 2,
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

      {/* Loading overlay */}
      {useGeoJSONMode && geoLoading && (
        <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-2 z-[1000] flex items-center gap-2">
          <div className="animate-spin w-4 h-4 border-2 border-teal-500 border-t-transparent rounded-full" />
          <span className="text-xs text-gray-600">Loading area data...</span>
        </div>
      )}

      {/* Error overlay */}
      {useGeoJSONMode && geoError && (
        <div className="absolute top-4 left-4 bg-red-50 border border-red-200 rounded-lg p-2 z-[1000]">
          <span className="text-xs text-red-600">{geoError}</span>
        </div>
      )}

      <HeatmapLegend />
    </>
  );

  // Full height mode - just the map filling the container
  if (fullHeight) {
    return (
      <div className="relative h-full rounded-lg overflow-hidden border border-gray-200">
        {mapContent}
      </div>
    );
  }

  // Normal mode with stats below
  return (
    <div className="space-y-4">
      <div className="relative h-[400px] rounded-lg overflow-hidden border border-gray-200">
        {mapContent}
      </div>

      {/* Summary Stats */}
      {useGeoJSONMode && residentialFeatures.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-teal-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Lowest</p>
            <p className="text-lg font-bold text-teal-600">{geoMin} kWh</p>
            <p className="text-xs text-gray-500">{geoMinName}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Average</p>
            <p className="text-lg font-bold text-gray-700">{geoAvg} kWh</p>
            <p className="text-xs text-gray-500">
              Across {residentialFeatures.length} areas
            </p>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Highest</p>
            <p className="text-lg font-bold text-red-600">{geoMax} kWh</p>
            <p className="text-xs text-gray-500">{geoMaxName}</p>
          </div>
        </div>
      )}

      {!useGeoJSONMode && mapData.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-teal-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Lowest</p>
            <p className="text-lg font-bold text-teal-600">{dataMin} kWh</p>
            <p className="text-xs text-gray-500">
              {mapData.find((d) => d.consumption === dataMin)?.name}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Average</p>
            <p className="text-lg font-bold text-gray-700">{dataAvg} kWh</p>
            <p className="text-xs text-gray-500">
              Across {mapData.length} districts
            </p>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">Highest</p>
            <p className="text-lg font-bold text-red-600">{dataMax} kWh</p>
            <p className="text-xs text-gray-500">
              {mapData.find((d) => d.consumption === dataMax)?.name}
            </p>
          </div>
        </div>
      )}

      {/* Selected Area Details (GeoJSON mode) */}
      {useGeoJSONMode && selectedArea && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-semibold text-gray-900">{selectedArea.name}</h4>
              <p className="text-sm text-gray-500">{selectedArea.region}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">
                {selectedArea.total > 0 ? `${selectedArea.total} kWh` : "N/A"}
              </p>
              <p className="text-sm text-gray-500">Monthly avg (all types)</p>
            </div>
          </div>
          {selectedArea.total > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {selectedArea.oneToTwoRm > 0 && (
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-gray-500 text-xs">1-2 Room</p>
                  <p className="font-medium">{selectedArea.oneToTwoRm} kWh</p>
                </div>
              )}
              {selectedArea.threeRm > 0 && (
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-gray-500 text-xs">3 Room</p>
                  <p className="font-medium">{selectedArea.threeRm} kWh</p>
                </div>
              )}
              {selectedArea.fourRm > 0 && (
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-gray-500 text-xs">4 Room</p>
                  <p className="font-medium">{selectedArea.fourRm} kWh</p>
                </div>
              )}
              {selectedArea.fiveRmExec > 0 && (
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-gray-500 text-xs">5 Room / Exec</p>
                  <p className="font-medium">{selectedArea.fiveRmExec} kWh</p>
                </div>
              )}
            </div>
          )}
          <div className="mt-3 flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: getConsumptionColor(selectedArea.total) }}
            />
            <span className="text-sm text-gray-600">
              {selectedArea.total === 0
                ? "Non-residential area"
                : selectedArea.total < 350
                ? "Below average consumption"
                : selectedArea.total < 400
                ? "Average consumption"
                : "Above average consumption"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
