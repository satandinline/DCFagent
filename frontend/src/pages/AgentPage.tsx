import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Input,
  Space,
  Statistic,
  Progress,
  Modal,
  Form,
  Select,
  message,
  Popconfirm,
  Spin,
  Alert,
  Descriptions,
  Badge,
  Timeline,
  Tooltip,
} from 'antd';
import {
  RobotOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SyncOutlined,
  PlusOutlined,
  DeleteOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  runValuation,
  runBatchValuation,
  getAgentInfo,
  getPendingWorkflows,
  getWorkflowStatus,
} from '@/services/api';
import type { AgentInfo, ValuationResult } from '@/types';

const { Search } = Input;

export default function AgentPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [pendingWorkflows, setPendingWorkflows] = useState<any[]>([]);
  const [singleTicker, setSingleTicker] = useState('');
  const [batchTickers, setBatchTickers] = useState('');
  const [valuationResults, setValuationResults] = useState<any[]>([]);
  const [runningWorkflows, setRunningWorkflows] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadAgentInfo();
    loadPendingWorkflows();
  }, []);

  const loadAgentInfo = async () => {
    try {
      const data = await getAgentInfo();
      if (data.success) {
        setAgents(data.agents);
      }
    } catch (err) {
      console.error('Failed to load agent info:', err);
    }
  };

  const loadPendingWorkflows = async () => {
    try {
      const data = await getPendingWorkflows();
      if (data.success) {
        setPendingWorkflows(data.pending || []);
      }
    } catch (err) {
      console.error('Failed to load pending workflows:', err);
    }
  };

  const handleSingleValuation = async () => {
    if (!singleTicker.trim()) {
      message.warning(t('agent.enterTicker'));
      return;
    }

    setLoading(true);
    try {
      const result = await runValuation(singleTicker.trim().toUpperCase());
      
      if (result.success) {
        if (result.requires_approval) {
          message.info(t('agent.approvalRequired'));
          loadPendingWorkflows();
        } else {
          message.success(t('agent.valuationComplete'));
          if (result.analysis) {
            setValuationResults(prev => [result.analysis, ...prev].slice(0, 20));
          }
        }
      } else {
        message.error(result.error || t('agent.valuationFailed'));
      }
    } catch (err) {
      message.error(t('agent.valuationFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleBatchValuation = async () => {
    const tickers = batchTickers
      .split(/[,\n]/)
      .map(t => t.trim().toUpperCase())
      .filter(t => t.length > 0);

    if (tickers.length === 0) {
      message.warning(t('agent.enterTickers'));
      return;
    }

    setLoading(true);
    try {
      const result = await runBatchValuation(tickers);
      
      if (result.total !== undefined) {
        message.success(t('agent.batchComplete', { total: result.total, completed: result.completed }));
        
        // Update pending count
        if (result.pending_approval > 0) {
          message.info(t('agent.pendingApprovals', { count: result.pending_approval }));
        }
        
        loadPendingWorkflows();
      } else {
        message.error(t('agent.batchFailed'));
      }
    } catch (err) {
      message.error(t('agent.batchFailed'));
    } finally {
      setLoading(false);
    }
  };

  const getActionTag = (action: string) => {
    const colors: Record<string, string> = {
      BUY: 'green',
      HOLD: 'orange',
      SELL: 'red',
    };
    return <Tag color={colors[action] || 'default'}>{action}</Tag>;
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode }> = {
      running: { color: 'processing', icon: <SyncOutlined spin /> },
      completed: { color: 'success', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', icon: <CloseCircleOutlined /> },
      awaiting_approval: { color: 'warning', icon: <ExclamationCircleOutlined /> },
      rejected: { color: 'error', icon: <CloseCircleOutlined /> },
    };
    const c = config[status] || { color: 'default', icon: null };
    return (
      <Badge status={c.color as any} text={status.replace('_', ' ')} />
    );
  };

  const agentColumns = [
    {
      title: t('agent.agent'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Tag icon={<RobotOutlined />}>{name}</Tag>,
    },
    {
      title: t('agent.role'),
      dataIndex: 'role',
      key: 'role',
    },
    {
      title: t('agent.capabilities'),
      dataIndex: 'capabilities',
      key: 'capabilities',
      render: (caps: string[]) => (
        <Space wrap>
          {caps.map(cap => (
            <Tag key={cap} color="blue">{cap.replace('_', ' ')}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('agent.tools'),
      dataIndex: 'tools',
      key: 'tools',
      render: (tools: string[]) => (
        <Tooltip title={tools.join(', ')}>
          <span>{tools.length} tools</span>
        </Tooltip>
      ),
    },
    {
      title: t('agent.successRate'),
      key: 'metrics',
      render: (_: any, record: AgentInfo) => {
        const rate = record.metrics.success_rate * 100;
        return (
          <Progress
            percent={rate}
            size="small"
            status={rate > 80 ? 'success' : rate > 50 ? 'normal' : 'exception'}
          />
        );
      },
    },
  ];

  const workflowColumns = [
    {
      title: t('agent.ticker'),
      dataIndex: 'ticker',
      key: 'ticker',
      render: (ticker: string) => <Tag color="cyan">{ticker}</Tag>,
    },
    {
      title: t('agent.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: t('agent.approvalId'),
      dataIndex: 'approval_request_id',
      key: 'approval_request_id',
      render: (id: string) => id ? <Tag>{id.slice(0, 8)}...</Tag> : '-',
    },
  ];

  const resultColumns = [
    {
      title: t('agent.ticker'),
      dataIndex: 'ticker',
      key: 'ticker',
      render: (ticker: string) => <Tag color="cyan">{ticker}</Tag>,
    },
    {
      title: t('agent.action'),
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => getActionTag(action),
    },
    {
      title: t('agent.upside'),
      dataIndex: 'upside_percent',
      key: 'upside_percent',
      render: (upside: number) => (
        <span style={{ color: upside > 0 ? '#52c41a' : '#ff4d4f' }}>
          {upside > 0 ? '+' : ''}{upside.toFixed(1)}%
        </span>
      ),
    },
    {
      title: t('agent.fairValue'),
      dataIndex: 'fair_value',
      key: 'fair_value',
      render: (val: number) => val ? `$${val.toFixed(2)}` : '-',
    },
    {
      title: t('agent.currentPrice'),
      dataIndex: 'current_price',
      key: 'current_price',
      render: (val: number) => val ? `$${val.toFixed(2)}` : '-',
    },
    {
      title: t('agent.confidence'),
      dataIndex: 'confidence',
      key: 'confidence',
      render: (conf: string) => {
        const colors: Record<string, string> = {
          高: 'green', high: 'green',
          中: 'orange', medium: 'orange',
          低: 'red', low: 'red',
        };
        return <Tag color={colors[conf] || 'default'}>{conf}</Tag>;
      },
    },
    {
      title: t('agent.industry'),
      dataIndex: 'industry',
      key: 'industry',
    },
    {
      title: t('agent.method'),
      dataIndex: 'primary_method',
      key: 'primary_method',
      render: (method: string) => method || '-',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <RobotOutlined />
            {t('agent.title')}
          </h2>
          <p className="text-gray-500">{t('agent.subtitle')}</p>
        </div>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadAgentInfo}>
            {t('agent.refresh')}
          </Button>
        </Space>
      </div>

      {/* Agent Status Cards */}
      <Row gutter={16}>
        {agents.map(agent => (
          <Col span={6} key={agent.name}>
            <Card size="small">
              <Statistic
                title={agent.role}
                value={agent.metrics.tasks_executed}
                suffix={
                  <Tooltip title={`成功率: ${(agent.metrics.success_rate * 100).toFixed(1)}%`}>
                    <Tag color={agent.metrics.success_rate > 0.8 ? 'green' : 'orange'}>
                      {(agent.metrics.success_rate * 100).toFixed(0)}%
                    </Tag>
                  </Tooltip>
                }
              />
              <div className="mt-2">
                <Progress
                  percent={agent.metrics.success_rate * 100}
                  size="small"
                  showInfo={false}
                />
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Valuation Controls */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title={t('agent.singleValuation')}>
            <Space.Compact className="w-full">
              <Input
                placeholder={t('agent.enterTickerPlaceholder')}
                value={singleTicker}
                onChange={e => setSingleTicker(e.target.value)}
                onPressEnter={handleSingleValuation}
                prefix={<SearchOutlined />}
              />
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleSingleValuation}
                loading={loading}
              >
                {t('agent.run')}
              </Button>
            </Space.Compact>
          </Card>
        </Col>
        <Col span={12}>
          <Card title={t('agent.batchValuation')}>
            <Space.Compact className="w-full">
              <Input.TextArea
                placeholder={t('agent.enterTickersPlaceholder')}
                value={batchTickers}
                onChange={e => setBatchTickers(e.target.value)}
                rows={1}
              />
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleBatchValuation}
                loading={loading}
              >
                {t('agent.runBatch')}
              </Button>
            </Space.Compact>
          </Card>
        </Col>
      </Row>

      {/* Pending Approvals Alert */}
      {pendingWorkflows.length > 0 && (
        <Alert
          message={t('agent.pendingApprovalsTitle')}
          description={t('agent.pendingApprovalsDesc', { count: pendingWorkflows.length })}
          type="warning"
          showIcon
          icon={<ClockCircleOutlined />}
          action={
            <Button size="small" onClick={loadPendingWorkflows}>
              {t('agent.view')}
            </Button>
          }
        />
      )}

      {/* Agent Info Table */}
      <Card title={t('agent.agentInfo')}>
        <Table
          columns={agentColumns}
          dataSource={agents}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Pending Workflows */}
      {pendingWorkflows.length > 0 && (
        <Card title={t('agent.pendingWorkflows')}>
          <Table
            columns={workflowColumns}
            dataSource={pendingWorkflows}
            rowKey="workflow_id"
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Recent Results */}
      {valuationResults.length > 0 && (
        <Card title={t('agent.recentResults')}>
          <Table
            columns={resultColumns}
            dataSource={valuationResults}
            rowKey="ticker"
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      )}
    </div>
  );
}
