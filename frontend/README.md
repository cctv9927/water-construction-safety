# 水利建设工地质量安全监管系统 - 前端 Monorepo

## 架构说明

本项目采用 **Monorepo** 结构，将原来的三个独立前端项目合并为统一的工作空间：

```
frontend/
├── apps/                      # 应用目录
│   ├── sandbox/              # 电子沙盘 (port 3000)
│   ├── workflow/             # 告警闭环管理 (port 3001)
│   └── expert/               # 专家系统 (port 3002)
├── packages/                  # 共享包
│   ├── ui/                   # UI 组件库
│   ├── api-client/           # API 客户端
│   └── utils/                # 工具函数
├── package.json              # 根配置（workspace 定义）
└── turbo.json                # Turborepo 配置
```

## 优势

| 优势 | 说明 |
|------|------|
| **代码复用** | 共享组件和工具函数只需维护一份 |
| **一致性** | UI 风格、API 调用方式全局统一 |
| **独立开发** | 各应用可独立运行、独立部署 |
| **依赖优化** | 公共依赖只安装一次 |

## 技术栈

- **构建工具**: Turborepo
- **UI 框架**: React 18 + Ant Design 5
- **3D 可视化**: CesiumJS (sandbox 专用)
- **包管理**: npm workspaces

## 快速开始

### 前置条件

```bash
node >= 18.0.0
npm >= 9.0.0
```

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
# 启动所有应用
npm run dev

# 或启动单个应用
npm run dev --filter=@water-safety/app-sandbox
```

### 构建

```bash
npm run build
```

## 添加共享组件

在 `packages/ui/src/components/` 中添加组件，例如：

```typescript
// packages/ui/src/components/MyComponent.tsx
import React from 'react';

export const MyComponent: React.FC = () => {
  return <div>共享组件</div>;
};
```

然后在 `packages/ui/src/index.ts` 中导出：

```typescript
export { MyComponent } from './components/MyComponent';
```

## 添加 API

在 `packages/api-client/src/index.ts` 中添加 API 方法：

```typescript
export const myApi = {
  list: (params?: any) => api.get('/my-resource', params),
  create: (data: any) => api.post('/my-resource', data),
};
```

## 应用中使用

```typescript
import { AlertCard, StatusBadge } from '@water-safety/ui';
import { alertApi, sensorApi } from '@water-safety/api-client';

// 使用共享组件
<AlertCard level="P1" message="告警信息" />

// 使用 API
const alerts = await alertApi.list();
```

## 部署

各应用可独立部署，或通过 Nginx 统一路由：

```nginx
location /sandbox {
  proxy_pass http://localhost:3000;
}
location /workflow {
  proxy_pass http://localhost:3001;
}
location /expert {
  proxy_pass http://localhost:3002;
}
```

## 迁移指南

从原来的独立项目迁移：

1. **复制代码**：
   ```bash
   # 原 frontend-sandbox/src → apps/sandbox/src
   cp -r ../frontend-sandbox/src apps/sandbox/
   ```

2. **更新导入**：
   ```typescript
   // 之前
   import { Button } from 'antd';
   
   // 之后
   import { StatusBadge } from '@water-safety/ui';
   ```

3. **安装共享包依赖**：
   ```bash
   npm install @water-safety/ui @water-safety/api-client
   ```
