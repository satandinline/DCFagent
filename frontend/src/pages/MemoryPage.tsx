import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Table,
  Tag,
  Button,
  Input,
  Space,
  Row,
  Col,
  Statistic,
  message,
  Empty,
  Modal,
  Descriptions,
  List,
  Progress,
  Popconfirm,
  Alert,
  Spin,
} from 'antd';
import {
  SearchOutlined,
  SyncOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  DeleteOutlined,
  EyeOutlined,
  BarChartOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import {
  searchMemory,
  getCompanyMemory,
  getCompanyInsights,
  getMemoryStats,
  clearMemory,
} from '@/services/api';
import type { MemoryEntry, MemoryInsights } from '@/types';

const { Search } = Input;

export default function MemoryPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [tickerInput, setTickerInput] = useState('');
  const [searchResults, setSearchResults] = useState<MemoryEntry[]>([]);
  const [companyHistory, setCompanyHistory] = useState<MemoryEntry[]>([]);
  const [companyInsights, setCompanyInsights] = useState<MemoryInsights | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<MemoryEntry | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getMemoryStats();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Failed to load memory stats:', err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      message.warning(t('memory.enterQuery'));
      return;
    }

    setLoading(true);
    try {
      const data = await searchMemory(searchQuery, tickerInput || undefined);
      if (data.success) {
        setSearchResults(data.results || []);
        message.success(t('memory.searchComplete', { count: data.count }));
      }
    } catch (err) {
      message.error(t('memory.searchFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleTickerSearch = async () => {
    if (!tickerInput.trim()) {
      message.warning(t('memory.enterTicker'));
      return;
    }

    setLoading(true);
    try {
      const [historyData, insightsData] = await Promise.all([
        getCompanyMemory(tickerInput.trim().toUpperCase()),
        getCompanyInsights(tickerInput.trim().toUpperCase()),
      ]);

      if (historyData.success) {
        setCompanyHistory(historyData.history || []);
      }
      if (insightsData.success) {
        setCompanyInsights(insightsData.insights);
      }

      if (historyData.success || insightsData.success) {
        message.success(t('memory.tickerSearchComplete'));
      }
    } catch (err) {
      message.error(t('memory.searchFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleClearMemory = async (olderThanDays?: number) => {
    try {
      const result = await clearMemory(olderThanDays);
      if (result.success) {
        message.success(t('memory.cleared', { count: result.cleared_count }));
        loadStats();
      }
    } catch (err) {
      message.error(t('memory.clearFailed'));
    }
  };

  const showDetail = (entry: MemoryEntry) => {
    setSelectedEntry(entry);
    setDetailVisible(true);
  };

  const getActionTag = (action: string) => {
    const colors: Record<string, string> = {
      BUY: 'green',
      HOLD: 'orange',
      SELL: 'red',
    };
    return <Tag color={colors[action] || 'default'}>{action}</Tag>;
  };

  const searchColumns = [
    {
      title: t('memory.ticker'),
      dataIndex: ['metadata', 'ticker'],
      key: 'ticker',
      render: (ticker: string) => ticker ? <Tag color="cyan">{ticker}</Tag> : '-',
    },
    {
      title: t('memory.company'),
      dataIndex: ['metadata', 'company_name'],
      key: 'company_name',
    },
    {
      title: t('memory.action'),
      dataIndex: ['metadata', 'action'],
      key: 'action',
      render: (action: string) => action ? getActionTag(action) : '-',
    },
    {
      title: t('memory.upside'),
      dataIndex: ['metadata', 'upside_percent'],
      key: 'upside',
      render: (upside: number) => upside !== undefined ? (
        <span style={{ color: upside > 0 ? '#52c41a' : '#ff4d4f' }}>
          {upside > 0 ? '+' : ''}{upside.toFixed(1)}%
        </span>
      ) : '-',
    },
    {
      title: t('memory.industry'),
      dataIndex: ['metadata', 'industry'],
      key: 'industry',
    },
    {
      title: t('memory.confidence'),
      dataIndex: ['metadata', 'confidence'],
      key: 'confidence',
      render: (conf: string) => conf || '-',
    },
    {
      title: t('memory.date'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleDateString(),
    },
    {
      title: t('memory.actions'),
      key: 'actions',
      render: (_: any, record: MemoryEntry) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => showDetail(record)}
        >
          {t('memory.view')}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <DatabaseOutlined />
            {t('memory.title')}
          </h2>
          <p className="text-gray-500">{t('memory.subtitle')}</p>
        </div>
        <Space>
          <Popconfirm
            title={t('memory.confirmClear')}
            onConfirm={() => handleClearMemory()}
          >
            <Button danger icon={<DeleteOutlined />}>
              {t('memory.clearAll')}
            </Button>
          </Popconfirm>
          <Button icon={<SyncOutlined />} onClick={loadStats}>
            {t('memory.refresh')}
          </Button>
        </Space>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('memory.totalEntries')}
                value={stats.total_entries || 0}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('memory.storageType')}
                value={stats.storage_type || 'unknown'}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title={t('memory.collection')}
                value={stats.collection_name || '-'}
                prefix={<LineChartOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Search Section */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title={t('memory.semanticSearch')}>
            <Space.Compact className="w-full mb-4">
              <Input
                placeholder={t('memory.searchPlaceholder')}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onPressEnter={handleSearch}
                prefix={<SearchOutlined />}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
                loading={loading}
              >
                {t('memory.search')}
              </Button>
            </Space.Compact>
            <p className="text-gray-500 text-sm">
              {t('memory.semanticSearchTip')}
            </p>
          </Card>
        </Col>
        <Col span={12}>
          <Card title={t('memory.companyHistory')}>
            <Space.Compact className="w-full mb-4">
              <Input
                placeholder={t('memory.tickerPlaceholder')}
                value={tickerInput}
                onChange={e => setTickerInput(e.target.value)}
                onPressEnter={handleTickerSearch}
                prefix={<SearchOutlined />}
              />
              <Button
                type="primary"
                icon={<HistoryOutlined />}
                onClick={handleTickerSearch}
                loading={loading}
              >
                {t('memory.lookup')}
              </Button>
            </Space.Compact>
            <p className="text-gray-500 text-sm">
              {t('memory.tickerSearchTip')}
            </p>
          </Card>
        </Col>
      </Row>

      {/* Company Insights */}
      {companyInsights && companyInsights.has_history && (
        <Card title={t('memory.insights')}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title={t('memory.analysisCount')}
                value={companyInsights.analysis_count}
                prefix={<BarChartOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={t('memory.avgUpside')}
                value={companyInsights.average_upside.toFixed(1)}
                suffix="%"
                valueStyle={{ 
                  color: companyInsights.average_upside > 0 ? '#52c41a' : '#ff4d4f' 
                }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={t('memory.confidenceTrend')}
                value={companyInsights.confidence_trend}
              />
            </Col>
            <Col span={6}>
              <div>
                <label>{t('memory.actionDistribution')}</label>
                <div className="mt-2">
                  {Object.entries(companyInsights.action_distribution).map(([action, count]) => (
                    <Tag key={action} color={action === 'BUY' ? 'green' : action === 'SELL' ? 'red' : 'orange'}>
                      {action}: {count as number}
                    </Tag>
                  ))}
                </div>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <Card title={t('memory.searchResults')}>
          <Table
            columns={searchColumns}
            dataSource={searchResults}
            rowKey="memory_id"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      {/* Company History */}
      {companyHistory.length > 0 && (
        <Card title={t('memory.historyFor', { ticker: tickerInput.toUpperCase() })}>
          <Table
            columns={searchColumns}
            dataSource={companyHistory}
            rowKey="memory_id"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      {/* Empty State */}
      {searchResults.length === 0 && companyHistory.length === 0 && !companyInsights?.has_history && (
        <Empty description={t('memory.noResults')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      {/* Detail Modal */}
      <Modal
        title={t('memory.detailTitle')}
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setSelectedEntry(null);
        }}
        footer={null}
        width={600}
      >
        {selectedEntry && (
          <div className="space-y-4">
            <Descriptions bordered column={1}>
              <Descriptions.Item label={t('memory.memoryId')}>
                {selectedEntry.memory_id}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.ticker')}>
                {selectedEntry.metadata?.ticker || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.company')}>
                {selectedEntry.metadata?.company_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.industry')}>
                {selectedEntry.metadata?.industry || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.action')}>
                {selectedEntry.metadata?.action ? getActionTag(selectedEntry.metadata.action) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.upside')}>
                {selectedEntry.metadata?.upside_percent !== undefined 
                  ? `${selectedEntry.metadata.upside_percent.toFixed(1)}%`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.confidence')}>
                {selectedEntry.metadata?.confidence || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('memory.date')}>
                {new Date(selectedEntry.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <div>
              <label className="font-medium">{t('memory.content')}</label>
              <div className="mt-2 p-4 bg-gray-50 rounded whitespace-pre-wrap text-sm">
                {selectedEntry.content}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
