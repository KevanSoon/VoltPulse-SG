"use client";

import { Zap, Droplets, Flame } from "lucide-react";

export type UtilityType = "electricity" | "water" | "gas";

interface UtilityToggleProps {
  currentUtility: UtilityType;
  onChange: (utility: UtilityType) => void;
}

const utilities = [
  { type: "electricity" as UtilityType, label: "Electricity", icon: Zap, color: "text-yellow-500" },
  { type: "water" as UtilityType, label: "Water", icon: Droplets, color: "text-blue-500" },
  { type: "gas" as UtilityType, label: "Gas", icon: Flame, color: "text-orange-500" },
];

export default function UtilityToggle({ currentUtility, onChange }: UtilityToggleProps) {
  return (
    <div className="flex bg-gray-100 rounded-lg p-1">
      {utilities.map(({ type, label, icon: Icon, color }) => (
        <button
          key={type}
          onClick={() => onChange(type)}
          className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md transition-colors ${
            currentUtility === type
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900 hover:bg-gray-200"
          }`}
        >
          <Icon size={16} className={currentUtility === type ? color : "text-gray-400"} />
          {label}
        </button>
      ))}
    </div>
  );
}
