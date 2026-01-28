# JTest - 测试管理平台

JTest 是一个基于 Django + React 的测试管理平台，支持 API 测试、UI 自动化测试、测试用例管理等功能。

## 功能特性

- **API 测试**: 支持 RESTful API 的创建、执行和断言
- **UI 自动化测试**: 基于 Playwright 的浏览器自动化录制和执行
- **测试用例管理**: 项目化管理测试用例和测试集合
- **测试报告**: 自动生成测试执行报告
- **AI 辅助**: 集成 AI 能力辅助测试用例生成

## 技术栈

### 后端
- Python 3.10+
- Django 5.x
- Django REST Framework
- Celery (异步任务)
- Playwright (UI 自动化)
- Redis (缓存和消息队列)
- MySQL / SQLite

### 前端
- React 18
- Ant Design
- Axios

## 快速开始

### 环境准备

1. 克隆项目
```bash
git clone https://github.com/yanjun1688/Jarrett_Test.git
cd JTest
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填写数据库、Redis 等配置
```

3. 安装后端依赖
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. 安装 Playwright 浏览器
```bash
python manage.py install_playwright
```

5. 数据库迁移
```bash
python manage.py migrate
```

6. 创建管理员账户
```bash
python manage.py createsuperuser
```

7. 安装前端依赖
```bash
cd frontend
npm install
```

### 启动服务

**一键启动所有服务：**

```bash
# Windows
python start.py

# Linux/Mac
chmod +x start.sh
./start.sh
```

**可选参数：**
```bash
python start.py --backend     # 只启动后端
python start.py --frontend    # 只启动前端
python start.py --celery      # 只启动 Celery Worker
python start.py --env-only    # 只检查环境，不启动服务
```

**或者分别启动各服务：**

```bash
# 启动 Django 后端 (默认端口 8000)
python manage.py runserver

# 启动 Celery Worker (异步任务处理)
celery -A testmanager worker -l info -P solo

# 启动前端开发服务器 (默认端口 3000)
cd frontend && npm start
```

启动成功后访问：
- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

## 使用示例

### API 测试操作流程

1. **创建项目**: 进入"项目管理"，点击"新建项目"
2. **创建 API 请求**: 在项目详情中，添加 API 请求
   - 填写请求名称、URL、方法（GET/POST/PUT/DELETE）
   - 配置请求头、请求体
   - 添加断言规则（状态码、响应体包含等）
3. **执行测试**: 点击"执行"按钮运行单个请求，或创建集合批量执行
4. **查看报告**: 在"测试报告"中查看执行结果和历史记录

```
示例 API 请求配置：
{
  "name": "获取用户列表",
  "url": "https://api.example.com/users",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer {{token}}"
  },
  "assertions": [
    {"type": "status_code", "value": 200},
    {"type": "json_path", "path": "$.data", "operator": "not_empty"}
  ]
}
```

### UI 自动化测试操作流程

1. **录制脚本**: 点击"录制脚本"按钮
   - 输入目标 URL 和脚本名称
   - 在打开的浏览器中执行操作（点击、输入、滚动等）
   - 操作会自动记录为测试步骤
   - 点击"停止录制"并保存脚本
2. **编辑脚本**: 可视化编辑录制的步骤，添加断言和等待
3. **执行测试**: 点击"执行"按钮运行 UI 测试
4. **查看结果**: 查看执行日志、截图和错误信息

```
支持的操作类型：
- navigate: 打开 URL
- click: 点击元素
- fill: 输入文本
- select: 下拉选择
- hover: 鼠标悬停
- wait: 等待（固定时间/元素出现/页面加载）
- screenshot: 截图
- assert: 断言（文本包含/URL 包含/元素可见）
- extract: 提取变量
```

## 项目结构

