"use client";

import { useState } from "react";

interface DateRange {
  start: Date;
  end: Date;
}

interface DateRangeFilterProps {
  onChange: (range: DateRange | null) => void;
}

export default function DateRangeFilter({ onChange }: DateRangeFilterProps) {
  const [preset, setPreset] = useState<string>("all");

  const handlePresetChange = (value: string) => {
    setPreset(value);

    if (value === "all") {
      onChange(null);
      return;
    }

    const end = new Date();
    const start = new Date();

    switch (value) {
      case "1m":
        start.setMonth(start.getMonth() - 1);
        break;
      case "3m":
        start.setMonth(start.getMonth() - 3);
        break;
      case "6m":
        start.setMonth(start.getMonth() - 6);
        break;
      case "1y":
        start.setFullYear(start.getFullYear() - 1);
        break;
      default:
        onChange(null);
        return;
    }

    onChange({ start, end });
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-gray-400 text-sm">Period:</span>
      <div className="flex bg-gray-700/50 rounded-lg p-1">
        {[
          { value: "1m", label: "1M" },
          { value: "3m", label: "3M" },
          { value: "6m", label: "6M" },
          { value: "1y", label: "1Y" },
          { value: "all", label: "All" },
        ].map((option) => (
          <button
            key={option.value}
            onClick={() => handlePresetChange(option.value)}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              preset === option.value
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
