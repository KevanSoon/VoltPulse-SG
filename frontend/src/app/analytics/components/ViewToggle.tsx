"use client";

import { LayoutDashboard, Map } from "lucide-react";

export type ViewMode = "dashboard" | "heatmap";

interface ViewToggleProps {
  currentView: ViewMode;
  onChange: (view: ViewMode) => void;
}

export default function ViewToggle({ currentView, onChange }: ViewToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-gray-500 text-sm">View:</span>
      <div className="flex bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => onChange("dashboard")}
          className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md transition-colors ${
            currentView === "dashboard"
              ? "bg-teal-600 text-white"
              : "text-gray-600 hover:text-gray-900 hover:bg-gray-200"
          }`}
        >
          <LayoutDashboard size={16} />
          Dashboard
        </button>
        <button
          onClick={() => onChange("heatmap")}
          className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md transition-colors ${
            currentView === "heatmap"
              ? "bg-teal-600 text-white"
              : "text-gray-600 hover:text-gray-900 hover:bg-gray-200"
          }`}
        >
          <Map size={16} />
          Heatmap
        </button>
      </div>
    </div>
  );
}
