"use client";

import Link from "next/link";

// Mock bill data - in production, this would come from the uploaded bill
const BILL_DATA = {
  currentBill: 156.80,
  previousBill: 142.50,
  currentUsage: 520,
  previousUsage: 475,
  nationalAverage: 400,
  billingPeriod: "Dec 2024",
  accountNumber: "****4521",
  tariffRate: 0.3016,
};

function ComparisonBar({
  value,
  maxValue,
  label,
  color
}: {
  value: number;
  maxValue: number;
  label: string;
  color: string;
}) {
  const percentage = (value / maxValue) * 100;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{value} kWh</span>
      </div>
      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function BillSummary() {
  const usageChange = BILL_DATA.currentUsage - BILL_DATA.previousUsage;
  const usageChangePercent = ((usageChange / BILL_DATA.previousUsage) * 100).toFixed(1);
  const vsNational = BILL_DATA.currentUsage - BILL_DATA.nationalAverage;
  const vsNationalPercent = ((vsNational / BILL_DATA.nationalAverage) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Bill Overview */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border border-green-100">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-gray-500">Current Bill - {BILL_DATA.billingPeriod}</p>
            <p className="text-3xl font-bold text-gray-900">S${BILL_DATA.currentBill.toFixed(2)}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Usage</p>
            <p className="text-2xl font-bold text-gray-900">{BILL_DATA.currentUsage} kWh</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-sm">
          {usageChange > 0 ? (
            <>
              <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
              <span className="text-red-600 font-medium">
                +{usageChange} kWh (+{usageChangePercent}%) vs last month
              </span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              <span className="text-green-600 font-medium">
                {usageChange} kWh ({usageChangePercent}%) vs last month
              </span>
            </>
          )}
        </div>
      </div>

      {/* Comparison */}
      <div className="bg-white rounded-xl p-6 border border-gray-200">
        <h3 className="font-semibold text-gray-900 mb-4">How You Compare</h3>
        <div className="space-y-4">
          <ComparisonBar
            value={BILL_DATA.currentUsage}
            maxValue={600}
            label="Your Usage"
            color="bg-blue-500"
          />
          <ComparisonBar
            value={BILL_DATA.nationalAverage}
            maxValue={600}
            label="National Average"
            color="bg-gray-400"
          />
        </div>

        <div className={`mt-4 p-3 rounded-lg ${vsNational > 0 ? "bg-red-50" : "bg-green-50"}`}>
          <p className={`text-sm font-medium ${vsNational > 0 ? "text-red-700" : "text-green-700"}`}>
            {vsNational > 0
              ? `You're using ${vsNational} kWh (+${vsNationalPercent}%) more than the national average`
              : `You're using ${Math.abs(vsNational)} kWh (${vsNationalPercent}%) less than the national average`
            }
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link
          href="/upload"
          className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-green-300 hover:shadow-md transition-all"
        >
          <div className="p-2 bg-green-50 rounded-lg">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div>
            <p className="font-medium text-gray-900">Upload New Bill</p>
            <p className="text-xs text-gray-500">Update your consumption data</p>
          </div>
        </Link>
        <Link
          href="/chat"
          className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-green-300 hover:shadow-md transition-all"
        >
          <div className="p-2 bg-green-50 rounded-lg">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <p className="font-medium text-gray-900">Chat with AI</p>
            <p className="text-xs text-gray-500">Get personalized advice</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
