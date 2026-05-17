import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Descriptions, Tag, Button, Timeline, Spin, Typography,
  Modal, Input, Form, message, Space, Divider, Select,
} from 'antd';
import {
  ArrowLeftOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  ClockCircleOutlined, TeamOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import { alertsApi } from '../lib/api';

const { Title, Paragraph, Text } = Typography;

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  open: { label: '待处理', color: 'error' },
  processing: { label: '处理中', color: 'processing' },
  resolved: { label: '已解决', color: 'success' },
  closed: { label: '已关闭', color: 'default' },
};

export default function AlertDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [assignOpen, setAssignOpen] = useState(false);
  const [resolveOpen, setResolveOpen] = useState(false);
  const [assignForm] = Form.useForm();
  const [resolveForm] = Form.useForm();

  const { data: alert, isLoading } = useQuery({
    queryKey: ['alert', id],
    queryFn: () => alertsApi.get(id!),
    select: (res) => res.data,
    enabled: !!id,
  });

  const assignMutation = useMutation({
    mutationFn: (userId: string) => alertsApi.assign(id!, userId),
    onSuccess: () => {
      message.success('派发成功');
      setAssignOpen(false);
      assignForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['alert', id] });
    },
    onError: () => message.error('派发失败'),
  });

  const resolveMutation = useMutation({
    mutationFn: (resolution: string) => alertsApi.resolve(id!, resolution),
    onSuccess: () => {
      message.success('已标记为已解决');
      setResolveOpen(false);
      queryClient.invalidateQueries({ queryKey: ['alert', id] });
    },
    onError: () => message.error('操作失败'),
  });

  const closeMutation = useMutation({
    mutationFn: () => alertsApi.close(id!),
    onSuccess: () => {
      message.success('告警已关闭');
      queryClient.invalidateQueries({ queryKey: ['alert', id] });
    },
    onError: () => message.error('关闭失败'),
  });

  if (isLoading) return <Spin style={{ margin: 100 }} />;

  const statusInfo = STATUS_MAP[alert?.status] || STATUS_MAP.open;

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/')}
        style={{ marginBottom: 16 }}
      >
        返回列表
      </Button>

      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>{alert?.title || '告警详情'}</Title>
          </Space>
        }
        extra={
          <Tag color={statusInfo.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            {statusInfo.label}
          </Tag>
        }
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="告警编号">
            <Text code>{alert?.alert_code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="级别">
            <Tag color={alert?.alert_level === 'P0' ? 'red' : alert?.alert_level === 'P1' ? 'orange' : 'blue'}>
              {alert?.alert_level}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="类型">{alert?.alert_type || '-'}</Descriptions.Item>
          <Descriptions.Item label="位置">{alert?.location_name || '未知'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {alert?.created_at ? new Date(alert.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {alert?.updated_at ? new Date(alert.updated_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="负责人">{alert?.assignee_name || '未分配'}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {alert?.description || '无详细描述'}
          </Descriptions.Item>
        </Descriptions>

        {alert?.status !== 'closed' && (
          <>
            <Divider>快速操作</Divider>
            <Space wrap>
              <Button
                type="primary"
                icon={<TeamOutlined />}
                onClick={() => setAssignOpen(true)}
              >
                派发负责人
              </Button>
              <Button
                icon={<CheckCircleOutlined />}
                onClick={() => setResolveOpen(true)}
              >
                标记已解决
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => closeMutation.mutate()}
                loading={closeMutation.isPending}
              >
                关闭告警
              </Button>
            </Space>
          </>
        )}
      </Card>

      <Card title="处理记录" style={{ marginTop: 16 }}>
        <Timeline
          items={[
            {
              color: 'blue',
              children: (
                <Space>
                  <ExclamationCircleOutlined style={{ color: '#1890ff' }} />
                  <Text>告警已创建</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {alert?.created_at ? new Date(alert.created_at).toLocaleString('zh-CN') : ''}
                  </Text>
                </Space>
              ),
            },
            ...(alert?.actions || []).map((a: any, idx: number) => ({
              children: (
                <Space key={idx}>
                  <ClockCircleOutlined style={{ color: '#fa8c16' }} />
                  <Text>{a.action_type}: {a.description}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(a.created_at).toLocaleString('zh-CN')}
                  </Text>
                </Space>
              ),
            })),
          ]}
        />
        {(!alert?.actions || alert.actions.length === 0) && (
          <Paragraph type="secondary">暂无处理记录</Paragraph>
        )}
      </Card>

      {/* 派发负责人弹窗 */}
      <Modal
        title="派发负责人"
        open={assignOpen}
        onOk={() => assignForm.submit()}
        onCancel={() => setAssignOpen(false)}
        confirmLoading={assignMutation.isPending}
        okText="确认派发"
        cancelText="取消"
      >
        <Form
          form={assignForm}
          layout="vertical"
          onFinish={(values) => assignMutation.mutate(values.userId)}
        >
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
        </Form>
        <Paragraph type="secondary" style={{ fontSize: 12 }}>
          选择负责处理此告警的人员，派发后告警状态将变为「处理中」。
        </Paragraph>
      </Modal>

      {/* 标记已解决弹窗 */}
      <Modal
        title="标记已解决"
        open={resolveOpen}
        onOk={() => resolveForm.submit()}
        onCancel={() => setResolveOpen(false)}
        confirmLoading={resolveMutation.isPending}
        okText="确认"
        cancelText="取消"
      >
        <Form
          form={resolveForm}
          layout="vertical"
          onFinish={(values) => resolveMutation.mutate(values.resolution)}
        >
          <Form.Item
            name="resolution"
            label="处理说明"
            rules={[{ required: true, message: '请填写处理说明' }]}
          >
            <Input.TextArea rows={4} placeholder="请描述处理结果和解决方案" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
