import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Statistic,
  Modal,
  Select,
  message,
  Spin,
  Descriptions,
  Empty,
  Tabs,
} from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import {
  getSchedulerStatus,
  runScheduledFetchNow,
  getFetchSummary,
  getMonitoredTickers,
  checkTickerData,
  getTickerFetchHistory,
  triggerSingleFetch,
  enableScheduler,
  disableScheduler,
} from '@/services/api';

interface FetchHistory {
  id: number;
  fetch_date: string;
  fetch_type: string;
  data_found: boolean;
  new_data_available: boolean;
  records_fetched: number;
  analysis_triggered: boolean;
  report_sent: boolean;
  error?: string;
  summary?: any;
}

export default function DataFetchPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);
  const [fetchSummary, setFetchSummary] = useState<any>(null);
  const [tickers, setTickers] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [tickerCheckResult, setTickerCheckResult] = useState<any>(null);
  const [fetchHistory, setFetchHistory] = useState<FetchHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalContent, setModalContent] = useState<any>(null);

  useEffect(() => {
    loadSchedulerStatus();
    loadFetchSummary();
    loadMonitoredTickers();
  }, []);

  const loadSchedulerStatus = async () => {
    try {
      const data = await getSchedulerStatus();
      if (data.success) {
        setSchedulerStatus(data.data);
      }
    } catch (err) {
      console.error('Failed to load scheduler status:', err);
    }
  };

  const loadFetchSummary = async () => {
    try {
      const data = await getFetchSummary(7);
      if (data.success) {
        setFetchSummary(data.data);
      }
    } catch (err) {
      console.error('Failed to load fetch summary:', err);
    }
  };

  const loadMonitoredTickers = async () => {
    try {
      const data = await getMonitoredTickers();
      if (data.success) {
        setTickers(data.tickers);
      }
    } catch (err) {
      console.error('Failed to load tickers:', err);
    }
  };

  const handleCheckTicker = async (ticker: string) => {
    setLoading(true);
    try {
      const data = await checkTickerData(ticker);
      if (data.success) {
        setTickerCheckResult(data);
        message.info(ticker + ': ' + data.message);
      }
    } catch (err) {
      message.error('Failed to check ticker data');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerFetch = async (ticker: string) => {
    setLoading(true);
    try {
      const data = await triggerSingleFetch(ticker);
      if (data.success) {
        const result = data.result;
        let msg = `${ticker}: `;
        if (result.data_changed) {
          msg += 'New data found and processed';
          if (result.analysis_triggered) msg += ', analysis completed';
          if (result.report_sent) msg += ', report sent';
        } else {
          msg += 'No new data to process';
        }
        message.success(msg);
        
        // Refresh history
        await loadFetchHistory(ticker);
        await loadFetchSummary();
      }
    } catch (err) {
      message.error('Failed to trigger fetch');
    } finally {
      setLoading(false);
    }
  };

  const loadFetchHistory = async (ticker: string) => {
    setHistoryLoading(true);
    try {
      const data = await getTickerFetchHistory(ticker, 30);
      if (data.success) {
        setFetchHistory(data.history);
      }
    } catch (err) {
      console.error('Failed to load fetch history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleRunAllFetch = async () => {
    setLoading(true);
    try {
      const data = await runScheduledFetchNow();
      if (data.success) {
        const result = data.result;
        message.success(
          `Fetch completed: ${result.tickers_checked} checked, ` +
          `${result.new_data_found} with new data, ` +
          `${result.analysis_triggered} analyses, ` +
          `${result.reports_sent} reports`
        );
        await loadFetchSummary();
        await loadSchedulerStatus();
      }
    } catch (err) {
      message.error('Failed to run scheduled fetch');
    } finally {
      setLoading(false);
    }
  };

  const handleEnableScheduler = async () => {
    try {
      const data = await enableScheduler();
      if (data.success) {
        message.success('Scheduler enabled');
        await loadSchedulerStatus();
      }
    } catch (err) {
      message.error('Failed to enable scheduler');
    }
  };

  const handleDisableScheduler = async () => {
    try {
      const data = await disableScheduler();
      if (data.success) {
        message.success('Scheduler disabled');
        await loadSchedulerStatus();
      }
    } catch (err) {
      message.error('Failed to disable scheduler');
    }
  };

  const showDetailModal = (title: string, content: any) => {
    setModalTitle(title);
    setModalContent(content);
    setModalVisible(true);
  };

  const historyColumns = [
    {
      title: t('fetch.date'),
      dataIndex: 'fetch_date',
      key: 'fetch_date',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('fetch.type'),
      dataIndex: 'fetch_type',
      key: 'fetch_type',
      width: 100,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('fetch.status'),
      key: 'status',
      width: 120,
      render: (_: any, record: FetchHistory) => {
        if (record.error) {
          return <Tag color="error" icon={<CloseCircleOutlined />}>Error</Tag>;
        }
        if (!record.data_found) {
          return <Tag color="default">No Data</Tag>;
        }
        if (!record.new_data_available) {
          return <Tag color="blue">Checked</Tag>;
        }
        if (record.analysis_triggered && record.report_sent) {
          return <Tag color="success" icon={<CheckCircleOutlined />}>Complete</Tag>;
        }
        if (record.analysis_triggered) {
          return <Tag color="processing">Analyzed</Tag>;
        }
        return <Tag color="cyan">Data Found</Tag>;
      },
    },
    {
      title: t('fetch.records'),
      dataIndex: 'records_fetched',
      key: 'records_fetched',
      width: 80,
      render: (count: number) => count || '-',
    },
    {
      title: t('fetch.actions'),
      key: 'actions',
      width: 120,
      render: (_: any, record: FetchHistory) => (
        <Space>
          {record.summary && (
            <Button 
              size="small" 
              onClick={() => showDetailModal('Fetch Details', record.summary)}
            >
              Details
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tickerColumns = [
    {
      title: t('fetch.ticker'),
      dataIndex: 'ticker',
      key: 'ticker',
      width: 100,
      render: (ticker: string) => <Tag color="cyan">{ticker}</Tag>,
    },
    {
      title: t('fetch.lastCheck'),
      key: 'lastCheck',
      width: 180,
      render: (_: any, record: any) => {
        const stats = fetchSummary?.ticker_stats?.find((s: any) => s.ticker === record);
        return stats?.last_fetch 
          ? new Date(stats.last_fetch).toLocaleString()
          : '-';
      },
    },
    {
      title: t('fetch.newDataCount'),
      key: 'newDataCount',
      width: 120,
      render: (_: any, record: any) => {
        const stats = fetchSummary?.ticker_stats?.find((s: any) => s.ticker === record);
        return stats?.new_data_count || 0;
      },
    },
    {
      title: t('fetch.actions'),
      key: 'actions',
      width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button 
            size="small" 
            icon={<SearchOutlined />}
            onClick={() => handleCheckTicker(record)}
            loading={loading}
          >
            Check
          </Button>
          <Button 
            size="small" 
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleTriggerFetch(record)}
            loading={loading}
          >
            Fetch
          </Button>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'overview',
      label: t('fetch.overview'),
      children: (
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('fetch.totalFetches')}
                value={fetchSummary?.total_fetches || 0}
                prefix={<SyncOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('fetch.withNewData')}
                value={fetchSummary?.fetches_with_new_data || 0}
                valueStyle={{ color: '#3f8600' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('fetch.analysesTriggered')}
                value={fetchSummary?.analyses_triggered || 0}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('fetch.reportsSent')}
                value={fetchSummary?.reports_sent || 0}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'monitored',
      label: t('fetch.monitoredTickers'),
      children: (
        <>
          <div className="mb-4 flex justify-between items-center">
            <Space>
              <Button 
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleRunAllFetch}
                loading={loading}
              >
                {t('fetch.runAll')}
              </Button>
              <Button 
                icon={<SyncOutlined />} 
                onClick={loadMonitoredTickers}
              >
                {t('fetch.refresh')}
              </Button>
            </Space>
            <Space>
              {schedulerStatus?.is_running ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>
                  {t('fetch.schedulerRunning')}
                </Tag>
              ) : (
                <Tag color="default" icon={<CloseCircleOutlined />}>
                  {t('fetch.schedulerStopped')}
                </Tag>
              )}
              {schedulerStatus?.is_running ? (
                <Button danger onClick={handleDisableScheduler}>
                  {t('fetch.disableScheduler')}
                </Button>
              ) : (
                <Button type="primary" onClick={handleEnableScheduler}>
                  {t('fetch.enableScheduler')}
                </Button>
              )}
            </Space>
          </div>
          
          {tickers.length > 0 ? (
            <Table
              columns={tickerColumns}
              dataSource={tickers.map(t => ({ ticker: t, key: t }))}
              rowKey="ticker"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          ) : (
            <Empty description={t('fetch.noTickers')} />
          )}
        </>
      ),
    },
    {
      key: 'history',
      label: t('fetch.fetchHistory'),
      children: (
        <>
          <div className="mb-4">
            <Select
              placeholder={t('fetch.selectTicker')}
              style={{ width: 200 }}
              onChange={(value) => {
                setSelectedTicker(value);
                loadFetchHistory(value);
              }}
              value={selectedTicker}
            >
              {tickers.map(t => (
                <Select.Option key={t} value={t}>{t}</Select.Option>
              ))}
            </Select>
          </div>
          
          {selectedTicker ? (
            <Spin spinning={historyLoading}>
              <Table
                columns={historyColumns}
                dataSource={fetchHistory}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 10 }}
              />
            </Spin>
          ) : (
            <Empty description={t('fetch.selectTickerToView')} />
          )}
        </>
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
            {t('fetch.title')}
          </h2>
          <p className="text-gray-500">{t('fetch.subtitle')}</p>
        </div>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadSchedulerStatus}>
            {t('fetch.refresh')}
          </Button>
        </Space>
      </div>

      {/* Scheduler Status */}
      <Card>
        <Descriptions column={3}>
          <Descriptions.Item label={t('fetch.schedulerStatus')}>
            {schedulerStatus?.is_running ? (
              <Tag color="success">{t('fetch.running')}</Tag>
            ) : (
              <Tag color="default">{t('fetch.stopped')}</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label={t('fetch.nextRun')}>
            {schedulerStatus?.next_run 
              ? new Date(schedulerStatus.next_run).toLocaleString()
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('fetch.schedule')}>
            12:00 & 00:00 ({t('fetch.daily')})
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Tabs */}
      <Card>
        <Tabs items={tabItems} />
      </Card>

      {/* Ticker Check Result */}
      {tickerCheckResult && (
        <Card title={t('fetch.checkResult', { ticker: tickerCheckResult.ticker })}>
          <Descriptions column={2}>
            <Descriptions.Item label={t('fetch.lastFetch')}>
              {tickerCheckResult.last_fetch || t('fetch.noHistory')}
            </Descriptions.Item>
            <Descriptions.Item label={t('fetch.hasNewData')}>
              <Tag color={tickerCheckResult.has_new_data ? 'success' : 'default'}>
                {tickerCheckResult.has_new_data ? t('fetch.yes') : t('fetch.no')}
              </Tag>
            </Descriptions.Item>
            {tickerCheckResult.data_changes && (
              <>
                <Descriptions.Item label={t('fetch.newIncome')}>
                  {tickerCheckResult.data_changes.new_income_statements_count}
                </Descriptions.Item>
                <Descriptions.Item label={t('fetch.newBalance')}>
                  {tickerCheckResult.data_changes.new_balance_sheets_count}
                </Descriptions.Item>
                <Descriptions.Item label={t('fetch.newCashflow')}>
                  {tickerCheckResult.data_changes.new_cash_flows_count}
                </Descriptions.Item>
                <Descriptions.Item label={t('fetch.newPrices')}>
                  {tickerCheckResult.data_changes.new_prices_count}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        </Card>
      )}

      {/* Detail Modal */}
      <Modal
        title={modalTitle}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            {t('common.close')}
          </Button>
        ]}
        width={600}
      >
        {modalContent && (
          <pre style={{ maxHeight: 400, overflow: 'auto' }}>
            {JSON.stringify(modalContent, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
}
