# UI 测试应用模块 (test_ui_app)

UI 测试应用模块是一个基于 Playwright 的 Web UI 自动化测试框架，提供脚本录制、编辑、执行和结果管理等功能。

## 目录结构

```
test_ui_app/
├── models.py              # 数据模型定义
├── services.py            # 业务服务层
├── views.py               # REST API 视图
├── serializers.py         # DRF 序列化器
├── urls.py                # URL 路由配置
├── playwright_engine.py   # Playwright 执行引擎
├── tasks.py               # Celery 异步任务
├── agent_integration.py   # Agent 集成模块
├── consumers.py           # WebSocket 消费者
├── execution/             # 执行管理
│   ├── execution_manager.py   # 执行生命周期管理
│   ├── action_runner.py       # 动作执行器
│   └── log_collector.py       # 日志采集器
├── recording/             # 录制功能
│   ├── session_manager.py     # 录制会话管理
│   └── sync_recorder.py       # 同步录制器
├── validators/            # 校验器
│   └── script_validator.py    # 脚本校验器
├── converters/            # 格式转换器
│   └── action_converter.py    # Action 格式转换
├── parsers/               # 解析器
├── utils/                 # 工具函数
└── db/                    # 数据库操作
```

## 核心功能

### 1. 测试脚本管理

**数据模型**:
- `UITestScript`: UI 测试脚本，存储动作列表、浏览器配置等
- `UITestExecution`: 执行记录，存储执行状态、结果、日志等

**Actions 格式**:
```json
[
  {
    "id": "action_1",
    "order": 1,
    "type": "navigate",
    "params": {"url": "https://example.com"},
    "selector": null,
    "description": "导航到首页"
  },
  {
    "id": "action_2",
    "order": 2,
    "type": "fill",
    "params": {"value": "test_user"},
    "selector": {"type": "id", "value": "username"},
    "description": "填写用户名"
  }
]
```

### 2. Playwright 执行引擎

**核心类**: `PlaywrightEngine`

**功能**:
- 浏览器初始化和清理（支持 Chromium、Firefox、WebKit）
- URL 验证和自动修复
- 语义化元素定位器（遵循 Playwright 最佳实践）
- 截图功能
- Windows 兼容的事件循环

**定位器优先级**:
1. `testid`: `get_by_test_id()` - 专门用于测试的标识
2. `role`: `get_by_role()` - 基于 ARIA 角色的语义化定位
3. `label`: `get_by_label()` - 基于标签文本的表单元素定位
4. `text`: `get_by_text()` - 基于文本内容定位
5. `placeholder`: `get_by_placeholder()` - 基于占位符定位
6. `id/name/css`: 传统 CSS 选择器

### 3. 动作执行器

**核心类**: `ActionRunner`（继承自 `PlaywrightEngine`）

**支持的动作类型**:

| 类型 | 描述 | 参数 |
|------|------|------|
| `navigate` | 导航到 URL | `url` |
| `click` | 点击元素 | `selector` |
| `fill` | 填写输入框 | `selector`, `value` |
| `select` | 选择下拉选项 | `selector`, `value` |
| `press` | 按键 | `selector`, `key` |
| `hover` | 悬停 | `selector` |
| `wait` | 等待 | `type`, `timeout/selector` |
| `screenshot` | 截图 | `name` |
| `canvas_click` | Canvas 点击 | `selector`, `x`, `y` |
| `canvas_drag` | Canvas 拖拽 | `selector`, `start_x/y`, `end_x/y` |

**自愈机制**:
- 当元素定位失败时，自动在页面中寻找最合适的替代元素
- 支持智能评分和匹配
- 记录原始选择器和修复后的选择器

### 4. 执行管理器

**核心类**: `ExecutionManager`

**执行生命周期**:
1. 加载脚本
2. 校验脚本（完整性、合法性）
3. 创建工作目录
4. 创建执行记录
5. 初始化浏览器
6. 执行 Actions
7. 采集日志和结果
8. 清理资源

### 5. 脚本录制

**录制器**: `SyncBrowserRecorder`

**功能**:
- 打开浏览器录制用户操作
- 自动捕获点击、输入、导航等操作
- 生成标准化 Actions 格式
- 支持质量检查

### 6. 元素提取

**核心类**: `ElementExtractor`

**功能**:
- 使用 Playwright 渲染页面
- 自动提取交互元素（input、button、a、select 等）
- 生成选择器提示
- 支持动态页面（等待网络空闲）

### 7. 脚本校验器

**核心类**: `ScriptValidator`

**校验项**:
- Actions 格式完整性
- 必填字段检查
- 参数合法性验证
- 浏览器配置验证
- 脚本质量检查

## REST API

