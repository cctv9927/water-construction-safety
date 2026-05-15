import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, Descriptions, Tag, Button, Timeline, Spin, Typography } from 'antd';
import { ArrowLeft } from '@ant-design/icons';
import { alertsApi } from '../lib/api';

const { Title } = Typography;

export default function AlertDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: alert, isLoading } = useQuery({
    queryKey: ['alert', id],
    queryFn: () => alertsApi.get(id!),
    select: (res) => res.data,
  });

  if (isLoading) return <Spin style={{ margin: 100 }} />;

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeft />} onClick={() => navigate('/')} style={{ marginBottom: 16 }}>
        返回列表
      </Button>

      <Card title={<Title level={4}>{alert?.title}</Title>}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="告警编号">{alert?.alert_code}</Descriptions.Item>
          <Descriptions.Item label="级别">
            <Tag color={alert?.alert_level === 'P0' ? 'red' : alert?.alert_level === 'P1' ? 'orange' : 'blue'}>
              {alert?.alert_level}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {alert?.status === 'open' ? '待处理' :
             alert?.status === 'processing' ? '处理中' :
             alert?.status === 'resolved' ? '已解决' : '已关闭'}
          </Descriptions.Item>
          <Descriptions.Item label="类型">{alert?.alert_type}</Descriptions.Item>
          <Descriptions.Item label="位置">{alert?.location_name || '未知'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(alert?.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{alert?.description}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="处理记录" style={{ marginTop: 16 }}>
        <Timeline
          items={[
            { children: '告警已创建' },
            ...(alert?.actions || []).map((a: any) => ({
              children: `${a.action_type}: ${a.description} - ${new Date(a.created_at).toLocaleString('zh-CN')}`,
            })),
          ]}
        />
      </Card>
    </div>
  );
}
