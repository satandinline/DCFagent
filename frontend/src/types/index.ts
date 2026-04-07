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

// =============================================================================
// Agent V2 Types - Multi-Agent System
// =============================================================================

export interface WorkflowStatus {
  workflow_id: string;
  ticker: string;
  status: 'running' | 'completed' | 'failed' | 'awaiting_approval' | 'rejected';
  requires_approval: boolean;
  approval_request_id?: string;
  analysis_result?: ValuationResult;
}

export interface ValuationResult {
  ticker: string;
  company_name?: string;
  industry?: string;
  action: 'BUY' | 'HOLD' | 'SELL';
  upside_percent: number;
  confidence: '高' | '中' | '低' | 'high' | 'medium' | 'low';
  fair_value?: number;
  current_price?: number;
  primary_method?: string;
  reasoning?: string;
  warnings?: string[];
}

export interface ApprovalRequest {
  id: string;
  requestor: string;
  request_type: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';
  details: {
    ticker?: string;
    analysis_result?: ValuationResult;
  };
  created_at: string;
  expires_at?: string;
  approver_comments?: string;
  approver?: string;
}

export interface MemoryEntry {
  memory_id: string;
  content: string;
  metadata: {
    ticker?: string;
    company_name?: string;
    industry?: string;
    action?: string;
    upside_percent?: number;
    confidence?: string;
    timestamp?: string;
  };
  created_at: string;
}

export interface MemoryInsights {
  has_history: boolean;
  analysis_count: number;
  action_distribution: Record<string, number>;
  average_upside: number;
  confidence_trend: string;
  message?: string;
}

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  tools: string[];
  metrics: {
    tasks_executed: number;
    tasks_succeeded: number;
    tasks_failed: number;
    total_execution_time: number;
    success_rate: number;
    avg_execution_time: number;
  };
}

export interface BatchValuationResult {
  total: number;
  completed: number;
  pending_approval: number;
  failed: number;
  results: Array<{
    ticker: string;
    success: boolean;
    workflow_id?: string;
    error?: string;
  }>;
}
