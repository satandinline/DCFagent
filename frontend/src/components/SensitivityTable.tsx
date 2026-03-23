import ReactECharts from 'echarts-for-react';
import { useTranslation } from 'react-i18next';
import type { SensitivityMatrix } from '@/types';

interface Props {
  sensitivityMatrix: SensitivityMatrix;
}

export default function SensitivityTable({ sensitivityMatrix }: Props) {
  const { t } = useTranslation();

  if (!sensitivityMatrix?.values?.length) return null;

  const { wacc_range, growth_range, values } = sensitivityMatrix;

  const waccLabels = wacc_range.map((w) => `${(w * 100).toFixed(1)}%`);
  const growthLabels = growth_range.map((g) => `${(g * 100).toFixed(1)}%`);

  const flat = values.flat();
  const minVal = Math.min(...flat);
  const maxVal = Math.max(...flat);

  const heatmapData: [number, number, number][] = [];
  for (let row = 0; row < values.length; row++) {
    for (let col = 0; col < values[row].length; col++) {
      heatmapData.push([col, row, values[row][col]]);
    }
  }

  const option = {
    tooltip: {
      position: 'top' as const,
      formatter: (params: { value: [number, number, number] }) => {
        const [colIdx, rowIdx, val] = params.value;
        return `${t('result.sensitivity.wacc_axis')}: ${waccLabels[rowIdx]}<br/>` +
          `${t('result.sensitivity.growth_axis')}: ${growthLabels[colIdx]}<br/>` +
          `${t('result.summary.per_share_value')}: <strong>${val.toFixed(2)}</strong>`;
      },
    },
    grid: {
      left: '12%',
      right: '12%',
      bottom: '15%',
      top: '6%',
    },
    xAxis: {
      type: 'category' as const,
      data: growthLabels,
      name: t('result.sensitivity.growth_axis'),
      nameLocation: 'center' as const,
      nameGap: 30,
      splitArea: { show: true },
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'category' as const,
      data: waccLabels,
      name: t('result.sensitivity.wacc_axis'),
      nameLocation: 'center' as const,
      nameGap: 50,
      splitArea: { show: true },
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      min: minVal,
      max: maxVal,
      calculable: true,
      orient: 'vertical' as const,
      right: '2%',
      top: 'center',
      inRange: {
        color: ['#c23531', '#e8804e', '#f0c75e', '#91c7ae', '#2f9e44'],
      },
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: 'heatmap' as const,
        data: heatmapData,
        label: {
          show: true,
          fontSize: 10,
          formatter: (params: { value: [number, number, number] }) => {
            return params.value[2].toFixed(1);
          },
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  };

  return (
    <ReactECharts option={option} style={{ height: 420 }} opts={{ renderer: 'canvas' }} />
  );
}