### 脚本管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ui-test/scripts/` | GET | 获取脚本列表 |
| `/api/ui-test/scripts/` | POST | 创建脚本 |
| `/api/ui-test/scripts/{id}/` | GET | 获取脚本详情 |
| `/api/ui-test/scripts/{id}/` | PUT/PATCH | 更新脚本 |
| `/api/ui-test/scripts/{id}/` | DELETE | 删除脚本 |
| `/api/ui-test/scripts/{id}/execute/` | POST | 执行脚本 |

### 录制相关

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ui-test/scripts/sync_record/` | POST | 开始同步录制 |
| `/api/ui-test/scripts/record/` | POST | 保存录制脚本 |
| `/api/ui-test/scripts/quality_check/` | POST | 脚本质量检查 |

### 元素操作

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ui-test/scripts/preview_page/` | GET | 预览页面（截图） |
| `/api/ui-test/scripts/select_element/` | POST | 选择元素（获取定位器） |
| `/api/ui-test/extract-elements/` | POST | 提取页面元素 |

### 执行查询

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ui-test/executions/` | GET | 获取执行记录列表 |
| `/api/ui-test/executions/{id}/` | GET | 获取执行详情 |
| `/api/ui-test/executions/{id}/logs/` | GET | 获取执行日志 |
| `/api/ui-test/scripts/get_execution_status/` | GET | 查询执行状态 |

## 异步执行

使用 Celery 进行后台任务执行：

```python
from test_ui_app.tasks import execute_ui_test_task

# 提交异步任务
task = execute_ui_test_task.delay(script_id, user_id=user_id)

# 获取任务状态
result = task.result
```

## 使用示例

### 创建并执行测试脚本

```python
from test_ui_app.services import ScriptBuilder

# 创建脚本
script = ScriptBuilder.create_script_from_steps(
    name="登录测试",
    steps_data=[
        {
            "id": "action_1",
            "order": 1,
            "type": "navigate",
            "params": {"url": "https://example.com/login"}
        },
        {
            "id": "action_2",
            "order": 2,
            "type": "fill",
            "selector": {"type": "id", "value": "username"},
            "params": {"value": "test_user"}
        },
        {
            "id": "action_3",
            "order": 3,
            "type": "fill",
            "selector": {"type": "id", "value": "password"},
            "params": {"value": "test_pass"}
        },
        {
            "id": "action_4",
            "order": 4,
            "type": "click",
            "selector": {"type": "text", "value": "登录"}
        }
    ],
    project_id=1,
    user_id=1
)
```

### 预览页面

```python
from test_ui_app.services import PlaywrightService

service = PlaywrightService()
result = service.preview_page_sync(
    url="https://example.com",
    browser_type="chromium",
    viewport_width=1280,
    viewport_height=720
)
# result['screenshot'] 包含 base64 编码的截图
```

### 提取页面元素

```python
from test_ui_app.services import ElementExtractor

extractor = ElementExtractor()
result = extractor.extract_page_elements(
    url="https://example.com",
    wait_for_network=True
)
# result['elements'] 包含提取的交互元素列表
```

## 技术特点

### 1. 语义化定位器

遵循 Playwright 最佳实践，优先使用语义化定位器而非脆弱的 CSS 选择器：
- 更稳定，不受页面结构变化影响
- 更易读，定位意图清晰
- 更健壮，自动等待元素可交互

### 2. 自愈机制

当首选定位器失败时，自动智能匹配替代元素：
- 基于关键词评分
- 基于元素属性匹配
- 记录修复历史，便于调试

### 3. 异步架构

- 使用 Celery 进行后台任务执行
- 支持任务进度查询
- 前端可轮询执行状态

### 4. Windows 兼容

- 正确处理 ProactorEventLoop（Windows 默认）
- 避免 SelectorEventLoop 的子进程问题
- 带超时保护的资源清理

### 5. 完整性校验

- 创建/录制后自动校验脚本
- 检测格式错误、缺失字段
- 提供质量报告和改进建议

## 配置选项

### 脚本配置

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `browser_type` | str | chromium | 浏览器类型 |
| `headless` | bool | True | 无头模式 |
| `viewport_width` | int | 1280 | 视口宽度 |
| `viewport_height` | int | 720 | 视口高度 |
| `timeout` | int | 30000 | 超时时间（毫秒） |

## 后续展望

1. **可视化编辑器**: 提供拖拽式脚本编辑界面
2. **智能定位器生成**: 基于页面结构自动生成稳定的选择器
3. **跨浏览器测试**: 支持多浏览器并行执行对比
4. **测试报告增强**: 生成详细的测试报告和统计数据
5. **录制回放优化**: 支持更多交互类型的录制
6. **AI 辅助**: 集成 Agent 能力，自然语言生成测试脚本
7. **移动端测试**: 支持移动设备模拟和真机测试
8. **性能测试**: 集成性能指标采集和分析