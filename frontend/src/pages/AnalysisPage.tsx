import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tabs, Button, Card, Spin, Descriptions, InputNumber, Input, message } from 'antd';
import {
  CloudUploadOutlined,
  EditOutlined,
  CalculatorOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import { calculateDCF, sensitivityAnalysis, generateNarrative } from '@/services/api';
import type { FinancialData } from '@/types';

/* ---------- lazy component imports (will be created separately) ---------- */
import FileUpload from '@/components/FileUpload';
import ManualInput from '@/components/ManualInput';
import ParamPanel from '@/components/ParamPanel';

const pctFields: (keyof FinancialData)[] = [
  'revenue_growth',
  'operating_margin',
  'tax_rate',
  'risk_free_rate',
  'market_return',
  'cost_of_debt',
];

export default function AnalysisPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    financialData,
    setFinancialData,
    dcfParameters,
    setDCFResult,
    setSensitivityMatrix,
    setNarrative,
    loading,
    setLoading,
    setError,
    language,
  } = useStore();

  const [activeTab, setActiveTab] = useState('upload');
  const [calcStep, setCalcStep] = useState('');

  const handleFieldChange = useCallback(
    (field: keyof FinancialData, value: number | string | null) => {
      if (!financialData) return;
      setFinancialData({ ...financialData, [field]: value ?? 0 });
    },
    [financialData, setFinancialData],
  );

  const canCalculate = !!financialData?.company_name && !!financialData?.revenue;

  const handleCalculate = async () => {
    if (!financialData) {
      message.warning(t('common.no_data'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      const request = { financial_data: financialData, parameters: dcfParameters };

      setCalcStep(t('analysis.calculating'));
      const dcfResult = await calculateDCF(request);
      setDCFResult(dcfResult);

      setCalcStep(t('analysis.sensitivity_btn'));
      const matrix = await sensitivityAnalysis(request);
      setSensitivityMatrix(matrix);

      setCalcStep(t('analysis.generating'));
      const narrativeResp = await generateNarrative({
        financial_data: financialData,
        dcf_result: dcfResult,
        sensitivity_matrix: matrix,
        language,
      });
      if (narrativeResp.success && narrativeResp.narrative) {
        setNarrative(narrativeResp.narrative);
      }

      message.success(t('common.success'));
      navigate('/result');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('common.error');
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
      setCalcStep('');
    }
  };

  /* ---------- Financial data summary (editable) ---------- */
  const renderDataSummary = () => {
    if (!financialData) return null;

    return (
      <Card
        size="small"
        title={
          <span className="text-sm font-medium">
            {financialData.company_name} — {t('analysis.fields.fiscal_year')} {financialData.fiscal_year}
          </span>
        }
        className="mt-4 !border-primary-500/20 dark:!border-primary-300/20"
      >
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" colon={false}>
          {Object.entries(financialData).map(([key, val]) => {
            if (key === 'company_name' || key === 'ticker' || key === 'currency' || key === 'fiscal_year') {
              return (
                <Descriptions.Item key={key} label={t(`analysis.fields.${key}`)}>
                  <Input
                    size="small"
                    value={val as string}
                    onChange={(e) => handleFieldChange(key as keyof FinancialData, e.target.value)}
                    className="!w-28"
                  />
                </Descriptions.Item>
              );
            }
            const isPct = pctFields.includes(key as keyof FinancialData);
            return (
              <Descriptions.Item key={key} label={t(`analysis.fields.${key}`)}>
                <InputNumber
                  size="small"
                  value={val as number}
                  onChange={(v) => handleFieldChange(key as keyof FinancialData, v)}
                  className="!w-32"
                  formatter={(v) =>
                    isPct ? `${((v as number) * 100).toFixed(1)}%` : String(v ?? '')
                  }
                  parser={(v) => {
                    const n = parseFloat((v ?? '').replace('%', ''));
                    return isPct ? n / 100 : n;
                  }}
                />
              </Descriptions.Item>
            );
          })}
        </Descriptions>
      </Card>
    );
  };

  return (
    <Spin spinning={loading} tip={calcStep || t('common.loading')} size="large">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* LEFT: data input */}
        <div className="flex-1 min-w-0">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'upload',
                label: (
                  <span className="flex items-center gap-1.5">
                    <CloudUploadOutlined />
                    {t('analysis.tabs.upload')}
                  </span>
                ),
                children: <FileUpload />,
              },
              {
                key: 'manual',
                label: (
                  <span className="flex items-center gap-1.5">
                    <EditOutlined />
                    {t('analysis.tabs.manual')}
                  </span>
                ),
                children: <ManualInput />,
              },
            ]}
            className="analysis-tabs"
          />

          {renderDataSummary()}
        </div>

        {/* RIGHT: DCF parameters */}
        <div className="w-full lg:w-80 xl:w-96 shrink-0">
          <ParamPanel />
        </div>
      </div>

      {/* Bottom calculate button */}
      <div className="flex justify-center mt-8 mb-4">
        <Button
          type="primary"
          size="large"
          icon={loading ? <ThunderboltOutlined className="animate-pulse" /> : <CalculatorOutlined />}
          onClick={handleCalculate}
          disabled={!canCalculate || loading}
          className="!h-12 !px-10 !text-base !font-semibold !rounded-xl hover:!scale-105 transition-transform"
          style={{
            background: canCalculate
              ? 'linear-gradient(135deg, #2b6cb0, #3182ce)'
              : undefined,
            boxShadow: canCalculate ? '0 4px 20px rgba(43, 108, 176, 0.35)' : undefined,
          }}
        >
          {loading ? calcStep || t('analysis.calculating') : t('analysis.calculate_btn')}
        </Button>
      </div>
    </Spin>
  );
}
