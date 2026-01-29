"use client";

import { useState, useEffect } from "react";
import { ROIProduct, ROIResult } from "../types";

interface ROICalculatorProps {
  onFindRetailers?: (productType: string) => void;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

export default function ROICalculator({ onFindRetailers }: ROICalculatorProps) {
  const [products, setProducts] = useState<ROIProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [currentRating, setCurrentRating] = useState<number>(1);
  const [newRating, setNewRating] = useState<number>(4);
  const [price, setPrice] = useState<string>("1000");
  const [applyVoucher, setApplyVoucher] = useState(true);

  // Result
  const [result, setResult] = useState<ROIResult | null>(null);

  // Fetch available products
  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${BACKEND_URL}/retailers/roi/products`);
        if (response.ok) {
          const data = await response.json();
          setProducts(data.products);
          if (data.products.length > 0) {
            setSelectedProduct(data.products[0].product_type);
          }
        }
      } catch (err) {
        console.error("Failed to fetch products:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  // Get current product info
  const currentProduct = products.find(p => p.product_type === selectedProduct);

  // Calculate ROI
  const handleCalculate = async () => {
    if (!selectedProduct || !price) return;

    setCalculating(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/retailers/roi/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_type: selectedProduct,
          current_rating: currentRating,
          new_rating: newRating,
          product_price: parseFloat(price),
          apply_voucher: applyVoucher,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Calculation failed");
      }
    } catch (err) {
      setError("Failed to calculate ROI");
      console.error(err);
    } finally {
      setCalculating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 border border-gray-200 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-4">
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-50 to-cyan-50 px-6 py-4 border-b border-teal-100">
        <h3 className="text-lg font-semibold text-gray-900">ROI Calculator</h3>
        <p className="text-sm text-gray-600">Calculate savings for appliance upgrades with Climate Voucher</p>
      </div>

      <div className="p-6">
        {/* Form */}
        <div className="space-y-4">
          {/* Product Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Appliance Type
            </label>
            <select
              value={selectedProduct}
              onChange={(e) => {
                setSelectedProduct(e.target.value);
                setResult(null);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            >
              {products.map((product) => (
                <option key={product.product_type} value={product.product_type}>
                  {product.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Ratings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Rating
              </label>
              <select
                value={currentRating}
                onChange={(e) => {
                  setCurrentRating(parseInt(e.target.value));
                  setResult(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              >
                <option value={0}>Unknown / Old</option>
                {currentProduct && Array.from({ length: currentProduct.max_ticks }, (_, i) => i + 1).map((tick) => (
                  <option key={tick} value={tick}>{tick}-tick</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Rating
              </label>
              <select
                value={newRating}
                onChange={(e) => {
                  setNewRating(parseInt(e.target.value));
                  setResult(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              >
                {currentProduct && Array.from({ length: currentProduct.max_ticks }, (_, i) => i + 1).map((tick) => (
                  <option key={tick} value={tick}>{tick}-tick</option>
                ))}
              </select>
            </div>
          </div>

          {/* Price */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Product Price (SGD)
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
              <input
                type="number"
                value={price}
                onChange={(e) => {
                  setPrice(e.target.value);
                  setResult(null);
                }}
                className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="Enter price"
                min="0"
              />
            </div>
            {currentProduct && (
              <p className="text-xs text-gray-500 mt-1">
                Typical range: ${currentProduct.typical_price_range[0]} - ${currentProduct.typical_price_range[1]}
              </p>
            )}
          </div>

          {/* Voucher Toggle */}
          <div className="flex items-center justify-between p-3 bg-teal-50 rounded-lg">
            <div>
              <p className="font-medium text-teal-900">Apply Climate Voucher</p>
              <p className="text-sm text-teal-700">$300 off eligible purchases</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={applyVoucher}
                onChange={(e) => {
                  setApplyVoucher(e.target.checked);
                  setResult(null);
                }}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-teal-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
            </label>
          </div>

          {/* Calculate Button */}
          <button
            onClick={handleCalculate}
            disabled={calculating || !selectedProduct || !price}
            className="w-full py-3 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {calculating ? "Calculating..." : "Calculate ROI"}
          </button>

          {error && (
            <p className="text-sm text-red-600 text-center">{error}</p>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="mt-6 pt-6 border-t border-gray-200 space-y-4">
            <h4 className="font-semibold text-gray-900">ROI Analysis</h4>

            {/* Cost Breakdown */}
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Cost Breakdown</p>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Product Price</span>
                  <span className="font-medium">${result.product_price.toFixed(2)}</span>
                </div>
                {result.voucher_amount > 0 && (
                  <div className="flex justify-between text-teal-600">
                    <span>Climate Voucher</span>
                    <span className="font-medium">-${result.voucher_amount.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between pt-2 border-t border-gray-200 font-semibold">
                  <span>Your Cost</span>
                  <span className="text-teal-600">${result.net_cost.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Savings */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-teal-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-teal-600">${result.annual_savings_sgd.toFixed(0)}</p>
                <p className="text-xs text-teal-700">Annual Savings</p>
              </div>
              <div className="bg-teal-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-teal-600">{result.payback_period_months}</p>
                <p className="text-xs text-teal-700">Months to Payback</p>
              </div>
            </div>

            {/* Long-term Benefits */}
            <div className="bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg p-4 text-white">
              <p className="text-sm opacity-90 mb-1">10-Year Net Benefit</p>
              <p className="text-3xl font-bold">${result.net_benefit_10_years.toFixed(0)}</p>
              <p className="text-sm opacity-90 mt-1">{result.roi_percent_annual.toFixed(1)}% annual ROI</p>
            </div>

            {/* Voucher Eligibility */}
            {!result.is_voucher_eligible && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-sm text-yellow-800">
                  <span className="font-medium">Note:</span> This product does not meet the minimum {result.minimum_rating_for_voucher}-tick requirement for Climate Voucher eligibility.
                </p>
              </div>
            )}

            {/* Notes */}
            {result.notes.length > 0 && (
              <div className="space-y-2">
                {result.notes.map((note, idx) => (
                  <p key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                    <svg className="w-4 h-4 text-teal-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {note}
                  </p>
                ))}
              </div>
            )}

            {/* Find Retailers Button */}
            {onFindRetailers && (
              <button
                onClick={() => onFindRetailers(result.product_type)}
                className="w-full py-2 border border-teal-600 text-teal-600 font-medium rounded-lg hover:bg-teal-50 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Find Retailers Near Me
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
