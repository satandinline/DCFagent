import { create } from 'zustand';
import type {
  AppState,
  DCFParameters,
  DCFResult,
  FinancialData,
  Language,
  SensitivityMatrix,
} from '@/types';

const defaultParameters: DCFParameters = {
  projection_years: 5,
  revenue_growth_rate: 0.08,
  terminal_growth_rate: 0.025,
  operating_margin: 0.15,
  tax_rate: 0.25,
  capex_ratio: 0.05,
  da_ratio: 0.04,
  nwc_ratio: 0.02,
  wacc: 0.1,
};

export const useStore = create<AppState>((set) => ({
  theme: 'light',
  language: 'zh',
  financialData: null,
  dcfParameters: { ...defaultParameters },
  dcfResult: null,
  sensitivityMatrix: null,
  narrative: '',
  extractedText: '',
  loading: false,
  error: '',

  setFinancialData: (data: FinancialData | null) => set({ financialData: data }),

  setDCFParameters: (params: Partial<DCFParameters>) =>
    set((state) => ({
      dcfParameters: { ...state.dcfParameters, ...params },
    })),

  setDCFResult: (result: DCFResult | null) => set({ dcfResult: result }),

  setSensitivityMatrix: (matrix: SensitivityMatrix | null) =>
    set({ sensitivityMatrix: matrix }),

  setNarrative: (narrative: string) => set({ narrative }),

  setExtractedText: (text: string) => set({ extractedText: text }),

  setLoading: (loading: boolean) => set({ loading }),

  setError: (error: string) => set({ error }),

  setLanguage: (lang: Language) => set({ language: lang }),

  toggleTheme: () =>
    set((state) => ({
      theme: state.theme === 'light' ? 'dark' : 'light',
    })),

  resetAll: () =>
    set({
      financialData: null,
      dcfParameters: { ...defaultParameters },
      dcfResult: null,
      sensitivityMatrix: null,
      narrative: '',
      extractedText: '',
      loading: false,
      error: '',
    }),
}));
