export type ThemeMode = 'light' | 'dark';
export type Language = 'zh' | 'en';

export interface FinancialData {
  company_name: string;
  ticker?: string;
  currency: string;
  fiscal_year: number;
  revenue: number;
  revenue_growth: number;
  operating_income: number;
  operating_margin: number;
  net_income: number;
  depreciation_amortization: number;
  capital_expenditure: number;
  change_in_working_capital: number;
  total_debt: number;
  cash_and_equivalents: number;
  shares_outstanding: number;
  tax_rate: number;
  beta: number;
  risk_free_rate: number;
  market_return: number;
  cost_of_debt: number;
  current_stock_price?: number;
}

export interface DCFParameters {
  projection_years: number;
  revenue_growth_rate: number;
  terminal_growth_rate: number;
  operating_margin: number;
  tax_rate: number;
  capex_ratio: number;
  da_ratio: number;
  nwc_ratio: number;
  wacc: number;
  discount_rate_override?: number;
}

export interface FCFProjection {
  year: number;
  revenue: number;
  operating_income: number;
  nopat: number;
  depreciation_amortization: number;
  capital_expenditure: number;
  change_in_nwc: number;
  free_cash_flow: number;
  discount_factor: number;
  present_value: number;
}

export interface DCFResult {
  projections: FCFProjection[];
  terminal_value: number;
  pv_terminal_value: number;
  pv_fcf_sum: number;
  enterprise_value: number;
  equity_value: number;
  per_share_value: number;
  current_price?: number;
  upside_downside?: number;
  wacc_used: number;
  terminal_growth_used: number;
}

export interface SensitivityCell {
  wacc: number;
  terminal_growth: number;
  per_share_value: number;
}

export interface SensitivityMatrix {
  wacc_range: number[];
  growth_range: number[];
  values: number[][];
}

export interface ExtractionResponse {
  success: boolean;
  financial_data?: FinancialData;
  extracted_text?: string;
  error?: string;
}

export interface NarrativeResponse {
  success: boolean;
  narrative?: string;
  error?: string;
}

export interface CalculateRequest {
  financial_data: FinancialData;
  parameters: DCFParameters;
}

export interface NarrativeRequest {
  financial_data: FinancialData;
  dcf_result: DCFResult;
  sensitivity_matrix?: SensitivityMatrix;
  language?: Language;
}

export interface AppState {
  theme: ThemeMode;
  language: Language;
  financialData: FinancialData | null;
  dcfParameters: DCFParameters;
  dcfResult: DCFResult | null;
  sensitivityMatrix: SensitivityMatrix | null;
  narrative: string;
  extractedText: string;
  loading: boolean;
  error: string;
  setFinancialData: (data: FinancialData | null) => void;
  setDCFParameters: (params: Partial<DCFParameters>) => void;
  setDCFResult: (result: DCFResult | null) => void;
  setSensitivityMatrix: (matrix: SensitivityMatrix | null) => void;
  setNarrative: (narrative: string) => void;
  setExtractedText: (text: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string) => void;
  setLanguage: (lang: Language) => void;
  toggleTheme: () => void;
  resetAll: () => void;
}
