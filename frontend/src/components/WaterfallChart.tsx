import ReactECharts from 'echarts-for-react';
import { useTranslation } from 'react-i18next';
import type { DCFResult, FinancialData } from '@/types';

interface Props {
  dcfResult: DCFResult;
  financialData: FinancialData;
}

function formatVal(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(value / 1e4).toFixed(1)}万`;
  return value.toFixed(0);
}

export default function WaterfallChart({ dcfResult, financialData }: Props) {
  const { t } = useTranslation();

  const steps = [
    { name: t('result.terminal.pv_fcf'), value: dcfResult.pv_fcf_sum, isTotal: false },
    { name: t('result.terminal.pv_terminal'), value: dcfResult.pv_terminal_value, isTotal: false },
    { name: t('result.summary.enterprise_value'), value: dcfResult.enterprise_value, isTotal: true },
    { name: `-${t('analysis.fields.total_debt')}`, value: -financialData.total_debt, isTotal: false },
    { name: `+${t('analysis.fields.cash_and_equivalents')}`, value: financialData.cash_and_equivalents, isTotal: false },
    { name: t('result.summary.equity_value'), value: dcfResult.equity_value, isTotal: true },
  ];

  const transparent: number[] = [];
  const positive: (number | string)[] = [];
  const negative: (number | string)[] = [];

  let cumulative = 0;
  for (const step of steps) {
    if (step.isTotal) {
      transparent.push(0);
      positive.push(step.value >= 0 ? step.value : '-');
      negative.push(step.value < 0 ? Math.abs(step.value) : '-');
      cumulative = step.value;
    } else {
      if (step.value >= 0) {
        transparent.push(cumulative);
        positive.push(step.value);
        negative.push('-');
        cumulative += step.value;
      } else {
        cumulative += step.value;
        transparent.push(cumulative);
        positive.push('-');
        negative.push(Math.abs(step.value));
      }
    }
  }

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: { seriesName: string; value: number | string; axisValue: string }[]) => {
        if (!Array.isArray(params)) return '';
        const label = params[0]?.axisValue ?? '';
        const idx = steps.findIndex((s) => s.name === label);
        if (idx < 0) return label;
        return `<strong>${label}</strong><br/>${formatVal(steps[idx].value)}`;
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '6%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: steps.map((s) => s.name),
      axisLabel: { fontSize: 11, interval: 0, rotate: 15 },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { formatter: (v: number) => formatVal(v), fontSize: 12 },
      splitLine: { lineStyle: { type: 'dashed' as const, color: '#e8e8e8' } },
    },
    series: [
      {
        name: 'Transparent',
        type: 'bar' as const,
        stack: 'waterfall',
        data: transparent,
        itemStyle: { color: 'transparent' },
        emphasis: { itemStyle: { color: 'transparent' } },
      },
      {
        name: 'Positive',
        type: 'bar' as const,
        stack: 'waterfall',
        data: positive,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        label: {
          show: true,
          position: 'top' as const,
          fontSize: 11,
          formatter: (params: { dataIndex: number }) => {
            return formatVal(steps[params.dataIndex].value);
          },
        },
        barMaxWidth: 50,
      },
      {
        name: 'Negative',
        type: 'bar' as const,
        stack: 'waterfall',
        data: negative,
        itemStyle: { color: '#ff4d4f', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 50,
      },
    ],
  };

  return (
    <ReactECharts option={option} style={{ height: 400 }} opts={{ renderer: 'canvas' }} />
  );
}
