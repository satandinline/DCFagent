import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Button, Spin, message, Empty, Tag } from 'antd';
import { ArrowLeftOutlined, HistoryOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getValuationHistory } from '@/services/api';

interface ValuationRecord {
  id: number;
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
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<ValuationRecord[]>([]);

  useEffect(() => {
    if (ticker) {
      loadHistory();
    }
  }, [ticker]);

  const loadHistory = async () => {
    if (!ticker) return;
    
    setLoading(true);
    try {
      const response = await getValuationHistory(ticker, 20);
      if (response.success) {
        setHistory(response.valuations || []);
      } else {
        message.error('Failed to load history');
      }
    } catch (error) {
      console.error('Error loading history:', error);
      message.error('Error loading valuation history');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
    },
    {
      title: '每股价值',
      dataIndex: 'per_share_value',
      key: 'per_share_value',
      render: (value: number | null) => 
        value ? `$${value.toFixed(2)}` : '-',
    },
    {
      title: '企业价值',
      dataIndex: 'enterprise_value',
      key: 'enterprise_value',
      render: (value: number | null) => 
        value ? `$${(value / 1e9).toFixed(2)}B` : '-',
    },
    {
      title: 'WACC',
      dataIndex: 'wacc_used',
      key: 'wacc_used',
      render: (value: number | null) => 
        value ? `${(value * 100).toFixed(2)}%` : '-',
    },
    {
      title: '当前股价',
      dataIndex: 'current_price',
      key: 'current_price',
      render: (value: number | null) => 
        value ? `$${value.toFixed(2)}` : '-',
    },
    {
      title: '涨跌幅',
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
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <Card
        title={
          <div className="flex items-center gap-2">
            <HistoryOutlined />
            <span>估值历史 - {ticker}</span>
          </div>
        }
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
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
            <Empty description="暂无估值历史记录" />
          )}
        </Spin>
      </Card>
    </div>
  );
}
