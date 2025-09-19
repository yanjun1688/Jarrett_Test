# 测试用例管理平台

一个基于Django和React的测试用例管理平台，用于集中管理测试用例、执行测试和查看结果。

## 功能特性

### 1. 用例管理
- 用例编写：支持基本信息（标题、步骤、预期结果）
- 用例组织：按项目/模块分类
- 用例导入导出：Excel/CSV 格式

### 2. 测试执行
- 手工执行：测试人员可以标记执行结果（通过/失败/阻塞）
- 执行记录：保存测试历史，支持查询

### 3. 测试报告
- 基本统计：执行数、通过率、失败率
- 可视化报表：柱状图/饼图简单展示

### 4. 自动化测试集成
- Pytest测试框架集成
- 测试脚本上传和执行
- API测试（类似Postman/Apifox）
- 请求集合管理，支持批量运行

### 5. 用户与权限（简化 MVP）
- MVP 阶段支持单用户或项目隔离

## 技术栈

### 后端
- Django 5.2
- Django REST Framework
- Pytest (测试框架)
- Requests (HTTP库)
- SQLite（默认数据库）

### 前端
- React 18
- React Router
- Axios
- Recharts（数据可视化）

## 快速开始

### 后端启动
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建管理员用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

### 前端启动
```bash
# 安装依赖
npm install

# 启动开发服务器
npm start
```

## API接口

### 项目管理
- `GET /api/projects/` - 获取项目列表
- `POST /api/projects/` - 创建项目
- `GET /api/projects/{id}/` - 获取项目详情
- `PUT /api/projects/{id}/` - 更新项目
- `DELETE /api/projects/{id}/` - 删除项目
- `GET /api/projects/{id}/statistics/` - 获取项目统计信息

### 模块管理
- `GET /api/modules/` - 获取模块列表
- `POST /api/modules/` - 创建模块
- `GET /api/modules/{id}/` - 获取模块详情
- `PUT /api/modules/{id}/` - 更新模块
- `DELETE /api/modules/{id}/` - 删除模块

### 测试用例管理
- `GET /api/testcases/` - 获取测试用例列表
- `POST /api/testcases/` - 创建测试用例
- `GET /api/testcases/{id}/` - 获取测试用例详情
- `PUT /api/testcases/{id}/` - 更新测试用例
- `DELETE /api/testcases/{id}/` - 删除测试用例

### 测试执行记录
- `GET /api/executions/` - 获取执行记录列表
- `POST /api/executions/` - 创建执行记录
- `GET /api/executions/{id}/` - 获取执行记录详情
- `PUT /api/executions/{id}/` - 更新执行记录
- `DELETE /api/executions/{id}/` - 删除执行记录

### 测试报告
- `GET /api/reports/` - 获取报告列表
- `POST /api/reports/` - 创建报告
- `GET /api/reports/{id}/` - 获取报告详情
- `PUT /api/reports/{id}/` - 更新报告
- `DELETE /api/reports/{id}/` - 删除报告
- `POST /api/reports/generate_report/` - 生成测试报告

### 测试脚本管理
- `GET /api/test-scripts/` - 获取测试脚本列表
- `POST /api/test-scripts/` - 创建测试脚本
- `GET /api/test-scripts/{id}/` - 获取测试脚本详情
- `PUT /api/test-scripts/{id}/` - 更新测试脚本
- `DELETE /api/test-scripts/{id}/` - 删除测试脚本
- `POST /api/test-scripts/{id}/execute/` - 执行测试脚本

### 脚本执行记录
- `GET /api/script-executions/` - 获取脚本执行记录列表
- `POST /api/script-executions/` - 创建脚本执行记录
- `GET /api/script-executions/{id}/` - 获取脚本执行记录详情

### API请求管理
- `GET /api/api-requests/` - 获取API请求列表
- `POST /api/api-requests/` - 创建API请求
- `GET /api/api-requests/{id}/` - 获取API请求详情
- `PUT /api/api-requests/{id}/` - 更新API请求
- `DELETE /api/api-requests/{id}/` - 删除API请求
- `POST /api/api-requests/{id}/execute/` - 执行API请求

### API断言管理
- `GET /api/api-assertions/` - 获取API断言列表
- `POST /api/api-assertions/` - 创建API断言
- `GET /api/api-assertions/{id}/` - 获取API断言详情
- `PUT /api/api-assertions/{id}/` - 更新API断言
- `DELETE /api/api-assertions/{id}/` - 删除API断言

### 请求集合管理
- `GET /api/request-collections/` - 获取请求集合列表
- `POST /api/request-collections/` - 创建请求集合
- `GET /api/request-collections/{id}/` - 获取请求集合详情
- `PUT /api/request-collections/{id}/` - 更新请求集合
- `DELETE /api/request-collections/{id}/` - 删除请求集合
- `POST /api/request-collections/{id}/execute/` - 执行请求集合

### 集合执行记录
- `GET /api/collection-executions/` - 获取集合执行记录列表
- `POST /api/collection-executions/` - 创建集合执行记录
- `GET /api/collection-executions/{id}/` - 获取集合执行记录详情

### 导入导出
- `POST /api/import-testcases/` - 导入测试用例（Excel/CSV）
- `GET /api/export-testcases/` - 导出测试用例（Excel）
- `GET /api/import-template/` - 获取导入模板

## 项目结构

```
testmanager/
├── testmanager/          # Django项目配置
├── tests/                # 测试管理应用
│   ├── models.py         # 数据模型
│   ├── views.py          # API视图
│   ├── serializers.py    # 序列化器
│   ├── urls.py           # URL路由
│   ├── import_export.py  # 导入导出功能
│   └── tests.py          # 单元测试
├── frontend/             # React前端应用
│   ├── src/
│   │   ├── components/   # React组件
│   │   ├── App.js        # 主应用组件
│   │   └── index.js      # 入口文件
│   └── public/           # 静态资源
├── manage.py             # Django管理脚本
└── requirements.txt      # Python依赖
```

## 开发理念

本项目采用TDD（测试驱动开发）理念，MVP（最小可行产品）产品层面，MVT（Model-View-Template）框架层面进行开发。

## 许可证

MIT License