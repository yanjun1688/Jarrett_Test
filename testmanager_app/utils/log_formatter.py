"""
执行日志格式化管理器
提供统一的日志格式和时间戳管理
"""

from django.utils import timezone


class ExecutionLogger:
    """
    执行日志格式化管理器

    解决日志时间戳重复生成的问题，提供统一的日志格式

    使用示例:
        logger = ExecutionLogger()
        logger.add_start(execution_id, api_request)
        logger.add_response(result)
        logs = logger.get_logs()
    """

    def __init__(self, start_time=None):
        """
        初始化日志管理器

        Args:
            start_time: 开始时间，如果为None则使用当前时间
        """
        self.logs = []
        self.start_time = start_time or timezone.now()

    def add(self, message, level='INFO', timestamp=None):
        """
        添加日志条目

        Args:
            message: 日志消息
            level: 日志级别（INFO/WARNING/ERROR）
            timestamp: 时间戳，如果为None则使用当前时间
        """
        ts = timestamp or timezone.now()
        self.logs.append(f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def add_start(self, execution_id, api_request):
        """
        添加开始执行的日志

        Args:
            execution_id: 执行记录ID
            api_request: API请求对象
        """
        self.add("======== 开始执行API测试 ========")
        self.add(f"执行记录ID: {execution_id}")
        self.add(f"API名称: {api_request.name}")
        self.add(f"请求URL: {api_request.url}")
        self.add(f"请求方法: {api_request.method}")

        # 获取代理配置
        import os
        proxy = os.environ.get('HTTP_PROXY') or '无代理'
        self.add(f"代理配置: {proxy}")

    def add_request_sent(self):
        """添加请求已发送的日志"""
        self.add("正在发送请求...")

    def add_request_completed(self):
        """添加请求已完成的日志"""
        self.add("请求发送完成")

    def add_response(self, result):
        """
        添加响应日志

        Args:
            result: API执行结果
        """
        if result.get('error'):
            self.add(f"❌ 请求失败")
            self.add(f"错误信息: {result['error']}")
        else:
            self.add(f"✅ 收到响应")
            self.add(f"HTTP状态码: {result.get('response_status', 'N/A')}")
            self.add(f"响应时间: {result['response_time']:.4f} 秒")

            # 解析响应体
            import json
            try:
                response_body = json.loads(result['response_body'])
                self.add(f"响应体格式: JSON")
                # 美化打印JSON格式
                formatted_json = json.dumps(response_body, indent=2, ensure_ascii=False)
                self.add(f"响应体内容:\n{formatted_json}")
            except:
                response_body = result['response_body']
                self.add(f"响应体格式: 文本")
                self.add(f"响应体内容:\n{response_body}")

    def add_assertions(self, assertions):
        """
        添加断言验证日志

        Args:
            assertions: 断言结果列表
        """
        if not assertions:
            return

        self.add("开始验证断言...")
        for assertion in assertions:
            status_str = "✅ 通过" if assertion['passed'] else "❌ 失败"
            self.add(f"  [{status_str}] 断言类型: {assertion['assertion_type']}")

    def add_assertion_summary(self, passed_count, total_count):
        """
        添加断言统计日志

        Args:
            passed_count: 通过的断言数
            total_count: 总断言数
        """
        if total_count > 0:
            self.add(f"📊 断言统计: {passed_count}/{total_count} 通过")

    def add_test_result(self, is_passed, passed_count, total_count):
        """
        添加测试结果日志

        Args:
            is_passed: 是否通过
            passed_count: 通过的断言数
            total_count: 总断言数
        """
        if is_passed:
            self.add(f"✅ 测试通过")
        else:
            self.add(f"❌ 测试失败")

    def add_completion(self):
        """添加执行完成日志"""
        self.add("======== 执行完成 ========")

    def add_formatted_summary(self, formatted_summary):
        """
        添加格式化的执行摘要

        Args:
            formatted_summary: 格式化的摘要字符串
        """
        self.add("\n" + "="*60)
        self.add("执行摘要:")
        self.add("="*60)
        self.add(formatted_summary)

    def get_logs_list(self):
        """获取日志列表"""
        return self.logs

    def get_logs_string(self):
        """获取合并的日志字符串"""
        return "\n".join(self.logs)

    def get_logs_count(self):
        """获取日志条目数"""
        return len(self.logs)
