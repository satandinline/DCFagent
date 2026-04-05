import { useMemo } from 'react';
import { Card, Collapse, InputNumber, Slider, Statistic, Tag } from 'antd';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import type { DCFParameters } from '@/types';

interface ParamConfig {
  key: keyof DCFParameters;
  min: number;
  max: number;
  step: number;
  displayMultiplier: number;
  suffix: string;
  integer?: boolean;
}

const paramConfigs: ParamConfig[] = [
  { key: 'wacc', min: 0, max: 0.2, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'revenue_growth_rate', min: 0, max: 0.3, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'terminal_growth_rate', min: 0, max: 0.05, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'operating_margin', min: 0, max: 0.5, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'tax_rate', min: 0, max: 0.5, step: 0.01, displayMultiplier: 100, suffix: '%' },
  { key: 'capex_ratio', min: 0, max: 0.2, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'da_ratio', min: 0, max: 0.2, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'nwc_ratio', min: 0, max: 0.1, step: 0.001, displayMultiplier: 100, suffix: '%' },
  { key: 'projection_years', min: 1, max: 10, step: 1, displayMultiplier: 1, suffix: '', integer: true },
];

function ParamSlider({
  config,
  value,
  onChange,
  label,
}: {
  config: ParamConfig;
  value: number;
  onChange: (v: number) => void;
  label: string;
}) {
  const displayValue = config.displayMultiplier === 1 ? value : +(value * config.displayMultiplier).toFixed(2);
  const sliderMin = config.displayMultiplier === 1 ? config.min : config.min * config.displayMultiplier;
  const sliderMax = config.displayMultiplier === 1 ? config.max : config.max * config.displayMultiplier;
  const sliderStep = config.displayMultiplier === 1 ? config.step : +(config.step * config.displayMultiplier).toFixed(4);

  const handleSlider = (v: number) => {
    onChange(config.displayMultiplier === 1 ? v : v / config.displayMultiplier);
  };

  const handleInput = (v: number | null) => {
    if (v == null) return;
    onChange(config.displayMultiplier === 1 ? v : v / config.displayMultiplier);
  };

  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
        <Tag color="blue">
          {displayValue}
          {config.suffix}
        </Tag>
      </div>
      <div className="flex items-center gap-3">
        <Slider
          className="flex-1"
          min={sliderMin}
          max={sliderMax}
          step={sliderStep}
          value={displayValue}
          onChange={handleSlider}
          tooltip={{ formatter: (v) => `${v}${config.suffix}` }}
        />
        <InputNumber
          size="small"
          className="!w-24"
          min={sliderMin}
          max={sliderMax}
          step={sliderStep}
          value={displayValue}
          onChange={handleInput}
          addonAfter={config.suffix || undefined}
        />
      </div>
    </div>
  );
}

export default function ParamPanel() {
  const { t } = useTranslation();
  const { dcfParameters, financialData, setDCFParameters } = useStore();

  const waccPreview = useMemo(() => {
    if (!financialData) return dcfParameters.wacc;
    const equityWeight = 1 - (financialData.total_debt / (financialData.total_debt + financialData.shares_outstanding * (financialData.current_stock_price ?? 0) || 1));
    const debtWeight = 1 - equityWeight;
    const costOfEquity = financialData.risk_free_rate + financialData.beta * (financialData.market_return - financialData.risk_free_rate);
    return costOfEquity * equityWeight + financialData.cost_of_debt * (1 - financialData.tax_rate) * debtWeight;
  }, [financialData, dcfParameters.wacc]);

  const handleChange = (key: keyof DCFParameters, value: number) => {
    setDCFParameters({ [key]: value });
  };

  const rateParams = paramConfigs.filter((p) =>
    ['wacc', 'revenue_growth_rate', 'terminal_growth_rate'].includes(p.key),
  );
  const marginParams = paramConfigs.filter((p) =>
    ['operating_margin', 'tax_rate'].includes(p.key),
  );
  const ratioParams = paramConfigs.filter((p) =>
    ['capex_ratio', 'da_ratio', 'nwc_ratio'].includes(p.key),
  );
  const otherParams = paramConfigs.filter((p) => p.key === 'projection_years');

  const collapseItems = [
    {
      key: 'rates',
      label: t('analysis.params.wacc'),
      children: (
        <>
          {rateParams.map((cfg) => (
            <ParamSlider
              key={cfg.key}
              config={cfg}
              value={dcfParameters[cfg.key] as number}
              onChange={(v) => handleChange(cfg.key, v)}
              label={t(`analysis.params.${cfg.key}`)}
            />
          ))}
        </>
      ),
    },
    {
      key: 'margins',
      label: t('analysis.params.operating_margin'),
      children: (
        <>
          {marginParams.map((cfg) => (
            <ParamSlider
              key={cfg.key}
              config={cfg}
              value={dcfParameters[cfg.key] as number}
              onChange={(v) => handleChange(cfg.key, v)}
              label={t(`analysis.params.${cfg.key}`)}
            />
          ))}
        </>
      ),
    },
    {
      key: 'ratios',
      label: t('analysis.params.capex_ratio'),
      children: (
        <>
          {ratioParams.map((cfg) => (
            <ParamSlider
              key={cfg.key}
              config={cfg}
              value={dcfParameters[cfg.key] as number}
              onChange={(v) => handleChange(cfg.key, v)}
              label={t(`analysis.params.${cfg.key}`)}
            />
          ))}
        </>
      ),
    },
    {
      key: 'other',
      label: t('analysis.params.projection_years'),
      children: (
        <>
          {otherParams.map((cfg) => (
            <ParamSlider
              key={cfg.key}
              config={cfg}
              value={dcfParameters[cfg.key] as number}
              onChange={(v) => handleChange(cfg.key, v)}
              label={t(`analysis.params.${cfg.key}`)}
            />
          ))}
        </>
      ),
    },
  ];

  return (
    <Card
      title={t('analysis.params.title')}
      size="small"
      className="sticky top-4"
    >
      {financialData && (
        <div className="mb-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <Statistic
            title={t('analysis.params.wacc') + ' (CAPM)'}
            value={(waccPreview * 100).toFixed(2)}
            suffix="%"
            valueStyle={{ fontSize: 20, fontWeight: 700, color: '#1677ff' }}
          />
        </div>
      )}
      <Collapse
        defaultActiveKey={['rates', 'margins', 'ratios', 'other']}
        ghost
        items={collapseItems}
      />
    </Card>
  );
}
