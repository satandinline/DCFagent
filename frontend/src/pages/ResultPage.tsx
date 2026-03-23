import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Collapse, Typography, Empty, Tooltip, Tag, Divider } from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  DollarOutlined,
  BankOutlined,
  StockOutlined,
  RiseOutlined,
  FallOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';

import CashFlowChart from '@/components/CashFlowChart';
import SensitivityTable from '@/components/SensitivityTable';
import WaterfallChart from '@/components/WaterfallChart';

const { Title, Text } = Typography;

function fmtCurrency(v: number, compact = true): string {
  if (compact && Math.abs(v) >= 1e8)
    return `${(v / 1e8).toFixed(2)} 亿`;
  if (compact && Math.abs(v) >= 1e4)
    return `${(v / 1e4).toFixed(2)} 万`;
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(2)}%`;
}

export default function ResultPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { financialData, dcfResult, sensitivityMatrix, narrative } = useStore();

  useEffect(() => {
    if (!dcfResult) navigate('/analysis', { replace: true });
  }, [dcfResult, navigate]);

  if (!dcfResult || !financialData) return null;

  const upsidePct = dcfResult.upside_downside;
  const isPositive = upsidePct !== undefined && upsidePct !== null && upsidePct >= 0;

  const summaryCards = [
    {
      key: 'ev',
      label: t('result.summary.enterprise_value'),
      value: fmtCurrency(dcfResult.enterprise_value),
      icon: <BankOutlined />,
      color: '#2b6cb0',
    },
    {
      key: 'equity',
      label: t('result.summary.equity_value'),
      value: fmtCurrency(dcfResult.equity_value),
      icon: <DollarOutlined />,
      color: '#38a169',
    },
    {
      key: 'share',
      label: t('result.summary.per_share_value'),
      value: `¥${dcfResult.per_share_value.toFixed(2)}`,
      icon: <StockOutlined />,
      color: '#d69e2e',
      extra:
        dcfResult.current_price != null && dcfResult.current_price > 0 ? (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <span className="text-gray-400">
              {t('result.summary.current_price')}: ¥{dcfResult.current_price.toFixed(2)}
            </span>
            {upsidePct != null && (
              <Tag
                color={isPositive ? 'success' : 'error'}
                icon={isPositive ? <RiseOutlined /> : <FallOutlined />}
                className="!text-xs"
              >
                {isPositive ? '+' : ''}
                {(upsidePct * 100).toFixed(1)}%
              </Tag>
            )}
          </div>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <Title level={3} className="!mb-1">
            {financialData.company_name}
            {financialData.ticker && (
              <Text type="secondary" className="ml-2 !text-base font-normal">
                ({financialData.ticker})
              </Text>
            )}
          </Title>
          <Text type="secondary" className="text-sm">
            {t('result.title')} — {t('analysis.fields.fiscal_year')} {financialData.fiscal_year} &middot;{' '}
            WACC {fmtPct(dcfResult.wacc_used)} &middot;{' '}
            {t('result.summary.terminal_growth')} {fmtPct(dcfResult.terminal_growth_used)}
          </Text>
        </div>

        <div className="flex gap-2">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/analysis')}>
            {t('common.back')}
          </Button>
          <Tooltip title="Coming soon">
            <Button type="primary" icon={<DownloadOutlined />}>
              {t('common.export')}
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {summaryCards.map((card) => (
          <Card
            key={card.key}
            hoverable
            className="!rounded-2xl !border-0 overflow-hidden"
            style={{
              background: `linear-gradient(135deg, ${card.color}08, ${card.color}15)`,
              boxShadow: `0 2px 12px ${card.color}18`,
            }}
          >
            <div className="flex items-start justify-between">
              <div>
                <Text className="!text-xs !font-medium uppercase tracking-wider" style={{ color: card.color }}>
                  {card.label}
                </Text>
                <div className="mt-1 text-2xl md:text-3xl font-bold text-gray-800 dark:text-gray-100 font-mono">
                  {card.value}
                </div>
                {card.extra}
              </div>
              <div
                className="flex items-center justify-center w-10 h-10 rounded-xl text-lg"
                style={{ background: `${card.color}15`, color: card.color }}
              >
                {card.icon}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Divider className="!my-2" />

      {/* Cash Flow Chart */}
      <Card
        title={t('result.charts.fcf_trend')}
        className="!rounded-2xl shadow-card"
        styles={{ header: { borderBottom: 'none', fontWeight: 600 } }}
      >
        <CashFlowChart projections={dcfResult.projections} />
      </Card>

      {/* Sensitivity + Waterfall Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title={t('result.sensitivity.title')}
          className="!rounded-2xl shadow-card"
          styles={{ header: { borderBottom: 'none', fontWeight: 600 } }}
        >
          {sensitivityMatrix ? (
            <SensitivityTable sensitivityMatrix={sensitivityMatrix} />
          ) : (
            <Empty description={t('common.no_data')} />
          )}
        </Card>

        <Card
          title={t('result.charts.value_bridge')}
          className="!rounded-2xl shadow-card"
          styles={{ header: { borderBottom: 'none', fontWeight: 600 } }}
        >
          <WaterfallChart dcfResult={dcfResult} financialData={financialData} />
        </Card>
      </div>

      {/* AI Narrative */}
      <Collapse
        defaultActiveKey={narrative ? ['narrative'] : []}
        className="!rounded-2xl shadow-card !border-0 overflow-hidden"
        items={[
          {
            key: 'narrative',
            label: (
              <span className="flex items-center gap-2 font-semibold">
                <FileTextOutlined className="text-primary-500" />
                {t('result.narrative.title')}
              </span>
            ),
            children: narrative ? (
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap leading-relaxed">
                {narrative}
              </div>
            ) : (
              <Empty description={t('result.narrative.empty')} />
            ),
          },
        ]}
      />
    </div>
  );
}
