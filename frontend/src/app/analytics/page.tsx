"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import StatsCard from "./components/StatsCard";
import ViewToggle, { ViewMode } from "./components/ViewToggle";
import UtilityToggle, { UtilityType } from "./components/UtilityToggle";
import BillSummary from "./components/BillSummary";
import MonthlyConsumptionChart from "./components/MonthlyConsumptionChart";
import { OCRResult, BillData, ChartData, UtilityData } from "./types";

// Dynamic import for the map component to avoid SSR issues
const SingaporeHeatmap = dynamic(
  () => import("./components/SingaporeHeatmap"),
  {
    ssr: false,
    loading: () => (
      <div className="h-[400px] bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full" />
      </div>
    ),
  }
);

function formatBillingPeriod(startDate: string | null, endDate: string | null): string {
  if (!endDate) return "Current Period";
  const date = new Date(endDate);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function transformOCRToChartData(ocrResult: OCRResult, utilityType: UtilityType): ChartData[] {
  const serviceTypeMap: Record<UtilityType, "Electricity" | "Gas" | "Water"> = {
    electricity: "Electricity",
    gas: "Gas",
    water: "Water",
  };

  const trend = ocrResult.form_data.extraction_data.consumption_trends.find(
    (t) => t.service_type === serviceTypeMap[utilityType]
  );

  if (!trend) return [];

  return trend.monthly_data.map((m) => ({
    month: m.month,
    consumption: m.value,
    average: trend.national_average,
  }));
}

function transformOCRToUtilityData(ocrResult: OCRResult, utilityType: UtilityType): UtilityData | null {
  const data = ocrResult.form_data.extraction_data;
  const serviceTypeMap: Record<UtilityType, "Electricity" | "Gas" | "Water"> = {
    electricity: "Electricity",
    gas: "Gas",
    water: "Water",
  };

  const trend = data.consumption_trends.find(
    (t) => t.service_type === serviceTypeMap[utilityType]
  );

  const monthlyData = trend?.monthly_data || [];
  const previousMonthData = monthlyData.length >= 2 ? monthlyData[monthlyData.length - 2] : null;

  if (utilityType === "electricity") {
    return {
      currentUsage: data.consumption_kwh || 0,
      previousUsage: previousMonthData?.value || null,
      nationalAverage: trend?.national_average || 338,
      neighbourAverage: trend?.neighbour_average || 300,
      charges: data.energy_charges || 0,
      unit: "kWh",
      trendDirection: trend?.trend_direction || "stable",
      chartData: transformOCRToChartData(ocrResult, utilityType),
    };
  } else if (utilityType === "gas") {
    return {
      currentUsage: data.gas_usage_kwh || 0,
      previousUsage: previousMonthData?.value || null,
      nationalAverage: trend?.national_average || 50,
      neighbourAverage: trend?.neighbour_average || 45,
      charges: data.gas_charges || 0,
      unit: "kWh",
      trendDirection: trend?.trend_direction || "stable",
      chartData: transformOCRToChartData(ocrResult, utilityType),
    };
  } else {
    return {
      currentUsage: data.water_usage_cu_m || 0,
      previousUsage: previousMonthData?.value || null,
      nationalAverage: trend?.national_average || 15,
      neighbourAverage: trend?.neighbour_average || 14,
      charges: data.water_charges || 0,
      unit: "m³",
      trendDirection: trend?.trend_direction || "stable",
      chartData: transformOCRToChartData(ocrResult, utilityType),
    };
  }
}

function transformOCRToBillData(ocrResult: OCRResult): BillData {
  const data = ocrResult.form_data.extraction_data;
  const electricityTrend = data.consumption_trends.find((t) => t.service_type === "Electricity");

  // Get previous month's consumption from trend data
  const monthlyData = electricityTrend?.monthly_data || [];
  const previousMonthData = monthlyData.length >= 2 ? monthlyData[monthlyData.length - 2] : null;

  return {
    currentBill: data.total_amount || 0,
    previousBill: null,
    currentUsage: data.consumption_kwh || 0,
    previousUsage: previousMonthData?.value || null,
    nationalAverage: electricityTrend?.national_average || 338,
    neighbourAverage: electricityTrend?.neighbour_average || 300,
    billingPeriod: formatBillingPeriod(data.billing_period_start, data.billing_period_end),
    accountNumber: data.account_number ? `****${data.account_number.slice(-4)}` : "N/A",
    tariffRate: data.energy_charges && data.consumption_kwh
      ? data.energy_charges / data.consumption_kwh
      : null,
    gasUsage: data.gas_usage_kwh,
    gasCharges: data.gas_charges,
    waterUsage: data.water_usage_cu_m,
    waterCharges: data.water_charges,
    customerName: data.customer_name,
    address: data.premise_address,
    providerName: data.provider_name,
  };
}

export default function AnalyticsDashboard() {
  const [viewMode, setViewMode] = useState<ViewMode>("dashboard");
  const [utilityType, setUtilityType] = useState<UtilityType>("electricity");
  const [ocrData, setOcrData] = useState<OCRResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [aiRecommendations, setAiRecommendations] = useState<string | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);

  useEffect(() => {
    async function fetchOCRResults() {
      try {
        setLoading(true);

        // Get the source_id from localStorage (set by the upload page)
        const sourceId = localStorage.getItem("ocr_source_id");

        if (!sourceId) {
          throw new Error("No bill data found. Please upload a bill first.");
        }

        const response = await fetch(`/api/ocr/results/${sourceId}`);
        if (!response.ok) {
          if (response.status === 404) {
            // Clear invalid source_id
            localStorage.removeItem("ocr_source_id");
            throw new Error("Bill data not found. Please upload a new bill.");
          }
          throw new Error("Failed to fetch OCR results");
        }
        const data = await response.json();
        setOcrData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchOCRResults();
  }, []);

  const billData = ocrData ? transformOCRToBillData(ocrData) : null;
  const utilityData = ocrData ? transformOCRToUtilityData(ocrData, utilityType) : null;
  const chartData = utilityData?.chartData || [];

  // Calculate stats from the utility-specific data
  const currentUsage = utilityData?.currentUsage || 0;
  const previousUsage = utilityData?.previousUsage || currentUsage;
  const nationalAverage = utilityData?.nationalAverage || 338;
  const unit = utilityData?.unit || "kWh";
  const usageChange = previousUsage ? ((currentUsage - previousUsage) / previousUsage * 100) : 0;
  const vsNational = nationalAverage ? ((currentUsage - nationalAverage) / nationalAverage * 100) : 0;

  // Calculate monthly average from chart data
  const monthlyAverage = chartData.length > 0
    ? Math.round(chartData.reduce((sum, d) => sum + d.consumption, 0) / chartData.length)
    : 0;

  // Estimate potential savings (difference between current and national average)
  const ratePerUnit = utilityType === "electricity" ? 0.30 : utilityType === "gas" ? 0.25 : 2.74;
  const potentialSavings = currentUsage > nationalAverage
    ? Math.round((currentUsage - nationalAverage) * ratePerUnit)
    : 0;

  // Function to get AI recommendations
  const getAIRecommendations = async () => {
    setLoadingRecommendations(true);
    setShowRecommendations(true);
    try {
      // Build context from the OCR data
      const context = ocrData ? {
        utilityType,
        currentUsage,
        nationalAverage,
        usageChange,
        providerName: billData?.providerName,
        address: billData?.address,
      } : null;

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Based on my ${utilityType} usage of ${currentUsage} ${unit} (which is ${vsNational.toFixed(1)}% ${vsNational > 0 ? 'above' : 'below'} the national average of ${nationalAverage} ${unit}), please provide:
1. Specific energy-efficient appliance recommendations available in Singapore
2. Estimated savings for each recommendation
3. Any available government vouchers or rebates I can apply for
4. Quick tips to reduce my ${utilityType} consumption

Please be specific with product names and prices in SGD where possible.`,
          context,
        }),
      });

      if (!response.ok) throw new Error("Failed to get recommendations");
      const data = await response.json();
      setAiRecommendations(data.response || data.message);
    } catch {
      setAiRecommendations("Unable to load recommendations. Please try again later or visit the chat page for personalized advice.");
    } finally {
      setLoadingRecommendations(false);
    }
  };

  // Get utility-specific label
  const getUtilityLabel = () => {
    switch (utilityType) {
      case "electricity": return "Electricity";
      case "gas": return "Gas";
      case "water": return "Water";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full mx-auto" />
          <p className="mt-4 text-gray-600">Loading your energy data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="mt-4 text-gray-900 font-medium">Unable to load data</p>
          <p className="mt-2 text-gray-600">{error}</p>
          <a href="/upload" className="mt-4 inline-block px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            Upload a Bill
          </a>
        </div>
      </div>
    );
  }

  // Heatmap View
  if (viewMode === "heatmap") {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Singapore Energy Heatmap</h1>
            <p className="text-gray-600 mt-1">
              Explore energy consumption patterns across Singapore districts
            </p>
          </div>
          <ViewToggle currentView={viewMode} onChange={setViewMode} />
        </div>

        {/* Full-screen Heatmap */}
        <div className="bg-white rounded-xl p-6 border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Consumption by District</h2>
              <p className="text-gray-500 text-sm mt-1">
                See how your area compares to other districts in Singapore
              </p>
            </div>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
              Click markers for details
            </span>
          </div>
          <div className="h-[600px]">
            <SingaporeHeatmap dateRange={null} fullHeight />
          </div>
        </div>
      </div>
    );
  }

  // Dashboard View
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Your Energy Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Track your consumption, compare with others, and discover ways to save
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <UtilityToggle currentUtility={utilityType} onChange={setUtilityType} />
          <ViewToggle currentView={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title={`This Month (${getUtilityLabel()})`}
          value={`${currentUsage} ${unit}`}
          trend={previousUsage ? `${usageChange >= 0 ? "+" : ""}${usageChange.toFixed(1)}% vs last month` : "No previous data"}
          trendDirection={usageChange > 0 ? "up" : usageChange < 0 ? "down" : "neutral"}
          trendColor={usageChange > 0 ? "red" : "green"}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
        />
        <StatsCard
          title="Monthly Average"
          value={`${monthlyAverage} ${unit}`}
          trend={`Based on ${chartData.length} months`}
          trendDirection="neutral"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
        <StatsCard
          title="vs National Avg"
          value={`${vsNational >= 0 ? "+" : ""}${vsNational.toFixed(0)}%`}
          trend={`National: ${nationalAverage} ${unit}`}
          trendDirection={vsNational > 0 ? "up" : "down"}
          trendColor={vsNational > 0 ? "red" : "green"}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          }
        />
        <StatsCard
          title="Potential Savings"
          value={potentialSavings > 0 ? `S$${potentialSavings}/mo` : "On track!"}
          trend={potentialSavings > 0 ? "With recommended changes" : "Below national average"}
          trendDirection="down"
          trendColor="green"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bill Summary - Left Column */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Bill Summary</h2>
            <BillSummary data={billData} />
          </div>

          {/* Monthly Consumption Chart */}
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Monthly Consumption</h2>
                <p className="text-gray-500 text-sm mt-1">Your {getUtilityLabel().toLowerCase()} usage over the past year</p>
              </div>
            </div>
            <MonthlyConsumptionChart data={chartData} nationalAverage={nationalAverage} />
          </div>
        </div>

        {/* AI Recommendations - Right Column */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Personalized Recommendations</h2>

            {!showRecommendations ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <p className="text-gray-600 mb-4">
                  Get AI-powered recommendations for energy-efficient appliances and government vouchers tailored to your {getUtilityLabel().toLowerCase()} usage.
                </p>
                <button
                  onClick={getAIRecommendations}
                  className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Get Smart Recommendations
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {loadingRecommendations ? (
                  <div className="text-center py-8">
                    <div className="animate-spin w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full mx-auto mb-3" />
                    <p className="text-gray-600 text-sm">Analyzing your usage and finding the best recommendations...</p>
                  </div>
                ) : (
                  <>
                    <div className="prose prose-sm max-w-none text-gray-700 max-h-[400px] overflow-y-auto">
                      <div className="whitespace-pre-wrap">{aiRecommendations}</div>
                    </div>
                    <div className="pt-4 border-t border-gray-100 flex gap-2">
                      <button
                        onClick={getAIRecommendations}
                        className="flex-1 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                      >
                        Refresh
                      </button>
                      <a
                        href="/chat"
                        className="flex-1 px-3 py-2 text-sm bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors text-center"
                      >
                        Chat for More
                      </a>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border border-green-100">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Need Help Understanding Your Usage?</h3>
            <p className="text-gray-600">
              Our AI assistant can analyze your bills, explain your consumption patterns,
              and provide personalized recommendations to help you save.
            </p>
          </div>
          <a
            href="/chat"
            className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors whitespace-nowrap"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Chat with AI Assistant
          </a>
        </div>
      </div>
    </div>
  );
}
