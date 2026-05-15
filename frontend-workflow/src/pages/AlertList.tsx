import React, { useState } from 'react';
import { Table, Tag, Button, Input, Select, Space, Typography, Card } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { alertsApi } from '../lib/api';

const { Title } = Typography;
const { Search } = Input;

const LEVEL_COLORS: Record<string, string> = {
  P0: 'red',
  P1: 'orange',
  P2: 'blue',
};

const STATUS_COLORS: Record<string, string> = {
  open: 'red',
  processing: 'orange',
  resolved: 'green',
  closed: 'gray',
};

export default function AlertList() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [level, setLevel] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [keyword, setKeyword] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', page, level, status, keyword],
    queryFn: () => alertsApi.list({ page, level, status, keyword, page_size: 20 }),
    select: (res) => res.data,
  });

  const columns = [
    {
      title: '告警编号',
      dataIndex: 'alert_code',
      width: 160,
      render: (code: string) => <code style={{ fontSize: 12 }}>{code}</code>,
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
        <Tag color={LEVEL_COLORS[level]}>{level}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status]}>
          {status === 'open' ? '待处理' :
           status === 'processing' ? '处理中' :
           status === 'resolved' ? '已解决' : '已关闭'}
        </Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'alert_type',
      width: 120,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => new Date(t).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      width: 100,
      render: (_: any, record: any) => (
        <Button type="link" size="small" onClick={() => navigate(`/alert/${record.id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>问题闭环管理</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Search placeholder="搜索告警" onSearch={setKeyword} style={{ width: 200 }} />
          <Select placeholder="级别" allowClear style={{ width: 100 }} onChange={setLevel}>
            <Select.Option value="P0">P0</Select.Option>
            <Select.Option value="P1">P1</Select.Option>
            <Select.Option value="P2">P2</Select.Option>
          </Select>
          <Select placeholder="状态" allowClear style={{ width: 120 }} onChange={setStatus}>
            <Select.Option value="open">待处理</Select.Option>
            <Select.Option value="processing">处理中</Select.Option>
            <Select.Option value="resolved">已解决</Select.Option>
            <Select.Option value="closed">已关闭</Select.Option>
          </Select>
        </Space>
      </Card>
      <Table
        columns={columns}
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total,
          onChange: setPage,
        }}
      />
    </div>
  );
}
