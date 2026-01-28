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
- MySQL

### 前端
- React 18
- Ant Design
- Axios

## 快速开始

### 环境准备

1. 克隆项目
```bash
git clone https://github.com/your-username/JTest.git
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

6. 安装前端依赖
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
# 启动 Django 后端
python manage.py runserver

# 启动 Celery Worker
celery -A testmanager worker -l info -P solo

# 启动前端开发服务器
cd frontend && npm start
```

## 项目结构

```
JTest/
├── frontend/           # React 前端
├── testmanager/        # Django 项目配置
├── testmanager_app/    # 主应用 (API 测试、项目管理)
├── test_ui_app/        # UI 测试应用
├── test_ai_agent/      # AI 辅助功能
├── manage.py
├── requirements.txt
└── start.py            # 一键启动脚本
```

## 许可证

MIT License
