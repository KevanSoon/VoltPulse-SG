"use client";

import { useState, useMemo } from "react";
import { Calculator, TrendingDown, Zap } from "lucide-react";

export function SavingsCalculator() {
  const [monthlyBill, setMonthlyBill] = useState<number>(150);
  const [householdSize, setHouseholdSize] = useState<number>(4);
  const [hasOldAppliances, setHasOldAppliances] = useState<boolean>(true);
  const [acUsageHours, setAcUsageHours] = useState<number>(8);

  const calculations = useMemo(() => {
    // Average Singapore household uses ~400 kWh/month
    // Rate is ~$0.30/kWh
    const estimatedKwh = monthlyBill / 0.30;
    const nationalAverage = 338; // kWh for 4-room HDB
    const adjustedAverage = nationalAverage * (householdSize / 4);
    
    // Potential savings calculations
    let potentialSavingsPercent = 0;
    
    // Old appliances: 15-30% savings potential
    if (hasOldAppliances) {
      potentialSavingsPercent += 20;
    }
    
    // AC usage: each hour above 6 = 3% more than necessary
    if (acUsageHours > 6) {
      potentialSavingsPercent += (acUsageHours - 6) * 3;
    }
    
    // Above national average penalty
    if (estimatedKwh > adjustedAverage) {
      potentialSavingsPercent += Math.min(15, ((estimatedKwh - adjustedAverage) / adjustedAverage) * 20);
    }
    
    const monthlySavings = Math.round(monthlyBill * (potentialSavingsPercent / 100));
    const annualSavings = monthlySavings * 12;
    const climateVoucher = 300; // Government voucher amount
    
    return {
      estimatedKwh: Math.round(estimatedKwh),
      nationalAverage: Math.round(adjustedAverage),
      potentialSavingsPercent: Math.round(potentialSavingsPercent),
      monthlySavings,
      annualSavings,
      climateVoucher,
      totalFirstYearSavings: annualSavings + climateVoucher,
    };
  }, [monthlyBill, householdSize, hasOldAppliances, acUsageHours]);

  return (
    <section className="py-16 lg:py-24 bg-white">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="max-w-3xl mx-auto text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Calculator className="w-8 h-8 text-teal-600" />
            <h2 className="text-3xl md:text-4xl font-bold text-slate-800">
              Savings Calculator
            </h2>
          </div>
          <p className="text-lg text-slate-600">
            See how much you could save with personalized recommendations
          </p>
        </div>

        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Input Form */}
            <div className="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-2xl p-6 md:p-8 border border-teal-100">
              <h3 className="font-semibold text-slate-800 mb-6">Your Household Details</h3>
              
              <div className="space-y-6">
                {/* Monthly Bill */}
                <div>
                  <label 
                    htmlFor="monthlyBill" 
                    className="block text-sm font-medium text-slate-700 mb-2"
                  >
                    Average Monthly Bill (S$)
                  </label>
                  <input
                    id="monthlyBill"
                    type="range"
                    min="50"
                    max="500"
                    step="10"
                    value={monthlyBill}
                    onChange={(e) => setMonthlyBill(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
                  />
                  <div className="flex justify-between mt-2">
                    <span className="text-sm text-slate-500">S$50</span>
                    <span className="text-lg font-semibold text-teal-600">S${monthlyBill}</span>
                    <span className="text-sm text-slate-500">S$500</span>
                  </div>
                </div>

                {/* Household Size */}
                <div>
                  <label 
                    htmlFor="householdSize" 
                    className="block text-sm font-medium text-slate-700 mb-2"
                  >
                    Household Size
                  </label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5, 6].map((size) => (
                      <button
                        key={size}
                        onClick={() => setHouseholdSize(size)}
                        className={`
                          flex-1 py-2 rounded-lg border-2 font-medium transition-colors
                          ${householdSize === size 
                            ? 'border-teal-600 bg-teal-50 text-teal-700' 
                            : 'border-slate-200 bg-white hover:border-slate-300 text-slate-600'
                          }
                        `}
                        aria-pressed={householdSize === size}
                      >
                        {size}{size === 6 ? '+' : ''}
                      </button>
                    ))}
                  </div>
                </div>

                {/* AC Usage */}
                <div>
                  <label 
                    htmlFor="acUsage" 
                    className="block text-sm font-medium text-slate-700 mb-2"
                  >
                    Daily AC Usage (hours)
                  </label>
                  <input
                    id="acUsage"
                    type="range"
                    min="0"
                    max="24"
                    step="1"
                    value={acUsageHours}
                    onChange={(e) => setAcUsageHours(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
                  />
                  <div className="flex justify-between mt-2">
                    <span className="text-sm text-slate-500">0h</span>
                    <span className="text-lg font-semibold text-teal-600">{acUsageHours}h</span>
                    <span className="text-sm text-slate-500">24h</span>
                  </div>
                </div>

                {/* Old Appliances */}
                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hasOldAppliances}
                      onChange={(e) => setHasOldAppliances(e.target.checked)}
                      className="w-5 h-5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                    />
                    <span className="text-slate-700">
                      I have appliances older than 5 years
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="space-y-4">
              {/* Current Estimate */}
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="w-5 h-5 text-amber-500" />
                  <h3 className="font-semibold text-slate-800">Current Estimate</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Monthly Usage</p>
                    <p className="text-2xl font-bold text-slate-800">{calculations.estimatedKwh} kWh</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">National Average</p>
                    <p className="text-2xl font-bold text-slate-800">{calculations.nationalAverage} kWh</p>
                  </div>
                </div>
                {calculations.estimatedKwh > calculations.nationalAverage && (
                  <p className="mt-3 text-sm text-amber-600 font-medium">
                    ⚠️ {Math.round((calculations.estimatedKwh / calculations.nationalAverage - 1) * 100)}% above average
                  </p>
                )}
              </div>

              {/* Potential Savings */}
              <div className="bg-gradient-to-br from-teal-600 to-cyan-700 rounded-2xl p-6 text-white shadow-lg">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingDown className="w-5 h-5" />
                  <h3 className="font-semibold">Potential Savings</h3>
                </div>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-3 border-b border-teal-500/30">
                    <span className="text-teal-100">Monthly Savings</span>
                    <span className="text-2xl font-bold">S${calculations.monthlySavings}</span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b border-teal-500/30">
                    <span className="text-teal-100">Annual Savings</span>
                    <span className="text-2xl font-bold">S${calculations.annualSavings}</span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b border-teal-500/30">
                    <span className="text-teal-100">+ Climate Voucher</span>
                    <span className="text-xl font-bold">S${calculations.climateVoucher}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <span className="font-semibold">First Year Total</span>
                    <span className="text-3xl font-bold">S${calculations.totalFirstYearSavings}</span>
                  </div>
                </div>
              </div>

              {/* CTA */}
              <a
                href="/upload"
                className="block w-full py-4 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white text-center font-semibold rounded-xl transition-all shadow-lg hover:shadow-xl"
              >
                Upload Your Bill for Exact Analysis →
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
