import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Spin, Empty, Tag, App } from 'antd';
import { ArrowLeftOutlined, HistoryOutlined, DownloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getAllValuationHistory, downloadReport } from '@/services/api';

interface ValuationRecord {
  id: number;
  ticker?: string;
  date: string;
  company_name: string;
  per_share_value: number | null;
  enterprise_value: number | null;
  equity_value: number | null;
  wacc_used: number | null;
  current_price: number | null;
  upside_downside: number | null;
  created_by: string;
}

export default function HistoryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<ValuationRecord[]>([]);

  useEffect(() => {
    loadAllHistory();
  }, []);

  const loadAllHistory = async () => {
    setLoading(true);
    try {
      const response = await getAllValuationHistory(50);
      if (response.success) {
        setHistory(response.valuations || []);
      } else {
        message.error(t('upload.load_error'));
      }
    } catch (error) {
      console.error('Error loading history:', error);
      message.error(t('upload.trend_error'));
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: t('history.ticker'),
      dataIndex: 'ticker',
      key: 'ticker',
      render: (ticker: string | undefined) => ticker || '-',
    },
    {
      title: t('history.date'),
      dataIndex: 'date',
      key: 'date',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('history.company_name'),
      dataIndex: 'company_name',
      key: 'company_name',
    },
    {
      title: t('history.per_share_value'),
      dataIndex: 'per_share_value',
      key: 'per_share_value',
      render: (value: number | null) => 
        value ? `$${value.toFixed(2)}` : '-',
    },
    {
      title: t('history.enterprise_value'),
      dataIndex: 'enterprise_value',
      key: 'enterprise_value',
      render: (value: number | null) => 
        value ? `$${(value / 1e9).toFixed(2)}B` : '-',
    },
    {
      title: t('history.wacc'),
      dataIndex: 'wacc_used',
      key: 'wacc_used',
      render: (value: number | null) => 
        value ? `${(value * 100).toFixed(2)}%` : '-',
    },
    {
      title: t('history.current_price'),
      dataIndex: 'current_price',
      key: 'current_price',
      render: (value: number | null) => 
        value ? `$${value.toFixed(2)}` : '-',
    },
    {
      title: t('history.upside_downside'),
      dataIndex: 'upside_downside',
      key: 'upside_downside',
      render: (value: number | null) => {
        if (!value) return '-';
        const percent = (value * 100).toFixed(2);
        const isPositive = value > 0;
        return (
          <Tag color={isPositive ? 'green' : 'red'}>
            {isPositive ? '+' : ''}{percent}%
          </Tag>
        );
      },
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 100,
      render: (_: any, record: ValuationRecord) => (
        <Button 
          type="link" 
          icon={<DownloadOutlined />} 
          onClick={() => handleDownload(record.id)}
        >
          {t('common.export')}
        </Button>
      ),
    },
  ];

  const handleDownload = async (valuationId: number) => {
    try {
      const success = await downloadReport(valuationId, 'txt');
      if (success) {
        message.success(t('common.download_success'));
      } else {
        message.error(t('common.download_error'));
      }
    } catch (error) {
      console.error('Download error:', error);
      message.error(t('common.download_error'));
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <Card
        title={
          <div className="flex items-center gap-2">
            <HistoryOutlined />
            <span>{t('history.title')}</span>
          </div>
        }
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}> 
            {t('history.back_home')}
          </Button>
        }
      >
        <Spin spinning={loading}>
          {history.length > 0 ? (
            <Table
              columns={columns}
              dataSource={history}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              scroll={{ x: true }}
            />
          ) : (
            <Empty description={t('history.no_records')} />
          )}
        </Spin>
      </Card>
    </div>
  );
}
