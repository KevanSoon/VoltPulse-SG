"use client";

const RECOMMENDATIONS = [
  {
    id: 1,
    title: "Switch to LED Lighting",
    description: "Replace incandescent bulbs with LED alternatives to save up to 80% on lighting costs.",
    savings: "S$15-25/month",
    difficulty: "Easy",
    icon: "💡",
    category: "lighting",
  },
  {
    id: 2,
    title: "Optimize Air Conditioning",
    description: "Set your AC to 25°C instead of 22°C. Each degree lower increases energy use by 3-5%.",
    savings: "S$30-50/month",
    difficulty: "Easy",
    icon: "❄️",
    category: "cooling",
  },
  {
    id: 3,
    title: "Use Natural Ventilation",
    description: "Open windows during cooler hours (7-9am, after 7pm) to reduce AC dependency.",
    savings: "S$20-40/month",
    difficulty: "Easy",
    icon: "🌬️",
    category: "cooling",
  },
  {
    id: 4,
    title: "Install a Smart Power Strip",
    description: "Eliminate standby power drain from electronics. Appliances use 5-10% energy even when \"off\".",
    savings: "S$10-15/month",
    difficulty: "Easy",
    icon: "🔌",
    category: "appliances",
  },
  {
    id: 5,
    title: "Upgrade to Energy-Efficient Appliances",
    description: "Look for appliances with 4-5 tick energy ratings. Consider upgrading old refrigerators and ACs.",
    savings: "S$40-80/month",
    difficulty: "Medium",
    icon: "⭐",
    category: "appliances",
  },
  {
    id: 6,
    title: "Wash Clothes in Cold Water",
    description: "90% of washing machine energy goes to heating water. Cold wash works for most clothes.",
    savings: "S$8-12/month",
    difficulty: "Easy",
    icon: "👕",
    category: "laundry",
  },
];

const VOUCHERS = [
  {
    title: "Climate Friendly Households Programme",
    description: "Get up to S$300 worth of e-vouchers to offset the cost of energy-efficient appliances.",
    eligibility: "All HDB households",
    link: "#",
  },
  {
    title: "Energy Efficiency Fund",
    description: "Grants for businesses and households to improve energy efficiency.",
    eligibility: "Selected households",
    link: "#",
  },
];

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const colors = {
    Easy: "bg-teal-100 text-teal-700",
    Medium: "bg-yellow-100 text-yellow-700",
    Hard: "bg-red-100 text-red-700",
  };

  return (
    <span className={`text-xs px-2 py-1 rounded-full ${colors[difficulty as keyof typeof colors] || colors.Easy}`}>
      {difficulty}
    </span>
  );
}

export default function Recommendations() {
  return (
    <div className="space-y-6">
      {/* Tips Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Energy Saving Tips</h3>
          <span className="text-xs text-gray-500">Based on your usage pattern</span>
        </div>

        <div className="grid gap-3">
          {RECOMMENDATIONS.slice(0, 4).map((rec) => (
            <div
              key={rec.id}
              className="flex items-start gap-4 p-4 bg-white border border-gray-200 rounded-xl hover:border-teal-300 hover:shadow-sm transition-all"
            >
              <div className="text-2xl">{rec.icon}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-gray-900">{rec.title}</h4>
                  <DifficultyBadge difficulty={rec.difficulty} />
                </div>
                <p className="text-sm text-gray-600 mb-2">{rec.description}</p>
                <p className="text-sm font-medium text-teal-600">
                  Potential savings: {rec.savings}
                </p>
              </div>
            </div>
          ))}
        </div>

        <button className="w-full mt-3 py-2 text-sm text-teal-600 hover:text-teal-700 font-medium">
          View all {RECOMMENDATIONS.length} recommendations →
        </button>
      </div>

      {/* Vouchers Section */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-4">Available Government Vouchers</h3>
        <div className="space-y-3">
          {VOUCHERS.map((voucher, index) => (
            <div
              key={index}
              className="p-4 bg-gradient-to-r from-teal-50 to-cyan-50 border border-teal-100 rounded-xl"
            >
              <h4 className="font-medium text-gray-900 mb-1">{voucher.title}</h4>
              <p className="text-sm text-gray-600 mb-2">{voucher.description}</p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Eligibility: {voucher.eligibility}</span>
                <a
                  href={voucher.link}
                  className="text-sm font-medium text-teal-600 hover:text-teal-700"
                >
                  Learn more →
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Potential Total Savings */}
      <div className="bg-teal-600 text-white rounded-xl p-5">
        <div className="flex items-center gap-3 mb-2">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="font-semibold text-lg">Total Potential Savings</h3>
        </div>
        <p className="text-3xl font-bold mb-1">Up to S$150/month</p>
        <p className="text-teal-100 text-sm">
          By implementing all recommended energy-saving measures
        </p>
      </div>
    </div>
  );
}
