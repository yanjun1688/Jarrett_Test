"""
测试报告服务
处理测试报告生成相关的业务逻辑
"""

from __future__ import annotations

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.db.models import Q, Count, QuerySet
from django.conf import settings
from django.contrib.auth.models import User
from core.models import TestExecution, ChatBotExecutionLog, Project
from testmanager_app.models import TestReport, ScriptExecution

logger = logging.getLogger(__name__)


class ReportService:
    """
    测试报告生成服务

    处理报告生成的核心业务逻辑，包括数据聚合、报告创建等
    """

    @staticmethod
    @transaction.atomic
    def generate_report(
        project: Project,
        start_date: datetime,
        end_date: datetime,
        created_by: User
    ) -> TestReport:
        """
        生成测试报告（带事务保护）

        Args:
            project: Project对象
            start_date: 开始时间
            end_date: 结束时间
            created_by: 创建者

        Returns:
            TestReport: 生成的报告实例

        Raises:
            Exception: 数据库操作失败时抛出
        """
        # 1. 获取执行统计数据
        stats = ReportService._get_execution_stats(project, start_date, end_date)

        # 2. 创建报告
        report = TestReport.objects.create(
            project=project,
            name=f"{project.name} 测试报告 {start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}",
            description=f"时间范围：{start_date.strftime('%Y-%m-%d %H:%M')} 至 {end_date.strftime('%Y-%m-%d %H:%M')}",
            start_date=start_date,
            end_date=end_date,
            total_cases=stats['total_cases'],
            passed_cases=stats['passed_cases'],
            failed_cases=stats['failed_cases'],
            blocked_cases=stats['blocked_cases'],
            skipped_cases=stats['skipped_cases'],
            created_by=created_by
        )

        logger.info(f"成功生成测试报告: report_id={report.id}, project={project.name}")

        return report

    @staticmethod
    def _get_execution_stats(
        project: Project,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """
        获取指定时间范围内的执行统计数据

        使用自定义 QuerySet 方法，简化查询逻辑，提高代码复用性

        Args:
            project: Project对象
            start_date: 开始时间
            end_date: 结束时间

        Returns:
            dict: 统计数据，包含total_cases, passed_cases, failed_cases, blocked_cases, skipped_cases

        Raises:
            Exception: 数据库查询失败时抛出
        """
        try:
            # 使用自定义 QuerySet 方法进行查询和聚合
            stats = TestExecution.objects.by_project_and_date_range(  # type: ignore[attr-defined]
                project, start_date, end_date
            ).aggregate_stats()

            # 处理NULL值，提供默认值0
            return {
                'total_cases': stats.get('total_cases', 0),
                'passed_cases': stats.get('passed_executions', 0),
                'failed_cases': stats.get('failed_executions', 0),
                'blocked_cases': stats.get('blocked_executions', 0),
                'skipped_cases': stats.get('skipped_executions', 0),
            }

        except Exception as e:
            logger.error(f"数据库聚合查询失败: {e}", exc_info=True)
            raise Exception(f"Failed to aggregate test execution data: {str(e)}")

    @staticmethod
    def get_report_data(
        project: Optional[Project] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        created_by: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        获取测试报告数据（聚合API测试、UI测试、ChatBot执行）

        Args:
            project: 项目对象（可选）
            start_date: 开始时间（可选）
            end_date: 结束时间（可选）
            created_by: 创建者（可选）

        Returns:
            dict: 包含 statistics 的报告数据
        """
        from core.models import Project

        statistics = []
        projects = [project] if project else Project.objects.all()

        for proj in projects:
            # 1. API测试统计（TestExecution - test_type='api'）
            # 使用 by_project 过滤，关联 test_case.project / api_request.project / collection_execution
            api_executions = TestExecution.objects.filter(
                test_type='api'
            ).by_project(proj)  # type: ignore[attr-defined]
            if start_date:
                api_executions = api_executions.filter(executed_at__gte=start_date)
            if end_date:
                api_executions = api_executions.filter(executed_at__lte=end_date)

            api_stats = api_executions.aggregate(
                total=Count('id'),
                passed=Count('id', filter=Q(status='passed')),
                failed=Count('id', filter=Q(status='failed')),
                blocked=Count('id', filter=Q(status='blocked')),
                skipped=Count('id', filter=Q(status='skipped')),
            )
            api_pass_rate = (api_stats['passed'] / api_stats['total'] * 100) if api_stats['total'] > 0 else 0

            # 2. UI测试统计（ScriptExecution）- 按脚本所属项目过滤
            ui_executions = ScriptExecution.objects.filter(script__project=proj)
            if start_date:
                ui_executions = ui_executions.filter(started_at__gte=start_date)
            if end_date:
                ui_executions = ui_executions.filter(started_at__lte=end_date)

            ui_stats = ui_executions.aggregate(
                total=Count('id'),
                success=Count('id', filter=Q(status='success')),
                failed=Count('id', filter=Q(status='failed')),
                running=Count('id', filter=Q(status='running')),
                pending=Count('id', filter=Q(status='pending')),
            )
            ui_success_rate = (ui_stats['success'] / ui_stats['total'] * 100) if ui_stats['total'] > 0 else 0

            # 3. ChatBot执行统计（ChatBotExecutionLog）- 通过 execution 关联过滤项目
            chatbot_logs = ChatBotExecutionLog.objects.filter(
                execution__isnull=False
            )
            # 复用 TestExecution 的 by_project 过滤逻辑
            chatbot_logs = chatbot_logs.filter(
                Q(execution__api_request__project=proj) |
                Q(execution__collection_execution__collection__project=proj)
            )
            if start_date:
                chatbot_logs = chatbot_logs.filter(created_at__gte=start_date)
            if end_date:
                chatbot_logs = chatbot_logs.filter(created_at__lte=end_date)

            chatbot_stats = chatbot_logs.aggregate(
                total=Count('id'),
                skill_count=Count('id', filter=Q(log_type='skill')),
                api_test_count=Count('id', filter=Q(log_type='api_test')),
                ui_test_count=Count('id', filter=Q(log_type='ui_test')),
            )

            # 统计ChatBot执行成功率（从details.status字段）
            chatbot_success_count = 0
            chatbot_error_count = 0
            for log in chatbot_logs:
                status = log.details.get('status', '') if log.details else ''
                if status == 'success':
                    chatbot_success_count += 1
                elif status == 'error':
                    chatbot_error_count += 1

            chatbot_success_rate = (chatbot_success_count / chatbot_stats['total'] * 100) if chatbot_stats['total'] > 0 else 0

            # 4. 总执行数统计
            total_executions = api_stats['total'] + ui_stats['total'] + chatbot_stats['total']
            total_passed = api_stats['passed'] + ui_stats['success'] + chatbot_success_count
            total_failed = api_stats['failed'] + ui_stats['failed'] + chatbot_error_count
            total_pass_rate = (total_passed / total_executions * 100) if total_executions > 0 else 0

            statistics.append({
                'project_id': proj.id,
                'project_name': proj.name,
                'api_tests': {
                    'total': api_stats['total'],
                    'passed': api_stats['passed'],
                    'failed': api_stats['failed'],
                    'blocked': api_stats['blocked'],
                    'skipped': api_stats['skipped'],
                    'pass_rate': round(api_pass_rate, 2),
                },
                'ui_tests': {
                    'total': ui_stats['total'],
                    'success': ui_stats['success'],
                    'failed': ui_stats['failed'],
                    'running': ui_stats['running'],
                    'pending': ui_stats['pending'],
                    'success_rate': round(ui_success_rate, 2),
                },
                'chatbot_executions': {
                    'total': chatbot_stats['total'],
                    'success': chatbot_success_count,
                    'error': chatbot_error_count,
                    'skill_count': chatbot_stats['skill_count'],
                    'api_test_count': chatbot_stats['api_test_count'],
                    'ui_test_count': chatbot_stats['ui_test_count'],
                    'success_rate': round(chatbot_success_rate, 2),
                },
                'total_executions': total_executions,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'total_pass_rate': round(total_pass_rate, 2),
            })

        return {'statistics': statistics}

    @staticmethod
    def get_report_list(project: Optional[Project] = None) -> QuerySet[TestReport]:
        """
        获取报告列表

        Args:
            project: 过滤的项目（可选）

        Returns:
            QuerySet: 报告查询集
        """
        queryset = TestReport.objects.all().order_by('-created_at')

        if project:
            queryset = queryset.filter(project=project)

        return queryset

    @staticmethod
    def generate_api_test_html_report(
        test_results: Dict[str, Any], 
        api_spec_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成API测试HTML报告

        Args:
            test_results: 测试结果数据，包含测试用例和执行结果
            api_spec_info: API规范信息（可选）

        Returns:
            str: HTML报告内容
        """
        try:
            # 计算统计信息
            total_cases = len(test_results.get('test_cases', []))
            passed_cases = sum(1 for case in test_results.get('test_cases', []) 
                              if case.get('status') == 'passed')
            failed_cases = sum(1 for case in test_results.get('test_cases', []) 
                              if case.get('status') == 'failed')
            skipped_cases = sum(1 for case in test_results.get('test_cases', []) 
                               if case.get('status') == 'skipped')
            
            # 计算通过率
            pass_rate = (passed_cases / total_cases * 100) if total_cases > 0 else 0
            
            # 生成HTML报告
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API测试报告 - {test_results.get('test_plan_name', '未命名测试计划')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eaeaea;
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 16px;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        
        .summary-card.passed {{
            border-left-color: #2ecc71;
        }}
        
        .summary-card.failed {{
            border-left-color: #e74c3c;
        }}
        
        .summary-card.skipped {{
            border-left-color: #f39c12;
        }}
        
        .summary-card .number {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .summary-card.passed .number {{
            color: #2ecc71;
        }}
        
        .summary-card.failed .number {{
            color: #e74c3c;
        }}
        
        .summary-card.skipped .number {{
            color: #f39c12;
        }}
        
        .summary-card .label {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        .test-cases {{
            margin-bottom: 30px;
        }}
        
        .test-cases h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eaeaea;
        }}
        
        .test-case {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
        }}
        
        .test-case.passed {{
            border-left-color: #2ecc71;
            background: #f0fff4;
        }}
        
        .test-case.failed {{
            border-left-color: #e74c3c;
            background: #fff5f5;
        }}
        
        .test-case.skipped {{
            border-left-color: #f39c12;
            background: #fffaf0;
        }}
        
        .test-case-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .test-case-title {{
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .test-case-status {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .status-passed {{
            background: #2ecc71;
            color: white;
        }}
        
        .status-failed {{
            background: #e74c3c;
            color: white;
        }}
        
        .status-skipped {{
            background: #f39c12;
            color: white;
        }}
        
        .test-case-details {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eaeaea;
        }}
        
        .detail-row {{
            display: flex;
            margin-bottom: 8px;
        }}
        
        .detail-label {{
            font-weight: bold;
            min-width: 120px;
            color: #7f8c8d;
        }}
        
        .detail-value {{
            flex: 1;
            word-break: break-all;
        }}
        
        .api-info {{
            background: #f0f7ff;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .api-info h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .api-info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .api-info-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .api-info-label {{
            font-weight: bold;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        
        .api-info-value {{
            color: #2c3e50;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eaeaea;
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        .timestamp {{
            margin-top: 10px;
            font-size: 12px;
        }}
        
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 13px;
            margin: 10px 0;
        }}
        
        .response-success {{
            color: #2ecc71;
        }}
        
        .response-error {{
            color: #e74c3c;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            .summary {{
                grid-template-columns: 1fr;
            }}
            
            .test-case-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            
            .test-case-status {{
                margin-top: 5px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>API测试报告</h1>
            <div class="subtitle">
                {test_results.get('test_plan_name', '未命名测试计划')}
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{total_cases}</div>
                <div class="label">总用例数</div>
            </div>
            <div class="summary-card passed">
                <div class="number">{passed_cases}</div>
                <div class="label">通过用例</div>
            </div>
            <div class="summary-card failed">
                <div class="number">{failed_cases}</div>
                <div class="label">失败用例</div>
            </div>
            <div class="summary-card skipped">
                <div class="number">{skipped_cases}</div>
                <div class="label">跳过用例</div>
            </div>
            <div class="summary-card">
                <div class="number">{pass_rate:.1f}%</div>
                <div class="label">通过率</div>
            </div>
        </div>
        
        {f'<div class="api-info"><h2>API规范信息</h2><div class="api-info-grid">' + 
         ''.join([f'<div class="api-info-item"><span class="api-info-label">{key}:</span><span class="api-info-value">{value}</span></div>' 
                  for key, value in api_spec_info.items()]) + '</div></div>' if api_spec_info else ''}
        
        <div class="test-cases">
            <h2>测试用例详情</h2>
            """
            
            # 添加测试用例详情
            for i, test_case in enumerate(test_results.get('test_cases', []), 1):
                status = test_case.get('status', 'unknown')
                status_class = status
                status_text = {'passed': '通过', 'failed': '失败', 'skipped': '跳过'}.get(status, '未知')
                
                # 格式化请求数据
                request_data = test_case.get('request', {})
                request_str = json.dumps(request_data, ensure_ascii=False, indent=2) if request_data else "无"
                
                # 格式化响应数据
                response_data = test_case.get('response', {})
                response_str = json.dumps(response_data, ensure_ascii=False, indent=2) if response_data else "无"
                
                # 格式化验证结果
                validation_results = test_case.get('validation_results', [])
                validation_html = ""
                if validation_results:
                    validation_html = "<div class='detail-row'><div class='detail-label'>验证结果:</div><div class='detail-value'>"
                    for validation in validation_results:
                        validation_status = "通过" if validation.get('passed') else "失败"
                        validation_class = "response-success" if validation.get('passed') else "response-error"
                        validation_html += f"<div><span class='{validation_class}'>{validation_status}</span>: {validation.get('rule', '')}</div>"
                    validation_html += "</div></div>"
                
                html_content += f"""
            <div class="test-case {status_class}">
                <div class="test-case-header">
                    <div class="test-case-title">用例 #{i}: {test_case.get('name', '未命名用例')}</div>
                    <div class="test-case-status status-{status_class}">{status_text}</div>
                </div>
                <div class="test-case-details">
                    <div class="detail-row">
                        <div class="detail-label">描述:</div>
                        <div class="detail-value">{test_case.get('description', '无描述')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">端点:</div>
                        <div class="detail-value">{test_case.get('endpoint', '未知')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">方法:</div>
                        <div class="detail-value">{test_case.get('method', '未知')}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">请求数据:</div>
                        <div class="detail-value"><pre>{request_str}</pre></div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">响应数据:</div>
                        <div class="detail-value"><pre>{response_str}</pre></div>
                    </div>
                    {validation_html}
                    <div class="detail-row">
                        <div class="detail-label">执行时间:</div>
                        <div class="detail-value">{test_case.get('execution_time', '未知')}ms</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">错误信息:</div>
                        <div class="detail-value">{test_case.get('error_message', '无')}</div>
                    </div>
                </div>
            </div>
                """
            
            html_content += """
        </div>
        
        <div class="footer">
            <div>报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</div>
            <div class="timestamp">JTest API测试平台</div>
        </div>
    </div>
</body>
</html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {e}", exc_info=True)
            # 返回简单的错误报告
            return f"""
            <html>
            <body>
                <h1>报告生成失败</h1>
                <p>错误信息: {str(e)}</p>
                <p>原始数据: {json.dumps(test_results, ensure_ascii=False, indent=2)}</p>
            </body>
            </html>
            """
    
    @staticmethod
    def save_html_report(html_content: str, report_name: Optional[str] = None) -> str:
        """
        保存HTML报告到文件

        Args:
            html_content: HTML内容
            report_name: 报告名称（可选）

        Returns:
            str: 保存的文件路径
        """
        try:
            # 创建报告目录
            reports_dir = os.path.join(settings.BASE_DIR, 'reports', 'api_tests')
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成文件名
            if not report_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_name = f"api_test_report_{timestamp}.html"
            else:
                if not report_name.endswith('.html'):
                    report_name += '.html'
            
            # 保存文件
            file_path = os.path.join(reports_dir, report_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告已保存: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存HTML报告失败: {e}", exc_info=True)
            raise Exception(f"Failed to save HTML report: {str(e)}")
    
    @staticmethod
    def generate_api_test_summary(test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成API测试摘要报告

        Args:
            test_results: 测试结果数据

        Returns:
            dict: 摘要报告数据
        """
        try:
            test_cases = test_results.get('test_cases', [])
            total_cases = len(test_cases)
            
            if total_cases == 0:
                return {
                    'status': 'no_cases',
                    'message': '没有测试用例'
                }
            
            # 统计状态
            passed_cases = sum(1 for case in test_cases if case.get('status') == 'passed')
            failed_cases = sum(1 for case in test_cases if case.get('status') == 'failed')
            skipped_cases = sum(1 for case in test_cases if case.get('status') == 'skipped')
            
            # 计算通过率
            pass_rate = (passed_cases / total_cases * 100) if total_cases > 0 else 0
            
            # 收集失败用例详情
            failed_details = []
            for case in test_cases:
                if case.get('status') == 'failed':
                    failed_details.append({
                        'name': case.get('name', '未命名用例'),
                        'endpoint': case.get('endpoint', '未知'),
                        'error_message': case.get('error_message', '无错误信息'),
                        'validation_errors': [v for v in case.get('validation_results', []) if not v.get('passed')]
                    })
            
            # 收集执行时间统计
            execution_times = [case.get('execution_time', 0) for case in test_cases if case.get('execution_time')]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            return {
                'status': 'success',
                'summary': {
                    'total_cases': total_cases,
                    'passed_cases': passed_cases,
                    'failed_cases': failed_cases,
                    'skipped_cases': skipped_cases,
                    'pass_rate': pass_rate,
                    'avg_execution_time': avg_execution_time,
                    'test_plan_name': test_results.get('test_plan_name', '未命名测试计划'),
                    'generated_at': datetime.now().isoformat()
                },
                'failed_details': failed_details,
                'recommendations': ReportService._generate_recommendations(
                    passed_cases, failed_cases, total_cases, failed_details
                )
            }
            
        except Exception as e:
            logger.error(f"生成API测试摘要失败: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'生成摘要失败: {str(e)}'
            }
    
    @staticmethod
    def _generate_recommendations(
        passed_cases: int, 
        failed_cases: int, 
        total_cases: int, 
        failed_details: List[Dict[str, Any]]
    ) -> List[str]:
        """
        根据测试结果生成建议

        Args:
            passed_cases: 通过用例数
            failed_cases: 失败用例数
            total_cases: 总用例数
            failed_details: 失败用例详情

        Returns:
            list: 建议列表
        """
        recommendations = []
        
        if total_cases == 0:
            recommendations.append("没有执行任何测试用例，请检查测试配置")
            return recommendations
        
        pass_rate = (passed_cases / total_cases * 100) if total_cases > 0 else 0
        
        if pass_rate >= 90:
            recommendations.append("测试通过率很高，API质量良好")
        elif pass_rate >= 70:
            recommendations.append("测试通过率中等，建议检查失败用例")
        else:
            recommendations.append("测试通过率较低，需要重点关注失败用例")
        
        if failed_cases > 0:
            # 分析常见失败原因
            validation_errors = []
            network_errors = []
            server_errors = []
            
            for detail in failed_details:
                error_msg = detail.get('error_message', '').lower()
                if 'validation' in error_msg or 'schema' in error_msg:
                    validation_errors.append(detail)
                elif 'timeout' in error_msg or 'connection' in error_msg:
                    network_errors.append(detail)
                elif '500' in error_msg or 'server' in error_msg:
                    server_errors.append(detail)
            
            if validation_errors:
                recommendations.append(f"发现{len(validation_errors)}个验证错误，请检查API响应格式是否符合规范")
            
            if network_errors:
                recommendations.append(f"发现{len(network_errors)}个网络错误，请检查网络连接和服务器状态")
            
            if server_errors:
                recommendations.append(f"发现{len(server_errors)}个服务器错误，请检查服务器日志")
        
        # 建议增加测试覆盖率
        if total_cases < 10:
            recommendations.append("测试用例数量较少，建议增加测试覆盖率")
        
        return recommendations
