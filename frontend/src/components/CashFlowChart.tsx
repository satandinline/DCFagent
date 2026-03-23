import ReactECharts from 'echarts-for-react';
import { useTranslation } from 'react-i18next';
import type { FCFProjection } from '@/types';

interface Props {
  projections: FCFProjection[];
}

function formatValue(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e8) return `${(value / 1e8).toFixed(1)}亿`;
  if (abs >= 1e4) return `${(value / 1e4).toFixed(1)}万`;
  return value.toFixed(0);
}

export default function CashFlowChart({ projections }: Props) {
  const { t } = useTranslation();

  if (!projections?.length) return null;

  const years = projections.map((p) => `Year ${p.year}`);
  const revenue = projections.map((p) => p.revenue);
  const operatingIncome = projections.map((p) => p.operating_income);
  const fcf = projections.map((p) => p.free_cash_flow);
  const pv = projections.map((p) => p.present_value);

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: { seriesName: string; value: number; color: string; axisValue?: string }[]) => {
        if (!Array.isArray(params) || params.length === 0) return '';
        let html = `<strong>${params[0]?.axisValue ?? ''}</strong><br/>`;
        for (const item of params) {
          html += `<span style="color:${item.color}">●</span> ${item.seriesName}: ${formatValue(item.value)}<br/>`;
        }
        return html;
      },
    },
    legend: {
      data: [
        t('result.projections.revenue'),
        t('result.projections.operating_income'),
        t('result.projections.fcf'),
        t('result.projections.present_value'),
      ],
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: years,
      axisLabel: { fontSize: 12 },
      axisLine: { lineStyle: { color: '#999' } },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: {
        formatter: (v: number) => formatValue(v),
        fontSize: 12,
      },
      splitLine: { lineStyle: { color: '#e8e8e8', type: 'dashed' as const } },
    },
    series: [
      {
        name: t('result.projections.revenue'),
        type: 'bar' as const,
        data: revenue,
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 30,
      },
      {
        name: t('result.projections.operating_income'),
        type: 'bar' as const,
        data: operatingIncome,
        itemStyle: { color: '#722ed1', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 30,
      },
      {
        name: t('result.projections.fcf'),
        type: 'bar' as const,
        data: fcf,
        itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 30,
      },
      {
        name: t('result.projections.present_value'),
        type: 'line' as const,
        data: pv,
        smooth: true,
        lineStyle: { width: 2, color: '#fa8c16' },
        itemStyle: { color: '#fa8c16' },
        symbol: 'circle',
        symbolSize: 6,
      },
    ],
  };

  return (
    <ReactECharts option={option} style={{ height: 400 }} opts={{ renderer: 'canvas' }} />
  );
}
