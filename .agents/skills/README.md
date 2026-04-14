# Agent Skills 技能包目录

本目录包含多个预置技能包（Skills），用于扩展 Agent 的专业能力。每个技能包封装了特定领域的知识、工作流程和最佳实践。

## 目录结构

```
.agents/skills/
├── testcase-generator/     # 测试用例生成器
├── frontend-design/        # 前端界面设计
├── api-design-principles/  # API 设计原则
├── webapp-testing/         # Web 应用测试
├── python-testing-patterns/# Python 测试模式
├── agent-browser/          # 浏览器自动化
└── find-skills/            # 技能发现工具
```

## 技能包列表

| 技能包 | 模式 | 功能描述 |
|--------|------|----------|
| `testcase-generator` | generate | 测试用例生成器，基于等价类划分和边界值分析理论生成高质量测试用例 |
| `frontend-design` | generate | 前端界面设计，创建独特的、生产级的 Web UI 组件和页面 |
| `api-design-principles` | generate | REST/GraphQL API 设计原则，构建直观、可扩展、可维护的 API |
| `webapp-testing` | execute | Web 应用测试工具包，使用 Playwright 进行 UI 功能验证和调试 |
| `python-testing-patterns` | generate | Python 测试模式，pytest 最佳实践、TDD、Mocking 等 |
| `agent-browser` | execute | 浏览器自动化 CLI，用于页面交互、表单填写、截图、数据抓取等 |
| `find-skills` | generate | 帮助用户发现和安装技能包 |

## 技能模式说明

- **generate**: 生成类技能，帮助 Agent 生成代码、文档或设计方案
- **execute**: 执行类技能，执行具体的操作任务

## 技能包格式

每个技能包遵循标准结构：

```
skill-name/
├── SKILL.md          # 必需，技能定义文件（YAML frontmatter + Markdown 内容）
├── references/       # 可选，参考文档
├── scripts/          # 可选，脚本文件
├── templates/        # 可选，模板文件
└── examples/         # 可选，示例文件
```

### SKILL.md 格式

```yaml
---
name: skill-name
description: 技能描述
allowed-tools: Read, Write, Bash  # 可选，限制可用工具
mode: generate | execute
---

# 技能详细说明
...
```

## 使用方式

Agent 通过 Skill Tool 加载技能包：

```
skill("skill-name")
```

加载后，技能包的详细说明将被注入到对话上下文中，指导 Agent 完成特定任务。

## 技能包详解

### testcase-generator

**触发条件**:
- 用户执行 `/testcase-gen` 命令
- 需要生成测试用例

**核心能力**:
- 等价类划分法
- 边界值分析法
- 自动生成 Markdown 格式测试用例
- 内置校验脚本验证用例质量

**输入输出**:
- 输入: `test-case/plan.md`, `clarified-requirements/index.md`
- 输出: `test-case/{ITEM}/{POINT}.md`, `test-case/all_cases.md`

---

### frontend-design

**触发条件**:
- 构建 Web 组件、页面、应用
- 创建 landing pages, dashboards, React 组件
- 美化/设计 Web UI

**核心能力**:
- 独特的字体和排版选择
- 大胆的色彩和主题设计
- 动画和微交互
- 非常规布局和空间构图
- 避免通用 AI 生成的设计风格

---

### api-design-principles

**触发条件**:
- 设计新 API
- 审查 API 规范
- 建立 API 设计标准

**核心能力**:
- RESTful 设计原则
- GraphQL Schema 设计
- API 版本控制策略
- 分页、过滤、错误处理模式
- HATEOAS 实现

---

### webapp-testing

**触发条件**:
- 测试本地 Web 应用
- 验证前端功能
- 调试 UI 行为
- 截取浏览器截图

**核心能力**:
- Playwright 脚本编写
- 服务器生命周期管理
- 页面交互自动化
- 元素发现和选择器识别

**辅助脚本**:
- `scripts/with_server.py` - 管理服务器生命周期

---

### python-testing-patterns

**触发条件**:
- 编写 Python 测试
- 设置测试套件
- 实现 TDD

**核心能力**:
- pytest 基础和高级模式
- Fixtures 设计
- Mocking 和 Patching
- 参数化测试
- 异步代码测试
- 属性测试（Hypothesis）
- 测试覆盖率报告
- CI/CD 集成

---

### agent-browser

**触发条件**:
- "打开网站"、"填写表单"
- "点击按钮"、"截图"
- "抓取数据"、"测试 Web 应用"
- "登录网站"、"自动化浏览器操作"

**核心能力**:
- 页面导航和快照
- 表单填写和点击操作
- 截图和 PDF 生成
- 认证状态管理
- 并行会话
- iOS 模拟器支持

**核心工作流**:
```
Navigate → Snapshot → Interact → Re-snapshot
```

---

### find-skills

**触发条件**:
- "如何做 X"、"找到 X 的技能"
- "有没有可以...的技能"
- 用户想扩展 Agent 能力

**核心能力**:
- 搜索可用技能
- 安装技能包
- 技能更新检查

**常用命令**:
- `npx skills find [query]` - 搜索技能
- `npx skills add <package>` - 安装技能
- `npx skills update` - 更新所有技能

## 扩展技能包

要创建新的技能包：

1. 在 `.agents/skills/` 下创建新目录
2. 创建 `SKILL.md` 文件，包含 YAML frontmatter 和详细说明
3. 可选添加 `references/`, `scripts/`, `templates/`, `examples/` 目录

### SKILL.md 编写指南

```markdown
---
name: my-skill
description: 技能简短描述，用于触发匹配
allowed-tools: Read, Write, Bash  # 可选
mode: generate | execute
---

# 技能名称

## 目标
描述技能的目标和用途

## 触发条件
列出何时使用此技能

## 工作流程
详细描述执行步骤

## 示例
提供具体使用示例

## 参考资源
列出相关文档和工具
```

## 后续展望

1. **技能包扩展**: 添加更多领域专业技能（如数据库设计、安全审计、性能优化等）
2. **技能组合**: 支持多个技能包协同工作
3. **自定义技能**: 允许用户创建和共享自己的技能包
4. **技能版本管理**: 支持技能包的版本控制和更新
5. **技能市场**: 建立技能包索引和发现机制