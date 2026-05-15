import React, { useState } from 'react';
import { Typography, Card, Select, Input, Button, Result, message } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { expertApi } from '../lib/api';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const FORM_TYPES = [
  { value: 'inspection', label: '日常检查表' },
  { value: 'rectification', label: '整改通知书' },
  { value: 'acceptance', label: '验收报告' },
  { value: 'accident', label: '事故报告' },
];

export default function FormGenerator() {
  const [formType, setFormType] = useState('');
  const [context, setContext] = useState('');
  const [generated, setGenerated] = useState('');

  const genMutation = useMutation({
    mutationFn: () => expertApi.generateForm(formType, context),
    onSuccess: (res) => {
      setGenerated(res.data.content || res.data.form_content || '');
      message.success('表格生成成功');
    },
    onError: () => message.error('生成失败，请重试'),
  });

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={4}>表格智慧生成</Title>
      <Card>
        <Paragraph type="secondary">
          选择表格类型并描述场景，AI 自动生成规范表格内容。
        </Paragraph>

        <Select
          placeholder="选择表格类型"
          value={formType}
          onChange={setFormType}
          options={FORM_TYPES}
          style={{ width: '100%', marginBottom: 12 }}
        />

        <TextArea
          rows={4}
          placeholder="描述场景，例如：水库大坝工地，2号施工段，基坑开挖作业"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          style={{ marginBottom: 12 }}
        />

        <Button
          type="primary"
          loading={genMutation.isPending}
          onClick={() => genMutation.mutate()}
          disabled={!formType || !context}
        >
          生成表格
        </Button>

        {generated && (
          <Card title="生成结果" style={{ marginTop: 16 }}>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
              {generated}
            </pre>
            <Button type="link" onClick={() => navigator.clipboard.writeText(generated)}>
              复制内容
            </Button>
          </Card>
        )}
      </Card>
    </div>
  );
}
