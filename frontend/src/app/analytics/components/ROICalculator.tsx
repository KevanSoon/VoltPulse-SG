"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ROIProduct } from "../types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

// All Singapore planning areas / towns
const SINGAPORE_TOWNS = [
  "Ang Mo Kio",
  "Bedok",
  "Bishan",
  "Boon Lay",
  "Bukit Batok",
  "Bukit Merah",
  "Bukit Panjang",
  "Bukit Timah",
  "Choa Chu Kang",
  "Clementi",
  "Geylang",
  "Hougang",
  "Jurong East",
  "Jurong West",
  "Kallang",
  "Katong",
  "Kranji",
  "Lim Chu Kang",
  "Little India",
  "Macpherson",
  "Marine Parade",
  "Middle Road",
  "Newton",
  "Novena",
  "Orchard",
  "Pasir Panjang",
  "Pasir Ris",
  "Paya Lebar",
  "Punggol",
  "Queenstown",
  "Raffles Place",
  "Sembawang",
  "Sengkang",
  "Sentosa",
  "Serangoon",
  "Tampines",
  "Telok Blangah",
  "Toa Payoh",
  "Tuas",
  "Woodlands",
  "Yishun",
];

export default function ROICalculator() {
  const router = useRouter();
  const [products, setProducts] = useState<ROIProduct[]>([]);
  const [loading, setLoading] = useState(false);

  // Form state
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedTown, setSelectedTown] = useState<string>("");

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

  // Redirect to chatbot with query
  const handleRecommendRetailers = () => {
    const productLabel = currentProduct?.display_name || selectedProduct;
    const query = `Find me Climate Voucher retailers selling ${productLabel} near ${selectedTown} in Singapore.`;
    router.push(`/chat?query=${encodeURIComponent(query)}`);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 border border-gray-200 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-4">
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
        <h3 className="text-lg font-semibold text-gray-900">Appliance Recommendation</h3>
        <p className="text-sm text-gray-600">Find nearby Climate Voucher retailers for your appliance upgrade</p>
      </div>

      <div className="p-6">
        <div className="space-y-4">
          {/* Appliance Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Appliance Type
            </label>
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            >
              {products.map((product) => (
                <option key={product.product_type} value={product.product_type}>
                  {product.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Town / Planning Area */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Town / Area
            </label>
            <select
              value={selectedTown}
              onChange={(e) => setSelectedTown(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            >
              <option value="">Select your town</option>
              {SINGAPORE_TOWNS.map((town) => (
                <option key={town} value={town}>
                  {town}
                </option>
              ))}
            </select>
          </div>

          {/* Info banner */}
          <div className="flex items-start gap-3 p-3 bg-teal-50 rounded-lg">
            <svg className="w-5 h-5 text-teal-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-teal-800">
              Our assistant will find participating retailers near your town that accept the <span className="font-medium">$300 Climate Voucher</span> for eligible appliances.
            </p>
          </div>

          {/* Recommend Button */}
          <button
            onClick={handleRecommendRetailers}
            disabled={!selectedProduct || !selectedTown}
            className="w-full py-3 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Recommend Me Retailers
          </button>
        </div>
      </div>
    </div>
  );
}
