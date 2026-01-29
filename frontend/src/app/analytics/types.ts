export interface MonthlyData {
  month: string;
  value: number;
  unit: string;
}

export interface ConsumptionTrend {
  service_type: "Electricity" | "Gas" | "Water";
  monthly_data: MonthlyData[];
  neighbour_average: number;
  national_average: number;
  trend_direction: "increasing" | "decreasing" | "stable";
}

export interface ExtractionData {
  account_number: string | null;
  customer_name: string | null;
  premise_address: string | null;
  billing_period_start: string | null;
  billing_period_end: string | null;
  bill_date: string | null;
  due_date: string | null;
  billing_days: number | null;
  consumption_kwh: number | null;
  previous_reading: number | null;
  current_reading: number | null;
  meter_number: string | null;
  daily_average_kwh: number | null;
  gas_usage_kwh: number | null;
  gas_charges: number | null;
  gas_provider: string | null;
  water_usage_cu_m: number | null;
  water_charges: number | null;
  water_provider: string | null;
  consumption_trends: ConsumptionTrend[];
  total_amount: number | null;
  energy_charges: number | null;
  tariff_tiers: unknown[];
  gst_amount: number | null;
  other_charges: number | null;
  previous_balance: number | null;
  provider_name: string | null;
  plan_name: string | null;
  extraction_confidence: number | null;
  extraction_warnings: string[];
}

// Diagnosis types
export type Severity = "low" | "medium" | "high";
export type AnomalyType = "spike" | "high_consumption" | "unusual_pattern" | "billing_discrepancy";
export type RecommendationCategory = "behavior" | "appliance" | "maintenance" | "monitoring";

export interface AnomalyFlag {
  type: AnomalyType;
  severity: Severity;
  description: string;
  affected_utility: string;
  value: number;
  threshold: number;
  deviation_percent: number | null;
}

export interface EfficiencyIssue {
  utility_type: string;
  current_value: number;
  national_average: number;
  neighbour_average: number | null;
  deviation_percent: number;
  severity: Severity;
  potential_monthly_savings_sgd: number;
  potential_annual_savings_sgd: number;
}

export interface TrendWarning {
  utility_type: string;
  trend_direction: string;
  months_affected: number;
  average_monthly_change_percent: number | null;
  description: string;
  severity: Severity;
}

export interface Recommendation {
  category: RecommendationCategory;
  title: string;
  description: string;
  potential_savings_percent: number | null;
  priority: number;
}

export interface DiagnosisResult {
  anomalies: AnomalyFlag[];
  efficiency_issues: EfficiencyIssue[];
  trend_warnings: TrendWarning[];
  overall_health_score: number;
  health_grade: string;
  recommendations: Recommendation[];
  summary: string;
  diagnosis_timestamp: string;
  utilities_analyzed: string[];
  total_potential_monthly_savings_sgd: number;
  total_potential_annual_savings_sgd: number;
}

export interface FormData {
  source_type: string;
  original_filename: string;
  extracted_texts: string[];
  text_count: number;
  combined_text: string;
  extraction_data: ExtractionData;
  diagnosis?: DiagnosisResult;
}

export interface OCRResult {
  id: string;
  form_type: string;
  form_data: FormData;
}

export interface BillData {
  currentBill: number;
  previousBill: number | null;
  currentUsage: number;
  previousUsage: number | null;
  nationalAverage: number;
  neighbourAverage: number;
  billingPeriod: string;
  accountNumber: string;
  tariffRate: number | null;
  gasUsage: number | null;
  gasCharges: number | null;
  waterUsage: number | null;
  waterCharges: number | null;
  customerName: string | null;
  address: string | null;
  providerName: string | null;
}

export interface ChartData {
  month: string;
  consumption: number;
  average: number;
}

export interface UtilityData {
  currentUsage: number;
  previousUsage: number | null;
  nationalAverage: number;
  neighbourAverage: number;
  charges: number;
  unit: string;
  trendDirection: "increasing" | "decreasing" | "stable";
  chartData: ChartData[];
}

// ROI Calculator types
export interface ROIProduct {
  product_type: string;
  display_name: string;
  min_voucher_tick: number;
  max_ticks: number;
  typical_price_range: [number, number];
}

export interface ROIResult {
  product_type: string;
  product_display_name: string;
  current_rating: number;
  new_rating: number;
  tick_improvement: number;
  product_price: number;
  voucher_amount: number;
  net_cost: number;
  annual_energy_savings_kwh: number;
  annual_savings_sgd: number;
  monthly_savings_sgd: number;
  payback_period_months: number;
  payback_period_years: number;
  net_benefit_5_years: number;
  net_benefit_10_years: number;
  roi_percent_annual: number;
  is_voucher_eligible: boolean;
  minimum_rating_for_voucher: number;
  notes: string[];
}

export interface UpgradeRecommendation {
  product_type: string;
  product_display_name: string;
  reason: string;
  estimated_annual_savings: number;
  priority: number;
  roi_if_upgraded: ROIResult | null;
}
