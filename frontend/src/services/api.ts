import axios, { AxiosError } from 'axios';
import type {
  ExtractionResponse,
  CalculateRequest,
  DCFResult,
  SensitivityMatrix,
  NarrativeRequest,
  NarrativeResponse,
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
