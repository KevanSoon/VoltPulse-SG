"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import StatsCard from "./components/StatsCard";
import ViewToggle, { ViewMode } from "./components/ViewToggle";
import BillSummary from "./components/BillSummary";
import Recommendations from "./components/Recommendations";
import MonthlyConsumptionChart from "./components/MonthlyConsumptionChart";
import { OCRResult, BillData, ChartData } from "./types";

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

function transformOCRToChartData(ocrResult: OCRResult): ChartData[] {
  const electricityTrend = ocrResult.form_data.extraction_data.consumption_trends.find(
    (t) => t.service_type === "Electricity"
  );

  if (!electricityTrend) return [];

  return electricityTrend.monthly_data.map((m) => ({
    month: m.month,
    consumption: m.value,
    average: electricityTrend.national_average,
  }));
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
  const [ocrData, setOcrData] = useState<OCRResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
  const chartData = ocrData ? transformOCRToChartData(ocrData) : [];

  // Calculate stats from the data
  const currentUsage = billData?.currentUsage || 0;
  const previousUsage = billData?.previousUsage || currentUsage;
  const nationalAverage = billData?.nationalAverage || 338;
  const usageChange = previousUsage ? ((currentUsage - previousUsage) / previousUsage * 100) : 0;
  const vsNational = nationalAverage ? ((currentUsage - nationalAverage) / nationalAverage * 100) : 0;

  // Calculate monthly average from chart data
  const monthlyAverage = chartData.length > 0
    ? Math.round(chartData.reduce((sum, d) => sum + d.consumption, 0) / chartData.length)
    : 0;

  // Estimate potential savings (difference between current and national average)
  const potentialSavings = currentUsage > nationalAverage
    ? Math.round((currentUsage - nationalAverage) * 0.30)
    : 0;

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
        <ViewToggle currentView={viewMode} onChange={setViewMode} />
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="This Month"
          value={`${currentUsage} kWh`}
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
          value={`${monthlyAverage} kWh`}
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
          trend={`National: ${nationalAverage} kWh`}
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
                <p className="text-gray-500 text-sm mt-1">Your electricity usage over the past year</p>
              </div>
            </div>
            <MonthlyConsumptionChart data={chartData} nationalAverage={nationalAverage} />
          </div>
        </div>

        {/* Recommendations - Right Column */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">How to Save</h2>
            <Recommendations />
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
