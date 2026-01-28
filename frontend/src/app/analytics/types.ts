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

export interface FormData {
  source_type: string;
  original_filename: string;
  extracted_texts: string[];
  text_count: number;
  combined_text: string;
  extraction_data: ExtractionData;
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
