import ReactECharts from 'echarts-for-react';
import { Card, Spin, Empty } from 'antd';
import { useTranslation } from 'react-i18next';

interface TrendData {
  revenue_trend?: number[];
  profit_trend?: number[];
  margin_trend?: number[];
  years?: string[];
  cagr?: number;
}

interface TrendChartProps {
  data: TrendData | null;
  loading?: boolean;
}

export default function TrendChart({ data, loading = false }: TrendChartProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <Card title={t('trend.title')}>
        <Spin size="large" className="w-full py-12" />
      </Card>
    );
  }

  if (!data || !data.years || data.years.length === 0) {
    return (
      <Card title={t('trend.title')}>
        <Empty description={t('trend.no_data')} />
      </Card>
    );
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
    },
    legend: {
      data: [t('trend.revenue'), t('trend.profit'), t('trend.margin')],
      top: 10,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.years,
    },
    yAxis: [
      {
        type: 'value',
        name: t('trend.amount'),
        position: 'left',
        axisLabel: {
          formatter: (value: number) => {
            if (Math.abs(value) >= 1e9) {
              return `${(value / 1e9).toFixed(1)}B`;
            }
            if (Math.abs(value) >= 1e6) {
              return `${(value / 1e6).toFixed(1)}M`;
            }
            return value.toLocaleString();
          },
        },
      },
      {
        type: 'value',
        name: t('trend.margin'),
        position: 'right',
        axisLabel: {
          formatter: '{value}%',
        },
      },
    ],
    series: [
      {
        name: t('trend.revenue'),
        type: 'line',
        smooth: true,
        data: data.revenue_trend || [],
        itemStyle: {
          color: '#1890ff',
        },
        areaStyle: {
          color: 'rgba(24, 144, 255, 0.1)',
        },
      },
      {
        name: t('trend.profit'),
        type: 'line',
        smooth: true,
        data: data.profit_trend || [],
        itemStyle: {
          color: '#52c41a',
        },
      },
      {
        name: t('trend.margin'),
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: data.margin_trend || [],
        itemStyle: {
          color: '#faad14',
        },
        lineStyle: {
          type: 'dashed',
        },
      },
    ],
  };

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <span>{t('trend.title')}</span>
          {data.cagr && (
            <span className="text-sm text-gray-500">
              {t('trend.cagr')}: {(data.cagr * 100).toFixed(2)}%
            </span>
          )}
        </div>
      }
    >
      <ReactECharts
        option={option}
        style={{ height: 400 }}
        opts={{ renderer: 'canvas' }}
      />
    </Card>
  );
}
