import { Card, Statistic, Row, Col, Tag } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  BankOutlined,
  FundOutlined,
  StockOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import type { DCFResult as DCFResultType } from '@/types';

function formatLargeNumber(value: number, currency: string): string {
  const abs = Math.abs(value);
  if (currency === 'CNY' || currency === 'RMB') {
    if (abs >= 1e8) return `¥${(value / 1e8).toFixed(2)}亿`;
    if (abs >= 1e4) return `¥${(value / 1e4).toFixed(2)}万`;
    return `¥${value.toFixed(2)}`;
  }
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

interface Props {
  result?: DCFResultType;
}

export default function DCFResultComponent({ result: propResult }: Props) {
  const { t } = useTranslation();
  const storeResult = useStore((s) => s.dcfResult);
  const financialData = useStore((s) => s.financialData);

  const result = propResult ?? storeResult;
  if (!result) return null;

  const currency = financialData?.currency ?? 'CNY';
  const upside = result.upside_downside ?? 0;
  const isPositive = upside >= 0;

  const metrics = [
    {
      title: t('result.summary.enterprise_value'),
      value: formatLargeNumber(result.enterprise_value, currency),
      icon: <BankOutlined />,
      color: '#1677ff',
    },
    {
      title: t('result.summary.equity_value'),
      value: formatLargeNumber(result.equity_value, currency),
      icon: <FundOutlined />,
      color: '#722ed1',
    },
    {
      title: t('result.summary.per_share_value'),
      value: formatLargeNumber(result.per_share_value, currency),
      icon: <StockOutlined />,
      color: '#13c2c2',
    },
  ];

  return (
    <div className="space-y-4">
      <Row gutter={[16, 16]}>
        {metrics.map((m) => (
          <Col xs={24} md={8} key={m.title}>
            <Card hoverable className="text-center shadow-md border-t-4" style={{ borderTopColor: m.color }}>
              <div className="text-3xl mb-2" style={{ color: m.color }}>
                {m.icon}
              </div>
              <Statistic
                title={m.title}
                value={m.value}
                valueStyle={{ fontSize: 28, fontWeight: 700, color: m.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        {result.current_price != null && result.current_price > 0 && (
          <Col xs={12} md={6}>
            <Card size="small">
              <Statistic
                title={t('result.summary.current_price')}
                value={formatLargeNumber(result.current_price, currency)}
                valueStyle={{ fontSize: 18 }}
              />
            </Card>
          </Col>
        )}

        {result.upside_downside != null && (
          <Col xs={12} md={6}>
            <Card size="small">
              <Statistic
                title={t('result.summary.upside_downside')}
                value={Math.abs(upside * 100).toFixed(1)}
                prefix={isPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                suffix="%"
                valueStyle={{ color: isPositive ? '#3f8600' : '#cf1322', fontSize: 18 }}
              />
              <Tag color={isPositive ? 'success' : 'error'} className="mt-1">
                {isPositive ? 'Undervalued' : 'Overvalued'}
              </Tag>
            </Card>
          </Col>
        )}

        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('result.summary.wacc_used')}
              value={(result.wacc_used * 100).toFixed(2)}
              suffix="%"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>

        <Col xs={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('result.summary.terminal_growth')}
              value={(result.terminal_growth_used * 100).toFixed(2)}
              suffix="%"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
