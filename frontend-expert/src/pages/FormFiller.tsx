import React, { useState } from 'react';
import {
  Typography, Card, Select, Input, Button, Form, Steps, Result, message,
  Divider, Tag, Space, Alert, Modal,
} from 'antd';
import { useMutation, useQuery } from '@tanstack/react-query';
import { SendOutlined, SaveOutlined, ClearOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { expertApi } from '../lib/api';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const FORM_TYPES = [
  { value: 'inspection', label: '日常检查表' },
  { value: 'rectification', label: '整改通知书' },
  { value: 'acceptance', label: '验收报告' },
  { value: 'accident', label: '事故报告' },
];

// 模拟表单字段配置
const FIELD_TEMPLATES: Record<string, Array<{ name: string; label: string; type: string; required: boolean; placeholder?: string }>> = {
  inspection: [
    { name: 'site_name', label: '工地名称', type: 'input', required: true, placeholder: '请输入工地名称' },
    { name: 'check_date', label: '检查日期', type: 'date', required: true },
    { name: 'inspector', label: '检查人', type: 'input', required: true, placeholder: '请输入检查人姓名' },
    { name: 'check_items', label: '检查项目', type: 'textarea', required: true, placeholder: '请列出检查的具体项目' },
    { name: 'findings', label: '发现问题', type: 'textarea', required: false, placeholder: '描述发现的问题（无则填"无"）' },
    { name: 'safety_level', label: '安全等级', type: 'select', required: true },
  ],
  rectification: [
    { name: 'unit_name', label: '单位名称', type: 'input', required: true, placeholder: '被整改单位名称' },
    { name: 'issue_desc', label: '问题描述', type: 'textarea', required: true },
    { name: 'deadline', label: '整改期限', type: 'date', required: true },
    { name: 'rectifier', label: '整改负责人', type: 'input', required: true },
  ],
  acceptance: [
    { name: 'project_name', label: '项目名称', type: 'input', required: true },
    { name: 'acceptance_date', label: '验收日期', type: 'date', required: true },
    { name: 'result', label: '验收结果', type: 'select', required: true },
    { name: 'notes', label: '备注', type: 'textarea', required: false },
  ],
  accident: [
    { name: 'accident_date', label: '事故时间', type: 'date', required: true },
    { name: 'accident_location', label: '事故地点', type: 'input', required: true },
    { name: 'accident_type', label: '事故类型', type: 'select', required: true },
    { name: 'casualties', label: '伤亡情况', type: 'input', required: false },
    { name: 'description', label: '事故描述', type: 'textarea', required: true },
  ],
};

export default function FormFiller() {
  const [formType, setFormType] = useState('');
  const [partialData, setPartialData] = useState('');
  const [description, setDescription] = useState('');
  const [filledResult, setFilledResult] = useState<Record<string, any> | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  const fillMutation = useMutation({
    mutationFn: () => expertApi.fillForm(formType, {}, description),
    onSuccess: (res) => {
      const data = res.data.filled_data || {};
      setFilledResult(data);
      form.setFieldsValue(data);
      setCurrentStep(2);
      message.success('智慧补全成功，已填充以下字段');
    },
    onError: () => {
      message.error('智慧填报服务暂时不可用，请稍后重试');
    },
  });

  const handleTypeChange = (value: string) => {
    setFormType(value);
    setFilledResult(null);
    form.resetFields();
    setCurrentStep(0);
  };

  const handleAIFill = () => {
    if (!formType) {
      message.warning('请先选择表单类型');
      return;
    }
    if (!description.trim()) {
      message.warning('请提供业务描述信息');
      return;
    }
    fillMutation.mutate();
  };

  const handleManualFill = () => {
    setCurrentStep(1);
    const values = form.getFieldsValue();
    if (Object.keys(values).length > 0 && values.constructor === Object) {
      message.info('已进入手动填写模式，请完善表单字段');
    }
  };

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      message.success('表单提交成功！');
      console.log('Submitted:', values);
    }).catch(() => {
      message.error('请检查必填字段');
    });
  };

  const handleReset = () => {
    form.resetFields();
    setFilledResult(null);
    setPartialData('');
    setDescription('');
    setCurrentStep(0);
  };

  const currentFields = FIELD_TEMPLATES[formType] || [];

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <Title level={4}>📝 表格智慧填报</Title>

      <Card style={{ marginBottom: 16 }}>
        <Paragraph type="secondary">
          输入已有的字段信息或描述业务场景，AI 将辅助补全表格剩余字段，确保数据规范完整。
        </Paragraph>

        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>表单类型</Text>
            <Select
              placeholder="请选择要填写的表单类型"
              value={formType}
              onChange={handleTypeChange}
              options={FORM_TYPES}
              style={{ width: '100%' }}
              size="large"
            />
          </div>

          {formType && (
            <>
              <Divider orientation="left">AI 智能补全（可选）</Divider>
              <Alert
                message="使用 AI 辅助填写"
                description="在下方描述业务场景或输入已知字段信息，AI 将自动补全其他字段。"
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
              />
              <TextArea
                rows={3}
                placeholder={'输入已知信息或描述场景，例如：\n工地：水库大坝工程\n检查日期：2026年5月14日\n检查人：张三\n主要检查内容：基坑开挖、高处作业'}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                showCount
                maxLength={800}
              />
              <Button
                type="primary"
                loading={fillMutation.isPending}
                onClick={handleAIFill}
                icon={<SendOutlined />}
              >
                {fillMutation.isPending ? 'AI 补全中…' : 'AI 智慧补全'}
              </Button>

              <Divider orientation="left">或手动填写</Divider>
              <Button onClick={handleManualFill} icon={<EditOutlined />} type="default">
                进入手动填写模式
              </Button>
            </>
          )}
        </Space>
      </Card>

      {formType && currentFields.length > 0 && (
        <Card title="表单填写" style={{ marginBottom: 16 }}>
          <Form form={form} layout="vertical" size="large">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' }}>
              {currentFields.map((field) => (
                <Form.Item
                  key={field.name}
                  name={field.name}
                  label={field.label}
                  rules={field.required ? [{ required: true, message: `请输入${field.label}` }] : []}
                  style={field.type === 'textarea' ? { gridColumn: '1 / -1' } : {}}
                >
                  {field.type === 'input' && <Input placeholder={field.placeholder} />}
                  {field.type === 'date' && <Input type="date" />}
                  {field.type === 'textarea' && <TextArea rows={3} placeholder={field.placeholder} />}
                  {field.type === 'select' && (
                    <Select placeholder={`请选择${field.label}`}>
                      <Select.Option value="pass">合格</Select.Option>
                      <Select.Option value="fail">不合格</Select.Option>
                      <Select.Option value="pending">待整改</Select.Option>
                    </Select>
                  )}
                </Form.Item>
              ))}
            </div>

            <Form.Item style={{ marginTop: 16 }}>
              <Space>
                <Button type="primary" onClick={handleSubmit} icon={<SaveOutlined />}>
                  提交表单
                </Button>
                <Button onClick={handleReset} icon={<ClearOutlined />}>
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      )}

      {filledResult && Object.keys(filledResult).length > 0 && (
        <Card title="AI 补全结果" style={{ marginBottom: 16 }}>
          <Space wrap style={{ marginBottom: 12 }}>
            {Object.entries(filledResult).map(([key, value]) => (
              <Tag key={key} color="blue">
                {key}: {String(value)}
              </Tag>
            ))}
          </Space>
          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            以上字段由 AI 根据您的描述自动填充，您可以在上方表单中修改后再提交。
          </Paragraph>
        </Card>
      )}
    </div>
  );
}

// 辅助函数（非导出）
function EditOutlined() {
  return <span style={{ fontStyle: 'italic' }}>✏️</span>;
}
