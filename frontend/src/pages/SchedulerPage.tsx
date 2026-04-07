import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Switch,
  Space,
  Statistic,
  Modal,
  Form,
  Input,
  message,
  Alert,
  Popconfirm,
  Spin,
  Divider,
  List,
  Badge,
  Tooltip,
  TimePicker,
} from 'antd';
import {
  ClockCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  HistoryOutlined,
  DatabaseOutlined,
  MailOutlined,
} from '@ant-design/icons';
import {
  getSchedulerStatus,
  runScheduledFetchNow,
  getFetchSummary,
  updateSchedulerConfig,
  enableScheduler,
  disableScheduler,
  getMonitoredTickers,
} from '@/services/api';

export default function SchedulerPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [tickers, setTickers] = useState<string[]>([]);
  const [configVisible, setConfigVisible] = useState(false);
  const [notificationEmails, setNotificationEmails] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statusRes, summaryRes, tickersRes] = await Promise.all([
        getSchedulerStatus(),
        getFetchSummary(7),
        getMonitoredTickers(),
      ]);

      if (statusRes.success) {
        setStatus(statusRes.data);
      }
      if (summaryRes.success) {
        setSummary(summaryRes.data);
      }
      if (tickersRes.success) {
        setTickers(tickersRes.tickers || []);
      }
    } catch (err) {
      console.error('Failed to load scheduler data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    Modal.confirm({
      title: t('scheduler.runNowConfirm'),
      content: t('scheduler.runNowDesc'),
      okText: t('common.confirm'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        setLoading(true);
        try {
          const result = await runScheduledFetchNow();
          if (result.success) {
            message.success(t('scheduler.runStarted'));
            // Refresh data after completion
            setTimeout(loadData, 2000);
          } else {
            message.error(result.error || t('scheduler.runFailed'));
          }
        } catch (err) {
          message.error(t('scheduler.runFailed'));
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const handleToggleScheduler = async (enabled: boolean) => {
    try {
      if (enabled) {
        await enableScheduler();
        message.success(t('scheduler.enabled'));
      } else {
        await disableScheduler();
        message.success(t('scheduler.disabled'));
      }
      loadData();
    } catch (err) {
      message.error(t('scheduler.toggleFailed'));
    }
  };

  const handleSaveConfig = async () => {
    setLoading(true);
    try {
      const emails = notificationEmails
        .split(',')
        .map((e) => e.trim())
        .filter((e) => e.length > 0);

      await updateSchedulerConfig({
        notification_emails: emails,
      });

      message.success(t('scheduler.configSaved'));
      setConfigVisible(false);
      loadData();
    } catch (err) {
      message.error(t('scheduler.configSaveFailed'));
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: t('scheduler.ticker'),
      dataIndex: 'ticker',
      key: 'ticker',
      render: (ticker: string) => <Tag color="cyan">{ticker}</Tag>,
    },
    {
      title: t('scheduler.lastFetch'),
      dataIndex: 'last_fetch',
      key: 'last_fetch',
      render: (time: string) =>
        time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: t('scheduler.newDataCount'),
      dataIndex: 'new_data_count',
      key: 'new_data_count',
      render: (count: number) => (
        <Tag color={count > 0 ? 'green' : 'default'}>{count}</Tag>
      ),
    },
  ];

  if (loading && !status) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <ClockCircleOutlined />
            {t('scheduler.title')}
          </h2>
          <p className="text-gray-500">{t('scheduler.subtitle')}</p>
        </div>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadData}>
            {t('scheduler.refresh')}
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => setConfigVisible(true)}>
            {t('scheduler.config')}
          </Button>
        </Space>
      </div>

      {/* Status Alert */}
      <Alert
        message={
          <Space>
            {status?.task_enabled ? (
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
            ) : (
              <PauseCircleOutlined style={{ color: '#faad14' }} />
            )}
            <span>
              {t('scheduler.status')}:{' '}
              {status?.task_enabled ? t('scheduler.enabled') : t('scheduler.disabled')}
            </span>
            {status?.next_run && (
              <span>
                | {t('scheduler.nextRun')}: {new Date(status.next_run).toLocaleString()}
              </span>
            )}
          </Space>
        }
        description={
          status?.is_fetching ? (
            <span>
              <SyncOutlined spin /> {t('scheduler.fetchingInProgress')}
            </span>
          ) : (
            t('scheduler.statusDesc')
          )
        }
        type={status?.task_enabled ? 'success' : 'warning'}
        showIcon
        action={
          <Switch
            checked={status?.task_enabled}
            onChange={handleToggleScheduler}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<CloseCircleOutlined />}
          />
        }
      />

      {/* Quick Actions */}
      <Card>
        <Row gutter={16}>
          <Col span={8}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              size="large"
              block
              onClick={handleRunNow}
              loading={loading}
            >
              {t('scheduler.runNow')}
            </Button>
          </Col>
          <Col span={8}>
            <Statistic
              title={t('scheduler.monitoredCount')}
              value={tickers.length}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('scheduler.nextRun')}
              value={status?.next_run ? new Date(status.next_run).toLocaleTimeString() : '-'}
              suffix={status?.next_run ? '' : t('scheduler.notScheduled')}
            />
          </Col>
        </Row>
      </Card>

      {/* Summary Stats */}
      <Row gutter={16}>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.totalFetches')}
              value={summary?.total_fetches || 0}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.fetchesWithData')}
              value={summary?.fetches_with_data || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.newDataFound')}
              value={summary?.fetches_with_new_data || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.analysesTriggered')}
              value={summary?.analyses_triggered || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.reportsSent')}
              value={summary?.reports_sent || 0}
              prefix={<MailOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title={t('scheduler.skipRate')}
              value={
                summary?.total_fetches
                  ? (((summary?.total_fetches - summary?.fetches_with_new_data) /
                      summary?.total_fetches) * 100).toFixed(1)
                  : 0
              }
              suffix="%"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Activity */}
      <Card
        title={t('scheduler.recentActivity')}
        extra={
          <Tag color="blue">
            {t('scheduler.last7Days')}
          </Tag>
        }
      >
        {summary?.ticker_stats && summary.ticker_stats.length > 0 ? (
          <Table
            columns={columns}
            dataSource={summary.ticker_stats}
            rowKey="ticker"
            pagination={{ pageSize: 10 }}
            size="small"
          />
        ) : (
          <div className="text-center text-gray-500 py-8">
            {t('scheduler.noRecentActivity')}
          </div>
        )}
      </Card>

      {/* Monitored Tickers */}
      <Card
        title={t('scheduler.monitoredTickers')}
        extra={<Tag color="cyan">{tickers.length}</Tag>}
      >
        <List
          grid={{ gutter: 8, xs: 4, sm: 6, md: 8, lg: 10 }}
          dataSource={tickers}
          renderItem={(ticker: string) => (
            <List.Item>
              <Tag color="blue">{ticker}</Tag>
            </List.Item>
          )}
          locale={{ emptyText: t('scheduler.noTickers') }}
        />
      </Card>

      {/* Config Modal */}
      <Modal
        title={t('scheduler.configTitle')}
        open={configVisible}
        onCancel={() => setConfigVisible(false)}
        onOk={handleSaveConfig}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        confirmLoading={loading}
      >
        <Form layout="vertical">
          <Form.Item label={t('scheduler.notificationEmails')}>
            <Input.TextArea
              rows={3}
              value={notificationEmails}
              onChange={(e) => setNotificationEmails(e.target.value)}
              placeholder="email1@example.com, email2@example.com"
            />
          </Form.Item>
          <Form.Item>
            <Alert
              message={t('scheduler.configNote')}
              type="info"
              showIcon
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
