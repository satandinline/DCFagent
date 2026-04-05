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
      <Card title="📈 财务趋势分析">
        <Spin size="large" className="w-full py-12" />
      </Card>
    );
  }

  if (!data || !data.years || data.years.length === 0) {
    return (
      <Card title="📈 财务趋势分析">
        <Empty description="暂无趋势数据" />
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
      data: ['收入', '利润', '利润率'],
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
        name: '金额',
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
        name: '利润率',
        position: 'right',
        axisLabel: {
          formatter: '{value}%',
        },
      },
    ],
    series: [
      {
        name: '收入',
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
        name: '利润',
        type: 'line',
        smooth: true,
        data: data.profit_trend || [],
        itemStyle: {
          color: '#52c41a',
        },
      },
      {
        name: '利润率',
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
          <span>📈 财务趋势分析</span>
          {data.cagr && (
            <span className="text-sm text-gray-500">
              CAGR: {(data.cagr * 100).toFixed(2)}%
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
