import React from 'react';
import { Typography, Card, Steps, Button, Select, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { alertsApi } from '../lib/api';

const { Title } = Typography;

const STEPS = ['待处理', '处理中', '已解决', '已关闭'];

export default function Workflow() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>告警处理工作流</Title>
      <Card>
        <Steps
          current={0}
          items={STEPS.map((s) => ({ title: s }))}
        />
      </Card>
      <Card title="批量处理" style={{ marginTop: 16 }}>
        <p>选择要处理的告警级别：</p>
        <Select placeholder="选择级别" style={{ width: 200, marginRight: 8 }}>
          <Select.Option value="P0">P0</Select.Option>
          <Select.Option value="P1">P1</Select.Option>
          <Select.Option value="P2">P2</Select.Option>
        </Select>
        <Button type="primary" style={{ marginTop: 8 }}>
          批量派发
        </Button>
      </Card>
    </div>
  );
}
