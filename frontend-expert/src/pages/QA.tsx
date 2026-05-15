import React, { useState } from 'react';
import { Typography, Card, Input, Button, List, Spin, Avatar, message } from 'antd';
import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { expertApi } from '../lib/api';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ title: string; snippet: string; score: number }>;
}

export default function QA() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  const queryMutation = useMutation({
    mutationFn: (q: string) => expertApi.query(q),
    onSuccess: (res) => {
      const answer = res.data.answer;
      const sources = res.data.sources || [];
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: answer,
          sources,
        },
      ]);
    },
    onError: () => message.error('问答服务暂时不可用'),
  });

  const handleSend = () => {
    if (!question.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: question },
    ]);
    queryMutation.mutate(question);
    setQuestion('');
  };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={4}>质量安全知识问答</Title>
      <Card style={{ marginBottom: 16 }}>
        <Paragraph type="secondary">
          基于知识库的智能问答，可咨询安全规范、问题处理方案、历史案例等。
        </Paragraph>
        <TextArea
          rows={3}
          placeholder="请输入您的问题，例如：基坑开挖有哪些安全要点？"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onPressEnter={(e) => !e.shiftKey && (e.preventDefault(), handleSend())}
        />
        <Button
          type="primary"
          onClick={handleSend}
          loading={queryMutation.isPending}
          style={{ marginTop: 8 }}
        >
          提问
        </Button>
      </Card>

      <List
        dataSource={messages}
        renderItem={(msg) => (
          <List.Item style={{ justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <Card
              size="small"
              style={{
                maxWidth: '75%',
                background: msg.role === 'user' ? '#1890ff' : '#f5f5f5',
                color: msg.role === 'user' ? '#fff' : '#000',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                {msg.role === 'assistant' ? (
                  <RobotOutlined style={{ marginTop: 4 }} />
                ) : (
                  <UserOutlined style={{ marginTop: 4 }} />
                )}
                <div>
                  <Paragraph style={{ margin: 0, color: 'inherit' }}>
                    {msg.content}
                  </Paragraph>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <small>参考来源：</small>
                      {msg.sources.map((s, i) => (
                        <div key={i} style={{ fontSize: 11, opacity: 0.7 }}>
                          • {s.title}（相似度 {Math.round(s.score * 100)}%）
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </List.Item>
        )}
      />
    </div>
  );
}
