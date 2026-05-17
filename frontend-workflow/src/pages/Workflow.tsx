import React, { useState } from 'react';
import {
  Typography, Card, Steps, Button, Select, Table, Tag, Space,
  Modal, Form, message, Badge, Tooltip, Statistic, Row, Col,
} from 'antd';
import {
  CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined,
  ExclamationCircleOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi, workflowApi } from '../lib/api';

const { Title, Paragraph, Text } = Typography;

const STATUS_MAP: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  open: { label: '待处理', color: 'error', icon: <ExclamationCircleOutlined /> },
  processing: { label: '处理中', color: 'processing', icon: <ClockCircleOutlined /> },
  resolved: { label: '已解决', color: 'success', icon: <CheckCircleOutlined /> },
  closed: { label: '已关闭', color: 'default', icon: <CloseCircleOutlined /> },
};

export default function Workflow() {
  const queryClient = useQueryClient();
  const [selectedLevel, setSelectedLevel] = useState<string>('');
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedAlertId, setSelectedAlertId] = useState<string>('');
  const [form] = Form.useForm();

  // 工作流统计
  const { data: workflows, isLoading: wfLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => workflowApi.list(),
    select: (res) => res.data,
  });

  // 告警统计（按状态）
  const { data: alertStats } = useQuery({
    queryKey: ['alert-stats'],
    queryFn: () => alertsApi.list({ page_size: 1 }),
    select: (res) => {
      const items = res.data?.items || [];
      return {
        total: res.data?.total || 0,
        open: items.filter((a: any) => a.status === 'open').length,
        processing: items.filter((a: any) => a.status === 'processing').length,
        resolved: items.filter((a: any) => a.status === 'resolved').length,
        closed: items.filter((a: any) => a.status === 'closed').length,
      };
    },
  });

  // 当前告警列表（筛选）
  const { data: alertList, isLoading: listLoading } = useQuery({
    queryKey: ['alerts-filtered', selectedLevel],
    queryFn: () => alertsApi.list({ alert_level: selectedLevel, page_size: 50 }),
    select: (res) => res.data?.items || [],
  });

  // 批量派发
  const assignMutation = useMutation({
    mutationFn: ({ alertId, userId }: { alertId: string; userId: string }) =>
      alertsApi.assign(alertId, userId),
    onSuccess: () => {
      message.success('派发成功');
      setAssignModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['alerts-filtered'] });
    },
    onError: () => message.error('派发失败，请重试'),
  });

  // 批量关闭
  const closeMutation = useMutation({
    mutationFn: (alertId: string) => alertsApi.close(alertId),
    onSuccess: () => {
      message.success('已关闭选中告警');
      queryClient.invalidateQueries({ queryKey: ['alerts-filtered'] });
    },
    onError: () => message.error('关闭失败'),
  });

  const handleAssign = (alertId: string) => {
    setSelectedAlertId(alertId);
    setAssignModalOpen(true);
  };

  const handleAssignSubmit = () => {
    form.validateFields().then((values) => {
      assignMutation.mutate({ alertId: selectedAlertId, userId: values.userId });
    });
  };

  const columns = [
    {
      title: '告警编号',
      dataIndex: 'alert_code',
      width: 160,
      render: (code: string) => <Text code style={{ fontSize: 12 }}>{code}</Text>,
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
    },
    {
      title: '级别',
      dataIndex: 'alert_level',
      width: 80,
      render: (level: string) => (
        <Tag color={level === 'P0' ? 'red' : level === 'P1' ? 'orange' : 'blue'}>{level}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: string) => {
        const info = STATUS_MAP[status] || STATUS_MAP.open;
        return <Tag color={info.color} icon={info.icon}>{info.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      width: 200,
      render: (_: any, record: any) => (
        <Space size="small">
          {record.status !== 'closed' && (
            <>
              <Button size="small" type="primary" onClick={() => handleAssign(record.id)}>
                派发
              </Button>
              <Button size="small" onClick={() => closeMutation.mutate(record.id)}>
                关闭
              </Button>
            </>
          )}
          <Button size="small" type="link" onClick={() => window.open(`/alert/${record.id}`, '_blank')}>
            详情
          </Button>
        </Space>
      ),
    },
  ];

  const workflowSteps = [
    { title: '待处理', description: '告警产生' },
    { title: '处理中', description: '专人负责' },
    { title: '已解决', description: '问题修复' },
    { title: '已关闭', description: '归档完成' },
  ];

  const currentStep = workflows?.current_step ?? 0;

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>⚙️ 告警处理工作流</Title>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="告警总数"
              value={alertStats?.total || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="待处理"
              value={alertStats?.open || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="处理中"
              value={alertStats?.processing || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已解决"
              value={alertStats?.resolved || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 工作流步骤 */}
      <Card title="工作流状态" style={{ marginBottom: 16 }}>
        <Steps current={currentStep} items={workflowSteps} />
      </Card>

      {/* 批量管理 */}
      <Card
        title="告警批量管理"
        extra={
          <Space>
            <Select
              placeholder="筛选级别"
              allowClear
              style={{ width: 140 }}
              onChange={setSelectedLevel}
            >
              <Select.Option value="P0">P0</Select.Option>
              <Select.Option value="P1">P1</Select.Option>
              <Select.Option value="P2">P2</Select.Option>
            </Select>
            <Tooltip title="刷新列表">
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['alerts-filtered'] })}
              />
            </Tooltip>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          选择告警级别进行筛选，点击「派发」将告警分配给指定负责人，点击「关闭」可结束告警处理流程。
        </Paragraph>
        <Table
          columns={columns}
          dataSource={alertList}
          rowKey="id"
          loading={listLoading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 工作流列表 */}
      <Card title="工作流实例" loading={wfLoading}>
        {workflows?.items?.length > 0 ? (
          <Table
            dataSource={workflows.items}
            rowKey="id"
            size="small"
            columns={[
              { title: '工作流ID', dataIndex: 'id', width: 200 },
              { title: '名称', dataIndex: 'name' },
              {
                title: '状态',
                dataIndex: 'status',
                render: (s: string) => <Badge status={s === 'active' ? 'processing' : 'default'} text={s} />,
              },
              {
                title: '当前步骤',
                dataIndex: 'current_step',
                render: (step: number) => workflowSteps[step]?.title || '-',
              },
            ]}
          />
        ) : (
          <Text type="secondary">暂无工作流数据</Text>
        )}
      </Card>

      {/* 派发弹窗 */}
      <Modal
        title="派发告警"
        open={assignModalOpen}
        onOk={handleAssignSubmit}
        onCancel={() => setAssignModalOpen(false)}
        confirmLoading={assignMutation.isPending}
        okText="确认派发"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="userId"
            label="选择负责人"
            rules={[{ required: true, message: '请选择负责人' }]}
          >
            <Select placeholder="请选择负责处理此告警的人员">
              <Select.Option value="user_001">👷 李工（安全主管）</Select.Option>
              <Select.Option value="user_002">👷 王工（施工经理）</Select.Option>
              <Select.Option value="user_003">👷 张工（技术负责人）</Select.Option>
            </Select>
          </Form.Item>
          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            派发后，该告警将从「待处理」变为「处理中」状态，负责人将收到通知。
          </Paragraph>
        </Form>
      </Modal>
    </div>
  );
}
