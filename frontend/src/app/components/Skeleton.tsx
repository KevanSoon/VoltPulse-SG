"use client";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular" | "card";
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export function Skeleton({ 
  className = "", 
  variant = "rectangular",
  width,
  height,
  lines = 1
}: SkeletonProps) {
  const baseClasses = "skeleton animate-pulse";
  
  const getVariantClasses = () => {
    switch (variant) {
      case "text":
        return "h-4 rounded";
      case "circular":
        return "rounded-full";
      case "card":
        return "rounded-xl";
      default:
        return "rounded-md";
    }
  };

  const style = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
  };

  if (variant === "text" && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`${baseClasses} h-4 rounded`}
            style={{ width: i === lines - 1 ? "75%" : "100%" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${baseClasses} ${getVariantClasses()} ${className}`}
      style={style}
      aria-hidden="true"
      role="presentation"
    />
  );
}

// Pre-built skeleton components for common use cases
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
      <Skeleton variant="text" width="40%" height={16} />
      <Skeleton variant="text" width="60%" height={28} />
      <Skeleton variant="text" width="80%" height={12} />
    </div>
  );
}

export function SkeletonChart() {
  // Use deterministic heights to avoid hydration mismatch
  const barHeights = ['70%', '45%', '85%', '55%', '65%', '75%'];
  
  return (
    <div className="bg-white rounded-xl p-6 border border-slate-200">
      <div className="flex justify-between items-center mb-4">
        <Skeleton variant="text" width="30%" height={20} />
        <Skeleton variant="rectangular" width={100} height={32} />
      </div>
      <div className="h-64 flex items-end justify-between gap-2 pt-8">
        {barHeights.map((height, i) => (
          <Skeleton
            key={i}
            variant="rectangular"
            width="14%"
            height={height}
          />
        ))}
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="p-4 border-b border-slate-200">
        <Skeleton variant="text" width="25%" height={20} />
      </div>
      <div className="divide-y divide-gray-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 flex items-center gap-4">
            <Skeleton variant="circular" width={40} height={40} />
            <div className="flex-1 space-y-2">
              <Skeleton variant="text" width="40%" height={14} />
              <Skeleton variant="text" width="60%" height={12} />
            </div>
            <Skeleton variant="rectangular" width={80} height={32} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonBillSummary() {
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-slate-100 to-slate-50 rounded-xl p-6 border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <div className="space-y-2">
            <Skeleton variant="text" width={120} height={14} />
            <Skeleton variant="text" width={160} height={32} />
          </div>
          <div className="text-right space-y-2">
            <Skeleton variant="text" width={60} height={14} />
            <Skeleton variant="text" width={100} height={28} />
          </div>
        </div>
        <Skeleton variant="text" width="50%" height={14} />
      </div>
      
      <div className="bg-white rounded-xl p-6 border border-slate-200 space-y-4">
        <Skeleton variant="text" width="30%" height={18} />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-between">
                <Skeleton variant="text" width="25%" height={14} />
                <Skeleton variant="text" width="15%" height={14} />
              </div>
              <Skeleton variant="rectangular" width="100%" height={12} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-8 animate-pulse">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2">
          <Skeleton variant="text" width={280} height={32} />
          <Skeleton variant="text" width={400} height={16} />
        </div>
        <div className="flex gap-3">
          <Skeleton variant="rectangular" width={150} height={40} />
          <Skeleton variant="rectangular" width={120} height={40} />
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SkeletonBillSummary />
          <SkeletonChart />
        </div>
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl p-6 border border-slate-200">
            <Skeleton variant="text" width="60%" height={20} className="mb-4" />
            <div className="text-center py-6 space-y-4">
              <Skeleton variant="circular" width={64} height={64} className="mx-auto" />
              <Skeleton variant="text" lines={3} />
              <Skeleton variant="rectangular" width="100%" height={48} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