```
JTest/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api/           # API 调用封装
│   │   ├── components/    # React 组件
│   │   ├── context/       # 全局状态管理
│   │   ├── hooks/         # 自定义 Hooks
│   │   ├── features/      # 功能模块
│   │   └── utils/         # 工具函数
│   └── public/
├── testmanager/           # Django 项目配置
│   ├── settings.py        # 项目配置
│   ├── urls.py            # 路由配置
│   ├── celery.py          # Celery 配置
│   └── asgi.py            # ASGI 配置
├── testmanager_app/       # 主应用 (API 测试、项目管理)
│   ├── models.py          # 数据模型
│   ├── views.py           # API 视图
│   ├── serializers.py     # 序列化器
│   └── services.py        # 业务逻辑
├── test_ui_app/           # UI 测试应用
│   ├── models.py          # UI 测试数据模型
│   ├── views.py           # UI 测试 API
│   ├── recording/         # 录制功能
│   ├── execution/         # 执行引擎
│   └── validators/        # 脚本验证
├── test_ai_agent/         # AI 辅助功能
├── manage.py
├── requirements.txt
├── start.py               # 一键启动脚本 (Windows/Linux/Mac)
└── start.sh               # Shell 启动脚本 (Linux/Mac)
```

## 开发者指南

### 开发环境配置

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest

# 运行单元测试（带覆盖率）
pytest --cov=. --cov-report=html

# 数据库迁移
python manage.py makemigrations
python manage.py migrate
```

### 代码规范

- **Python**: 遵循 PEP 8，使用 Black 格式化
- **JavaScript/React**: 遵循 ESLint 规则
- **提交信息**: 使用语义化提交 (feat/fix/docs/refactor)

```bash
# 提交示例
git commit -m "feat: Add user authentication"
git commit -m "fix: Resolve login redirect issue"
git commit -m "docs: Update API documentation"
```

### API 接口说明

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `/api/auth/login/` | 用户登录 |
| 项目 | `/api/projects/` | 项目 CRUD |
| API 请求 | `/api/api-requests/` | API 请求管理 |
| 测试执行 | `/api/test-executions/` | 测试执行记录 |
| UI 测试 | `/api/ui-test/ui-scripts/` | UI 测试脚本管理 |
| AI 辅助 | `/api/ai/` | AI 功能接口 |

### 扩展开发指南

#### 添加新的 API 端点

1. 在 `testmanager_app/models.py` 定义数据模型
2. 在 `testmanager_app/serializers.py` 创建序列化器
3. 在 `testmanager_app/views.py` 创建 ViewSet
4. 在 `testmanager_app/urls.py` 注册路由

```python
# 示例：添加新模型
class NewFeature(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

# 示例：添加 ViewSet
class NewFeatureViewSet(viewsets.ModelViewSet):
    queryset = NewFeature.objects.all()
    serializer_class = NewFeatureSerializer
```

#### 添加新的前端页面

1. 在 `frontend/src/components/` 创建组件
2. 在 `frontend/src/api/` 添加 API 调用
3. 在 `frontend/src/App.js` 添加路由

```javascript
// 示例：添加新组件
import React from 'react';
import { Card, Table } from 'antd';

const NewFeature = () => {
  return (
    <Card title="新功能">
      <Table columns={columns} dataSource={data} />
    </Card>
  );
};

export default NewFeature;
```

#### 添加新的 UI 测试操作类型

1. 在 `test_ui_app/execution/action_runner.py` 添加操作处理
2. 在 `frontend/src/constants/index.js` 添加操作标签
3. 在 `frontend/src/components/UiTestManager.js` 添加表单字段

## 常见问题

### Q: Playwright 浏览器安装失败？
```bash
# 手动安装
python -m playwright install chromium
# 或安装所有浏览器
python -m playwright install
```

### Q: Celery Worker 无法启动？
确保 Redis 服务已启动，检查 `.env` 中的 Redis 配置：
```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Q: 前端无法连接后端 API？
检查 `frontend/.env` 中的 API 地址配置：
```
REACT_APP_API_BASE_URL=http://localhost:8000
```

### Q: 数据库连接失败？
- SQLite: 确保有写入权限
- MySQL: 检查 `.env` 中的数据库配置，确保数据库已创建

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发建议

- 新功能请先创建 Issue 讨论
- 保持代码风格一致
- 添加必要的测试用例
- 更新相关文档

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- GitHub Issues: [提交问题](https://github.com/yanjun1688/Jarrett_Test/issues)
- 项目主页: [Jarrett_Test](https://github.com/yanjun1688/Jarrett_Test)
