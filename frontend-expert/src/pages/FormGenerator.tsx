import React, { useState } from 'react';
import { Typography, Card, Select, Input, Button, Result, message, Collapse, Tag, Space } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { CopyOutlined, CheckOutlined, EditOutlined, ReloadOutlined } from '@ant-design/icons';
import { expertApi } from '../lib/api';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

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
  const [isCopied, setIsCopied] = useState(false);
  const [history, setHistory] = useState<Array<{ type: string; content: string; time: string }>>([]);

  const genMutation = useMutation({
    mutationFn: () => expertApi.generateForm(formType, context),
    onSuccess: (res) => {
      const content = res.data.content || res.data.form_content || '';
      setGenerated(content);
      setHistory((prev) => [
        { type: formType, content, time: new Date().toLocaleTimeString('zh-CN') },
        ...prev.slice(0, 4),
      ]);
      message.success('表格生成成功');
    },
    onError: () => message.error('生成失败，请重试'),
  });

  const handleGenerate = () => {
    if (!formType || !context.trim()) {
      message.warning('请填写表单类型和场景描述');
      return;
    }
    genMutation.mutate();
  };

  const handleCopy = () => {
    if (!generated) return;
    navigator.clipboard.writeText(generated).then(() => {
      setIsCopied(true);
      message.success('已复制到剪贴板');
      setTimeout(() => setIsCopied(false), 2000);
    });
  };

  const handleClear = () => {
    setGenerated('');
    setIsCopied(false);
  };

  const handleLoadHistory = (content: string) => {
    setGenerated(content);
  };

  const getTypeLabel = (value: string) => {
    return FORM_TYPES.find((t) => t.value === value)?.label || value;
  };

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <Title level={4}>📋 表格智慧生成</Title>

      <Card style={{ marginBottom: 16 }}>
        <Paragraph type="secondary">
          选择表格类型并描述业务场景，AI 将自动生成符合规范的表格内容。生成的表格可直接复制使用。
        </Paragraph>

        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>表单类型</Text>
            <Select
              placeholder="请选择要生成的表单类型"
              value={formType}
              onChange={setFormType}
              options={FORM_TYPES}
              style={{ width: '100%' }}
              size="large"
            />
          </div>

          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>场景描述</Text>
            <TextArea
              rows={4}
              placeholder="请详细描述使用场景，包括：工地名称、施工段号、作业类型、特殊要求等。例如：水库大坝工程，2号施工段，基坑开挖作业，涉及深基坑和高处作业，需包含安全检查要点。"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              showCount
              maxLength={500}
            />
          </div>

          <Space>
            <Button
              type="primary"
              loading={genMutation.isPending}
              onClick={handleGenerate}
              disabled={!formType || !context.trim()}
              icon={<EditOutlined />}
              size="large"
            >
              {genMutation.isPending ? '生成中…' : '生成表格'}
            </Button>
            {generated && (
              <Button onClick={handleClear} icon={<ReloadOutlined />}>
                重新生成
              </Button>
            )}
          </Space>
        </Space>
      </Card>

      {generated && (
        <Card
          title={
            <Space>
              <span>生成结果</span>
              <Tag color="blue">{getTypeLabel(formType)}</Tag>
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={isCopied ? <CheckOutlined /> : <CopyOutlined />}
                onClick={handleCopy}
                type={isCopied ? 'default' : 'primary'}
              >
                {isCopied ? '已复制' : '复制内容'}
              </Button>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 13,
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 6,
              border: '1px solid #e8e8e8',
              maxHeight: 500,
              overflow: 'auto',
              lineHeight: 1.8,
            }}
          >
            {generated}
          </pre>
          <Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
            提示：如需调整表格内容，可复制后在编辑器中修改，或重新描述场景后再次生成。
          </Paragraph>
        </Card>
      )}

      {history.length > 0 && (
        <Card title="历史生成记录" size="small">
          <Collapse accordion>
            {history.map((item, idx) => (
              <Panel
                key={idx}
                header={
                  <Space>
                    <Tag>{getTypeLabel(item.type)}</Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>{item.time}</Text>
                  </Space>
                }
                extra={
                  <Button size="small" type="link" onClick={() => handleLoadHistory(item.content)}>
                    加载
                  </Button>
                }
              >
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{item.content}</pre>
              </Panel>
            ))}
          </Collapse>
        </Card>
      )}
    </div>
  );
}
