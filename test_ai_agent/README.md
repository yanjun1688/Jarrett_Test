# AI Agent App

AI Agent App是一个能够处理PRD文档并自动生成测试用例的Django应用。

## 功能特性

- 支持PDF、Word和TXT格式的PRD文档加载
- 利用LangChain和大语言模型（LLM）分析需求并生成测试用例
- 将生成的测试用例导出为Excel格式
- 提供RESTful API接口

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境配置

在项目根目录的`.env`文件中配置以下环境变量：

```
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_API_KEY=your_langchain_api_key_here
```

## API接口

### 处理PRD文档

```
POST /api/ai-agent/process-prd/
```

**参数:**
- `file`: 上传的PRD文档文件

**响应:**
```json
{
  "success": true,
  "message": "Test cases generated successfully",
  "data": {
    "chunk_id": "chunk_1",
    "test_suites_count": 2
  }
}
```

### 导出测试用例

```
POST /api/ai-agent/export-test-cases/
```

**参数:**
- JSON数据包含处理后的测试用例信息

**响应:**
- Excel文件下载

## 命令行使用

```bash
python manage.py process_prd <input_file> -o <output_file>
```

## 测试

```bash
python manage.py test test_ai_agent
```