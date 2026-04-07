import axios, { AxiosError } from 'axios';
import type {
  ExtractionResponse,
  CalculateRequest,
  DCFResult,
  SensitivityMatrix,
  NarrativeRequest,
  NarrativeResponse,
  ValuationResult,
  ApprovalRequest,
  MemoryEntry,
  MemoryInsights,
  AgentInfo,
  BatchValuationResult,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
});

function handleError(err: unknown): never {
  if (err instanceof AxiosError) {
    const message =
      (err.response?.data as { detail?: string })?.detail ??
      err.message ??
      'Network error';
    throw new Error(message);
  }
  throw err;
}

export async function uploadPDF(
  file: File,
  companyName?: string,
  ticker?: string,
  useRag: boolean = true,
  useWebSearch: boolean = true
): Promise<ExtractionResponse> {
  try {
    const form = new FormData();
    form.append('file', file);
    
    if (companyName) form.append('company_name', companyName);
    if (ticker) form.append('ticker', ticker);
    form.append('use_rag', String(useRag));
    form.append('use_web_search', String(useWebSearch));
    
    const { data } = await api.post<ExtractionResponse>('/extract/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180_000,
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function extractData(text: string): Promise<ExtractionResponse> {
  try {
    const { data } = await api.post<ExtractionResponse>('/extract/text', { text });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function calculateDCF(
  request: CalculateRequest,
  saveToDb: boolean = true
): Promise<DCFResult> {
  try {
    const { data } = await api.post<DCFResult>('/calculate', request, {
      params: { save_to_db: saveToDb }
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function sensitivityAnalysis(
  request: CalculateRequest,
): Promise<SensitivityMatrix> {
  try {
    const { data } = await api.post<SensitivityMatrix>('/sensitivity', request);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function generateNarrative(
  request: NarrativeRequest,
): Promise<NarrativeResponse> {
  try {
    const { data } = await api.post<NarrativeResponse>('/narrative', request);
    return data;
  } catch (err) {
    handleError(err);
  }
}

// Database-related API functions
export async function getTrends(ticker: string) {
  try {
    const { data } = await api.get(`/trends/${ticker}`);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function loadFromDb(ticker: string) {
  try {
    const { data } = await api.get(`/load-from-db/${ticker}`);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getValuationHistory(ticker: string, limit: number = 10) {
  try {
    const { data } = await api.get(`/valuation-history/${ticker}`, {
      params: { limit }
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getAllValuationHistory(limit: number = 50) {
  try {
    const { data } = await api.get(`/valuation-history`, {
      params: { limit }
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function downloadReport(valuationId: number, format: 'json' | 'txt' = 'txt') {
  try {
    const response = await fetch(`/api/report/${valuationId}/download?format=${format}`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('Download failed');
    }
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `dcf_report_${valuationId}.${format}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename\*?=['"]?([^'"\r\n]+)/i);
      if (match) {
        filename = match[1];
      }
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    return true;
  } catch (err) {
    handleError(err);
    return false;
  }
}

// =============================================================================
// Agent V2 - Multi-Agent System APIs
// =============================================================================

export async function runValuation(ticker: string, forceUpdate: boolean = false) {
  try {
    const { data } = await api.post('/agent/v2/valuation', {
      ticker,
      force_update: forceUpdate
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function runBatchValuation(tickers: string[], forceUpdate: boolean = false) {
  try {
    const { data } = await api.post<BatchValuationResult>('/agent/v2/valuation/batch', {
      tickers,
      force_update: forceUpdate
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getWorkflowStatus(workflowId: string) {
  try {
    const { data } = await api.get(`/agent/v2/valuation/status/${workflowId}`);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getPendingWorkflows() {
  try {
    const { data } = await api.get('/agent/v2/valuation/pending');
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// Approval APIs
// =============================================================================

export async function getPendingApprovals() {
  try {
    const { data } = await api.get<{ success: boolean; count: number; approvals: ApprovalRequest[] }>(
      '/agent/v2/approval/pending'
    );
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function respondToApproval(
  workflowId: string,
  approved: boolean,
  comments?: string
) {
  try {
    const { data } = await api.post('/agent/v2/approval/respond', {
      workflow_id: workflowId,
      approved,
      approver: 'web_user',
      comments
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// Memory APIs
// =============================================================================

export async function searchMemory(query: string, ticker?: string, limit: number = 10) {
  try {
    const { data } = await api.post<{ success: boolean; count: number; results: MemoryEntry[] }>(
      '/agent/v2/memory/search',
      { query, ticker, limit }
    );
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getCompanyMemory(ticker: string, limit: number = 20) {
  try {
    const { data } = await api.get<{ success: boolean; ticker: string; count: number; history: MemoryEntry[] }>(
      `/agent/v2/memory/company/${ticker}`
    );
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getCompanyInsights(ticker: string) {
  try {
    const { data } = await api.get<{ success: boolean; ticker: string; insights: MemoryInsights }>(
      `/agent/v2/memory/insights/${ticker}`
    );
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getMemoryStats() {
  try {
    const { data } = await api.get('/agent/v2/memory/stats');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function clearMemory(olderThanDays?: number) {
  try {
    const url = olderThanDays 
      ? `/agent/v2/memory/clear?older_than_days=${olderThanDays}`
      : '/agent/v2/memory/clear';
    const { data } = await api.delete(url);
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// Agent Info API
// =============================================================================

export async function getAgentInfo() {
  try {
    const { data } = await api.get<{ success: boolean; agents: AgentInfo[]; total_agents: number }>(
      '/agent/v2/info'
    );
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// LLM Reasoning API
// =============================================================================

export async function llmReasoning(
  taskType: 'classify_industry' | 'recommend_valuation' | 'decide_action' | 'explain_result',
  context: Record<string, unknown>
) {
  try {
    const { data } = await api.post('/agent/v2/reasoning', {
      task_type: taskType,
      context
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// Scheduled Tasks APIs
// =============================================================================

export async function getSchedulerStatus() {
  try {
    const { data } = await api.get('/scheduled/status');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function runScheduledFetchNow() {
  try {
    const { data } = await api.post('/scheduled/run-now');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getFetchSummary(days: number = 7) {
  try {
    const { data } = await api.get('/scheduled/summary', {
      params: { days }
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function updateSchedulerConfig(config: {
  fetch_hours?: number[];
  fetch_minute?: number;
  batch_size?: number;
  analysis_enabled?: boolean;
  report_enabled?: boolean;
  notification_emails?: string[];
  enabled?: boolean;
}) {
  try {
    const { data } = await api.post('/scheduled/config', config);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getSchedulerConfig() {
  try {
    const { data } = await api.get('/scheduled/config');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function enableScheduler() {
  try {
    const { data } = await api.post('/scheduled/enable');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function disableScheduler() {
  try {
    const { data } = await api.post('/scheduled/disable');
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getMonitoredTickers() {
  try {
    const { data } = await api.get('/scheduled/tick');
    return data;
  } catch (err) {
    handleError(err);
  }
}

// =============================================================================
// Data Fetch APIs - Enhanced
// =============================================================================

export async function checkTickerData(ticker: string) {
  try {
    const { data } = await api.get(`/scheduled/check-ticker/${ticker}`);
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getFetchLogs(ticker?: string, limit: number = 50) {
  try {
    const params = ticker ? { ticker, limit } : { limit };
    const { data } = await api.get('/scheduled/fetch-logs', { params });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function getTickerFetchHistory(ticker: string, days: number = 30) {
  try {
    const { data } = await api.get(`/scheduled/fetch-history/${ticker}`, {
      params: { days }
    });
    return data;
  } catch (err) {
    handleError(err);
  }
}

export async function triggerSingleFetch(ticker: string) {
  try {
    const { data } = await api.post(`/scheduled/trigger-fetch/${ticker}`);
    return data;
  } catch (err) {
    handleError(err);
  }
}
