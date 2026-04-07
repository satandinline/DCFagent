import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Input,
  message,
  Descriptions,
  Statistic,
  Row,
  Col,
  Alert,
  Empty,
  Spin,
  Timeline,
  Divider,
  Popconfirm,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  getPendingApprovals,
  respondToApproval,
} from '@/services/api';
import type { ApprovalRequest, ValuationResult } from '@/types';

const { TextArea } = Input;

export default function ApprovalsPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [comments, setComments] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadApprovals();
    // Poll for updates every 30 seconds
    const interval = setInterval(loadApprovals, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadApprovals = async () => {
    try {
      const data = await getPendingApprovals();
      if (data.success) {
        setApprovals(data.approvals || []);
      }
    } catch (err) {
      console.error('Failed to load approvals:', err);
    }
  };

  const handleApprove = async (approval: ApprovalRequest) => {
    setActionLoading(true);
    try {
      const result = await respondToApproval(approval.id, true, comments);
      if (result.success) {
        message.success(t('approval.approved'));
        loadApprovals();
        setDetailVisible(false);
        setSelectedApproval(null);
        setComments('');
      } else {
        message.error(result.error || t('approval.failed'));
      }
    } catch (err) {
      message.error(t('approval.failed'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (approval: ApprovalRequest) => {
    if (!comments.trim()) {
      message.warning(t('approval.enterReason'));
      return;
    }
    
    setActionLoading(true);
    try {
      const result = await respondToApproval(approval.id, false, comments);
      if (result.success) {
        message.success(t('approval.rejected'));
        loadApprovals();
        setDetailVisible(false);
        setSelectedApproval(null);
        setComments('');
      } else {
        message.error(result.error || t('approval.failed'));
      }
    } catch (err) {
      message.error(t('approval.failed'));
    } finally {
      setActionLoading(false);
    }
  };

  const showDetail = (approval: ApprovalRequest) => {
    setSelectedApproval(approval);
    setDetailVisible(true);
  };

  const getRiskTag = (level: string) => {
    const colors: Record<string, string> = {
      low: 'green',
      medium: 'orange',
      high: 'red',
      critical: 'purple',
    };
    const labels: Record<string, string> = {
      low: t('approval.riskLow'),
      medium: t('approval.riskMedium'),
      high: t('approval.riskHigh'),
      critical: t('approval.riskCritical'),
    };
    return (
      <Tag color={colors[level] || 'default'}>
        {labels[level] || level}
      </Tag>
    );
  };

  const getActionTag = (action: string) => {
    const colors: Record<string, string> = {
      BUY: 'green',
      HOLD: 'orange',
      SELL: 'red',
    };
    return <Tag color={colors[action] || 'default'}>{action}</Tag>;
  };

  const columns = [
    {
      title: t('approval.ticker'),
      dataIndex: ['details', 'ticker'],
      key: 'ticker',
      render: (ticker: string) => ticker ? <Tag color="cyan">{ticker}</Tag> : '-',
    },
    {
      title: t('approval.riskLevel'),
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level: string) => getRiskTag(level),
    },
    {
      title: t('approval.action'),
      dataIndex: ['details', 'analysis_result', 'action'],
      key: 'action',
      render: (action: string) => action ? getActionTag(action) : '-',
    },
    {
      title: t('approval.upside'),
      dataIndex: ['details', 'analysis_result', 'upside_percent'],
      key: 'upside',
      render: (upside: number) => upside !== undefined ? (
        <span style={{ color: upside > 0 ? '#52c41a' : '#ff4d4f' }}>
          {upside > 0 ? '+' : ''}{upside.toFixed(1)}%
        </span>
      ) : '-',
    },
    {
      title: t('approval.confidence'),
      dataIndex: ['details', 'analysis_result', 'confidence'],
      key: 'confidence',
      render: (conf: string) => conf || '-',
    },
    {
      title: t('approval.requestType'),
      dataIndex: 'request_type',
      key: 'request_type',
    },
    {
      title: t('approval.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: t('approval.actions'),
      key: 'actions',
      render: (_: any, record: ApprovalRequest) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            {t('approval.view')}
          </Button>
          <Popconfirm
            title={t('approval.confirmApprove')}
            onConfirm={() => handleApprove(record)}
          >
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
            >
              {t('approval.approve')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const expandedRowRender = (approval: ApprovalRequest) => {
    const result = approval.details?.analysis_result as ValuationResult;
    if (!result) return null;

    return (
      <Descriptions size="small" column={3} className="pl-8">
        <Descriptions.Item label={t('approval.fairValue')}>
          ${result.fair_value?.toFixed(2) || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('approval.currentPrice')}>
          ${result.current_price?.toFixed(2) || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('approval.industry')}>
          {result.industry || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('approval.method')}>
          {result.primary_method || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('approval.reasoning')} span={2}>
          {result.reasoning || '-'}
        </Descriptions.Item>
        {result.warnings && result.warnings.length > 0 && (
          <Descriptions.Item label={t('approval.warnings')}>
            <Space>
              {result.warnings.map((w, i) => (
                <Tag key={i} color="orange">{w}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
        )}
      </Descriptions>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <ExclamationCircleOutlined />
            {t('approval.title')}
          </h2>
          <p className="text-gray-500">{t('approval.subtitle')}</p>
        </div>
        <Space>
          <Button icon={<SyncOutlined />} onClick={loadApprovals}>
            {t('approval.refresh')}
          </Button>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('approval.pending')}
              value={approvals.filter(a => a.status === 'pending').length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('approval.highRisk')}
              value={approvals.filter(a => a.risk_level === 'high' || a.risk_level === 'critical').length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('approval.sellActions')}
              value={approvals.filter(a => a.details?.analysis_result?.action === 'SELL').length}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Alert for pending approvals */}
      {approvals.filter(a => a.status === 'pending').length > 0 && (
        <Alert
          message={t('approval.pendingAlert')}
          description={t('approval.pendingAlertDesc')}
          type="warning"
          showIcon
        />
      )}

      {/* Approvals Table */}
      <Card>
        {approvals.length === 0 ? (
          <Empty description={t('approval.noPending')} />
        ) : (
          <Table
            columns={columns}
            dataSource={approvals}
            rowKey="id"
            expandable={{
              expandedRowRender,
              expandRowByClick: true,
            }}
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* Detail Modal */}
      <Modal
        title={t('approval.detailTitle')}
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setSelectedApproval(null);
          setComments('');
        }}
        footer={null}
        width={700}
      >
        {selectedApproval && (
          <div className="space-y-4">
            {/* Header Info */}
            <Descriptions bordered column={2}>
              <Descriptions.Item label={t('approval.ticker')}>
                <Tag color="cyan">{selectedApproval.details?.ticker || '-'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('approval.riskLevel')}>
                {getRiskTag(selectedApproval.risk_level)}
              </Descriptions.Item>
              <Descriptions.Item label={t('approval.requestType')}>
                {selectedApproval.request_type}
              </Descriptions.Item>
              <Descriptions.Item label={t('approval.createdAt')}>
                {new Date(selectedApproval.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            {/* Analysis Result */}
            {selectedApproval.details?.analysis_result && (
              <>
                <h4>{t('approval.analysisResult')}</h4>
                <Descriptions bordered column={2}>
                  <Descriptions.Item label={t('approval.action')}>
                    {getActionTag(selectedApproval.details.analysis_result.action)}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.upside')}>
                    <span style={{ 
                      color: (selectedApproval.details.analysis_result.upside_percent || 0) > 0 ? '#52c41a' : '#ff4d4f',
                      fontWeight: 'bold'
                    }}>
                      {(selectedApproval.details.analysis_result.upside_percent || 0).toFixed(1)}%
                    </span>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.fairValue')}>
                    ${selectedApproval.details.analysis_result.fair_value?.toFixed(2) || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.currentPrice')}>
                    ${selectedApproval.details.analysis_result.current_price?.toFixed(2) || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.confidence')}>
                    {selectedApproval.details.analysis_result.confidence}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.industry')}>
                    {selectedApproval.details.analysis_result.industry || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('approval.reasoning')} span={2}>
                    {selectedApproval.details.analysis_result.reasoning || '-'}
                  </Descriptions.Item>
                  {selectedApproval.details.analysis_result.warnings && (
                    <Descriptions.Item label={t('approval.warnings')} span={2}>
                      <Space>
                        {selectedApproval.details.analysis_result.warnings.map((w, i) => (
                          <Tag key={i} color="orange">{w}</Tag>
                        ))}
                      </Space>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </>
            )}

            <Divider />

            {/* Comments */}
            <div>
              <label>{t('approval.comments')}</label>
              <TextArea
                rows={3}
                value={comments}
                onChange={e => setComments(e.target.value)}
                placeholder={t('approval.commentsPlaceholder')}
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => {
                  setDetailVisible(false);
                  setComments('');
                }}
              >
                {t('approval.cancel')}
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleReject(selectedApproval)}
                loading={actionLoading}
              >
                {t('approval.reject')}
              </Button>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApprove(selectedApproval)}
                loading={actionLoading}
              >
                {t('approval.approve')}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
