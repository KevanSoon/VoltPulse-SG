"use client";

interface StatsCardProps {
  title: string;
  value: string | number;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  trendColor?: "green" | "red" | "gray";
  icon?: React.ReactNode;
  subtitle?: string;
}

export default function StatsCard({
  title,
  value,
  trend,
  trendDirection = "neutral",
  trendColor,
  icon,
  subtitle,
}: StatsCardProps) {
  const getTrendColor = () => {
    if (trendColor === "green") return "text-teal-600";
    if (trendColor === "red") return "text-red-600";
    if (trendDirection === "up") return "text-teal-600";
    if (trendDirection === "down") return "text-red-600";
    return "text-gray-500";
  };

  const getTrendIcon = () => {
    if (trendDirection === "up") {
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 17l9.2-9.2M17 17V7H7"
          />
        </svg>
      );
    }
    if (trendDirection === "down") {
      return (
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 7l-9.2 9.2M7 7v10h10"
          />
        </svg>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-200 hover:border-teal-300 hover:shadow-md transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-gray-500 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-gray-400 text-xs mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="text-teal-600 bg-teal-50 p-2 rounded-lg">
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 mt-3 text-sm ${getTrendColor()}`}>
          {getTrendIcon()}
          <span>{trend}</span>
        </div>
      )}
    </div>
  );
}
