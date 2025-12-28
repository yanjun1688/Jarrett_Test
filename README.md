# Test Manager Pro

一个功能强大的测试管理平台，支持 API 测试、测试用例管理、AI 测试用例生成等功能。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2.6-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特性

- 🔧 **API 测试管理** - 支持 RESTful API 测试，包括请求构建、断言配置、批量执行
- 📝 **测试用例管理** - 完整的测试用例生命周期管理，支持项目、模块组织
- 🤖 **AI 测试用例生成** - 基于 PRD 文档自动生成测试用例（支持 PDF、Word、TXT）
- 📊 **测试执行和报告** - 支持多种执行策略（并发、顺序、链式），生成详细测试报告
- 🔗 **请求集合管理** - 支持 YAML 格式的测试脚本，批量管理 API 请求
- 👥 **权限管理** - 基于角色的权限控制（RBAC）
- 📈 **数据统计** - 项目测试数据统计和可视化

## 🛠️ 技术栈

### 后端
- **Django 5.2.6** - Web 框架
- **Django REST Framework** - RESTful API
- **MySQL** - 数据库
- **Redis** - 缓存和会话存储
- **LangChain** - AI 功能支持
- **pytest** - 测试框架

### 前端
- **React 18** - UI 框架
- **Ant Design** - UI 组件库
- **Axios** - HTTP 客户端
- **React Router** - 路由管理

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+
- MySQL 5.7+ 或 PostgreSQL 10+
- Redis 6.0+

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/test-hyanjun-pro.git
cd test-hyanjun-pro
```

#### 2. 后端设置

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置（数据库、Redis、SECRET_KEY等）

# 运行数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

后端服务将在 `http://localhost:8000` 启动

#### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端应用将在 `http://localhost:3000` 启动

### 环境变量配置

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=testmanager
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# OpenAI (Optional, for AI features)
OPENAI_API_KEY=your-openai-api-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

**重要**: 请确保 `SECRET_KEY` 使用强随机字符串，不要使用默认值！

## 📖 文档

- [架构分析](./ARCHITECTURE_ANALYSIS.md) - 项目架构和数据结构说明
- [业务逻辑诊断](./BUSINESS_LOGIC_DIAGNOSIS.md) - 业务逻辑分析和优化建议
- [安全审计报告](./SECURITY_AUDIT_REPORT.md) - 安全审计和修复记录
- [前端设置指南](./frontend/SETUP_GUIDE.md) - 前端开发配置说明
- [开源准备度评估](./OPEN_SOURCE_READINESS_REPORT.md) - 项目开源准备情况

## 🎯 主要功能说明

### API 测试

- 支持 GET、POST、PUT、DELETE 等 HTTP 方法
- 支持请求头、请求体配置
- 支持变量替换和模板渲染
- 支持多种断言类型（状态码、响应体、响应头等）
- 支持批量执行和并发执行

### AI 测试用例生成

1. 上传 PRD 文档（支持 PDF、Word、TXT 格式）
2. 配置 OpenAI API Key
3. AI 自动分析文档并生成测试用例
4. 选择需要的测试用例保存到功能测试模块

### 测试执行策略

- **并发执行** - 同时执行多个请求，提高效率
- **顺序执行** - 按顺序执行请求，支持变量传递
- **链式执行** - 请求之间可以传递变量，形成执行链

### 请求集合

支持 YAML 格式的测试脚本：

```yaml
name: 用户登录流程
description: 测试用户登录功能

variables:
  username: test_user
  password: "123456"

test_steps:
  - name: 用户登录
    request:
      method: POST
      url: https://api.example.com/login
      json:
        username: "{{username}}"
        password: "{{password}}"
    extract:
      - name: token
        jsonpath: "$.data.token"
    assertions:
      - type: status_code
        expected: 200
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=testmanager_app --cov-report=html

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

## 📁 项目结构

```
Test_Hyanjun_Pro/
├── frontend/                 # React 前端应用
│   ├── src/
│   │   ├── api/              # API 调用封装
│   │   ├── components/       # React 组件
│   │   ├── context/          # React Context
│   │   └── hooks/            # 自定义 Hooks
│   └── package.json
├── testmanager/             # Django 项目配置
│   ├── settings.py           # 项目设置
│   └── urls.py               # 根 URL 配置
├── testmanager_app/         # 核心业务应用
│   ├── models.py            # 数据模型
│   ├── views.py             # API 视图
│   ├── serializers.py       # 序列化器
│   ├── services/            # 业务逻辑服务
│   └── utils/               # 工具函数
├── test_ai_agent/           # AI 测试用例生成模块
│   ├── ai_processor.py      # AI 处理逻辑
│   └── document_loader.py  # 文档加载器
└── requirements.txt         # Python 依赖
```

## 🔒 安全注意事项

1. **SECRET_KEY**: 必须使用环境变量配置，不要使用默认值
2. **数据库密码**: 使用强密码，不要硬编码
3. **API Key**: AI 功能的 API Key 建议通过后端代理，不要在前端存储
4. **DEBUG 模式**: 生产环境必须设置 `DEBUG=False`

更多安全建议请参考 [安全审计报告](./SECURITY_AUDIT_REPORT.md)

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发计划

- [ ] 完善 AI 测试用例生成功能
- [ ] 添加更多测试报告模板
- [ ] 支持更多数据库（PostgreSQL、MongoDB）
- [ ] 添加 Docker 支持
- [ ] 完善 API 文档
- [ ] 添加 CI/CD 支持

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

感谢所有贡献者的支持！

## 📧 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

**注意**: 本项目处于 MVP 阶段，部分功能可能仍在开发中。欢迎反馈和建议！

