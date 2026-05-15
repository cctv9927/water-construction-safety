import React, { useState } from 'react';
import { Typography, Card, Select, Input, Button, Descriptions, message } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { expertApi } from '../lib/api';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const FORM_TYPES = [
  { value: 'inspection', label: '日常检查表' },
  { value: 'rectification', label: '整改通知书' },
];

export default function FormFiller() {
  const [formType, setFormType] = useState('');
  const [partialData, setPartialData] = useState('');
  const [description, setDescription] = useState('');

  const fillMutation = useMutation({
    mutationFn: () => expertApi.fillForm(formType, {}, description),
    onSuccess: (res) => {
      message.success('智慧填报完成');
      console.log('Filled form:', res.data);
    },
    onError: () => message.error('填报失败，请重试'),
  });

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={4}>表格智慧填报</Title>
      <Card>
        <Paragraph type="secondary">
          输入已有的字段信息，AI 辅助补全剩余字段。
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
          placeholder={'输入已知信息，例如：\n工地：水库大坝\n检查日期：2026-05-14\n检查人：张三\n检查项目：基坑'}
          value={partialData}
          onChange={(e) => setPartialData(e.target.value)}
          style={{ marginBottom: 12 }}
        />

        <TextArea
          rows={2}
          placeholder="补充描述（可选）"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{ marginBottom: 12 }}
        />

        <Button
          type="primary"
          loading={fillMutation.isPending}
          onClick={() => fillMutation.mutate()}
          disabled={!formType || !partialData}
        >
          智慧补全
        </Button>
      </Card>
    </div>
  );
}
