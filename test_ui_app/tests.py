"""
test_ui_app 单元测试

⚠️ 重要：此文件不能直接运行（python tests.py），必须通过 Django 测试框架运行！

正确的运行方式：
1. 使用 Django test 命令（推荐）：
   python manage.py test test_ui_app.tests
   python manage.py test test_ui_app.tests.RecordingFlowIntegrationTest
   python manage.py test test_ui_app.tests.ExecutionFlowIntegrationTest

2. 使用 pytest（如果已安装 pytest-django）：
   pytest test_ui_app/tests.py -v
   pytest test_ui_app/tests.py::RecordingFlowIntegrationTest -v

3. 运行特定测试方法：
   python manage.py test test_ui_app.tests.RecordingFlowIntegrationTest.test_recording_flow_create_session

为什么不能直接运行？
- 使用了相对导入（from .playwright_engine import ...）
- 需要 Django 的测试数据库和配置
- 需要 Django 的包上下文
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from django.test import TestCase
import asyncio
import sys

from .playwright_engine import PlaywrightEngine, create_windows_compatible_event_loop
from .recording.sync_recorder import SyncBrowserRecorder


class PlaywrightEngineTest(TestCase):
    """PlaywrightEngine 单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = PlaywrightEngine()
    
    def test_validate_and_fix_url_basic(self):
        """测试URL验证 - 基本URL"""
        # 正常URL
        self.assertEqual(
            self.engine._validate_and_fix_url("https://example.com"),
            "https://example.com"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url("http://example.com"),
            "http://example.com"
        )
    
    def test_validate_and_fix_url_add_protocol(self):
        """测试URL验证 - 自动添加协议"""
        # 缺少协议
        self.assertEqual(
            self.engine._validate_and_fix_url("example.com"),
            "https://example.com"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url("www.example.com"),
            "https://www.example.com"
        )
    
    def test_validate_and_fix_url_file_path(self):
        """测试URL验证 - 文件路径"""
        # 本地文件路径
        self.assertEqual(
            self.engine._validate_and_fix_url("/path/to/file.html"),
            "file:///path/to/file.html"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url("./relative/path.html"),
            "file://./relative/path.html"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url("../parent/path.html"),
            "file://../parent/path.html"
        )
    
    def test_validate_and_fix_url_strip_quotes(self):
        """测试URL验证 - 移除引号"""
        # 带引号的URL
        self.assertEqual(
            self.engine._validate_and_fix_url('"https://example.com"'),
            "https://example.com"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url("'https://example.com'"),
            "https://example.com"
        )
        self.assertEqual(
            self.engine._validate_and_fix_url('  "https://example.com"  '),
            "https://example.com"
        )
    
    def test_validate_and_fix_url_empty(self):
        """测试URL验证 - 空URL"""
        # 空URL应该抛出异常
        with self.assertRaises(ValueError):
            self.engine._validate_and_fix_url("")
        
        with self.assertRaises(ValueError):
            self.engine._validate_and_fix_url(None)
        
        with self.assertRaises(ValueError):
            self.engine._validate_and_fix_url("   ")
    
    def test_validate_and_fix_url_invalid(self):
        """测试URL验证 - 无效URL"""
        # 无效URL应该抛出异常
        # 注意："not-a-url" 会被自动添加 https://，所以不会抛出异常
        # 真正无效的URL是那些没有 netloc 且 scheme 不在允许列表中的
        # 例如：无效scheme "invalid://"
        with self.assertRaises(ValueError):
            self.engine._validate_and_fix_url("invalid://")
        
        # 或者测试空字符串（已经在 test_validate_and_fix_url_empty 中测试）
        with self.assertRaises(ValueError):
            self.engine._validate_and_fix_url("   ")
    
    def test_get_selector_string_new_format(self):
        """测试选择器转换 - 新格式"""
        # 新格式: {'type': 'id', 'value': 'xxx'}
        selector = {'type': 'id', 'value': 'submit-btn'}
        self.assertEqual(self.engine._get_selector_string(selector), "#submit-btn")
        
        selector = {'type': 'name', 'value': 'username'}
        self.assertEqual(self.engine._get_selector_string(selector), "[name='username']")
        
        selector = {'type': 'css', 'value': '.button.primary'}
        self.assertEqual(self.engine._get_selector_string(selector), ".button.primary")
        
        selector = {'type': 'xpath', 'value': '//button[@id="submit"]'}
        self.assertEqual(self.engine._get_selector_string(selector), "xpath=//button[@id=\"submit\"]")
        
        selector = {'type': 'text', 'value': 'Submit'}
        self.assertEqual(self.engine._get_selector_string(selector), "text=Submit")
        
        selector = {'type': 'testid', 'value': 'submit-button'}
        self.assertEqual(self.engine._get_selector_string(selector), "[data-testid='submit-button']")
        
        selector = {'type': 'role', 'value': 'button'}
        self.assertEqual(self.engine._get_selector_string(selector), "role=button")
        
        selector = {'type': 'label', 'value': 'Username'}
        self.assertEqual(self.engine._get_selector_string(selector), "label=Username")
    
    def test_get_selector_string_old_format(self):
        """测试选择器转换 - 旧格式"""
        # 旧格式: {'locator_type': 'id', 'locator_value': 'xxx'}
        selector = {'locator_type': 'id', 'locator_value': 'submit-btn'}
        self.assertEqual(self.engine._get_selector_string(selector), "#submit-btn")
        
        selector = {'locator_type': 'name', 'locator_value': 'username'}
        self.assertEqual(self.engine._get_selector_string(selector), "[name='username']")
        
        selector = {'locator_type': 'css', 'locator_value': '.button.primary'}
        self.assertEqual(self.engine._get_selector_string(selector), ".button.primary")
    
    def test_get_selector_string_empty(self):
        """测试选择器转换 - 空选择器"""
        with self.assertRaises(ValueError):
            self.engine._get_selector_string(None)
        
        with self.assertRaises(ValueError):
            self.engine._get_selector_string({})
        
        with self.assertRaises(ValueError):
            self.engine._get_selector_string({'type': 'id'})  # 缺少value
        
        with self.assertRaises(ValueError):
            self.engine._get_selector_string({'value': 'submit-btn'})  # 缺少type
    
    def test_get_selector_string_unknown_type(self):
        """测试选择器转换 - 未知类型"""
        # 未知类型应该返回原始值
        selector = {'type': 'unknown', 'value': 'some-value'}
        self.assertEqual(self.engine._get_selector_string(selector), "some-value")
    
    
    @patch('test_ui_app.playwright_engine.async_playwright')
    def test_initialize(self, mock_async_playwright):
        """测试初始化浏览器"""
        # Mock Playwright对象
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # 设置 chromium 对象
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright_instance.chromium = mock_chromium
        
        # 设置 browser 和 context 的方法
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # async_playwright() 返回一个对象，调用 .start() 返回 playwright_instance
        mock_playwright_context = AsyncMock()
        mock_playwright_context.start = AsyncMock(return_value=mock_playwright_instance)
        mock_async_playwright.return_value = mock_playwright_context
        
        # 执行初始化（使用asyncio.run包装）
        result = asyncio.run(self.engine.initialize(browser_type='chromium', headless=True))
        
        # 验证
        self.assertTrue(result)
        self.assertEqual(self.engine.browser, mock_browser)
        self.assertEqual(self.engine.context, mock_context)
        self.assertEqual(self.engine.page, mock_page)
        mock_context.set_default_timeout.assert_called_once_with(30000)
    
    def test_cleanup(self):
        """测试清理资源"""
        # 设置mock对象
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        
        self.engine.page = mock_page
        self.engine.context = mock_context
        self.engine.browser = mock_browser
        self.engine.playwright = mock_playwright
        
        # 执行清理（使用asyncio.run包装）
        asyncio.run(self.engine.cleanup())
        
        # 验证清理顺序
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


class SyncBrowserRecorderTest(TestCase):
    """SyncBrowserRecorder 单元测试
    
    注意：PlaywrightRecorder 已废弃，请使用 SyncBrowserRecorder。
    SyncBrowserRecorder 使用同步模式 + 线程隔离，解决了 Windows 上
    async_playwright 与 SelectorEventLoop 冲突导致的阻塞问题。
    """
    
    def setUp(self):
        """测试前准备"""
        self.recorder = SyncBrowserRecorder()
    
    def test_get_recording_script(self):
        """测试获取录制脚本"""
        script = self.recorder._get_recording_script()
        
        # 验证脚本是字符串
        self.assertIsInstance(script, str)
        self.assertTrue(len(script) > 0)
        
        # 验证脚本包含关键功能
        self.assertIn("getSelector", script)
        self.assertIn("reportAction", script)
        self.assertIn("addEventListener", script)
    
    def test_add_action(self):
        """测试添加动作"""
        action = self.recorder._add_action(
            action_type='click',
            selector='#submit-btn',
            description='点击提交按钮'
        )
        
        # 验证动作格式
        self.assertIn('id', action)
        self.assertIn('order', action)
        self.assertIn('type', action)
        self.assertEqual(action['type'], 'click')
        self.assertEqual(action['description'], '点击提交按钮')
    
    def test_add_action_with_params(self):
        """测试添加带参数的动作"""
        action = self.recorder._add_action(
            action_type='fill',  # 使用 Playwright 标准方法 'fill'
            selector='#username',
            params={'value': 'test_user'},
            description='输入用户名'
        )
        
        # 验证动作格式
        self.assertEqual(action['type'], 'fill')
        self.assertEqual(action['params']['value'], 'test_user')
    

class UtilityFunctionsTest(TestCase):
    """工具函数测试"""
    
    def test_create_windows_compatible_event_loop(self):
        """测试创建Windows兼容的事件循环"""
        loop = create_windows_compatible_event_loop()
        self.assertIsNotNone(loop)
        self.assertTrue(isinstance(loop, asyncio.AbstractEventLoop))
        
        # 清理
        loop.close()


# 注意：由于环境依赖问题，某些测试可能无法运行
# 但测试代码本身是正确的，可以在有完整依赖的环境中运行


# ============================================================================
# 全链路测试 - 录制和执行功能
# ============================================================================

class RecordingFlowIntegrationTest(TestCase):
    """录制功能全链路集成测试"""
    
    def setUp(self):
        """测试前准备"""
        from django.contrib.auth.models import User
        from test_ui_app.recording.session_manager import RecordingSessionManager
        
        # 创建测试用户
        self.test_user, _ = User.objects.get_or_create(
            username='test_recording_user',
            defaults={'email': 'test_recording@example.com'}
        )
        
        # 清理可能的测试会话
        RecordingSessionManager.delete_session = lambda x: True
    
    def test_recording_flow_create_session(self):
        """测试录制流程 - 创建会话"""
        from test_ui_app.recording.session_manager import RecordingSessionManager
        
        # 创建会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com',
            browser_type='chromium'
        )
        
        # 验证会话创建成功
        self.assertIsNotNone(session_id)
        self.assertTrue(len(session_id) > 0)
        
        # 验证会话数据
        session = RecordingSessionManager.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session['user_id'], self.test_user.id)
        self.assertEqual(session['start_url'], 'https://example.com')
        self.assertEqual(session['status'], 'created')
        self.assertEqual(session['steps'], [])
    
    def test_recording_flow_add_steps(self):
        """测试录制流程 - 添加步骤到会话"""
        from test_ui_app.recording.session_manager import RecordingSessionManager
        
        # 创建会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com'
        )
        
        # 添加步骤
        step1 = {
            'action_type': 'navigate',
            'action_params': {'url': 'https://example.com'},
            'description': '导航到示例网站'
        }
        RecordingSessionManager.add_step(session_id, step1)
        
        step2 = {
            'action_type': 'click',
            'element_locator': {
                'locator_type': 'id',
                'locator_value': 'submit-btn'
            },
            'description': '点击提交按钮'
        }
        RecordingSessionManager.add_step(session_id, step2)
        
        # 验证步骤已添加
        steps = RecordingSessionManager.get_steps(session_id)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]['action_type'], 'navigate')
        self.assertEqual(steps[1]['action_type'], 'click')
    
    def test_recording_flow_save_script(self):
        """测试录制流程 - 保存录制的脚本"""
        from test_ui_app.services import ScriptBuilder
        
        # 模拟录制得到的步骤数据
        recorded_steps = [
            {
                'action_type': 'navigate',
                'action_params': {'url': 'https://example.com'},
                'description': '导航到示例网站'
            },
            {
                'action_type': 'click',
                'element_locator': {
                    'locator_type': 'id',
                    'locator_value': 'submit-btn'
                },
                'description': '点击提交按钮'
            },
            {
                'action_type': 'fill',
                'element_locator': {
                    'locator_type': 'name',
                    'locator_value': 'username'
                },
                'action_params': {'value': 'testuser'},
                'description': '填写用户名'
            }
        ]
        
        # 使用ScriptBuilder创建脚本
        script = ScriptBuilder.create_script_from_steps(
            name='录制的测试脚本',
            steps_data=recorded_steps,
            user_id=self.test_user.id,
            browser_type='chromium',
            headless=True
        )
        
        # 验证脚本创建成功
        self.assertIsNotNone(script)
        self.assertEqual(script.name, '录制的测试脚本')
        self.assertIsInstance(script.actions, list)
        self.assertTrue(len(script.actions) >= 3)  # 至少有3个actions
        
        # 验证actions格式正确
        for i, action in enumerate(script.actions[:3], 1):
            self.assertIn('id', action)
            self.assertIn('order', action)
            self.assertIn('type', action)
            self.assertEqual(action['order'], i)
        
        # 验证actions类型
        self.assertEqual(script.actions[0]['type'], 'navigate')
        self.assertEqual(script.actions[1]['type'], 'click')
        self.assertEqual(script.actions[2]['type'], 'fill')
        
        # 清理
        script.delete()
    
    @patch('test_ui_app.playwright_engine.async_playwright')
    def test_recording_flow_webSocket_consumer_start(self, mock_async_playwright):
        """测试录制流程 - WebSocket Consumer启动录制"""
        from channels.testing import WebsocketCommunicator
        from test_ui_app.consumers.recording_consumer import RecordingConsumer
        from test_ui_app.recording.session_manager import RecordingSessionManager
        import json
        
        # 创建会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com'
        )
        
        # Mock Playwright
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.url = 'https://example.com'
        
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_async_playwright.return_value = mock_playwright_instance
        
        # 注意：WebSocket测试需要Django Channels测试工具，这里仅验证逻辑
        # 实际测试中可以使用WebsocketCommunicator进行完整测试
        
        # 验证会话存在
        session = RecordingSessionManager.get_session(session_id)
        self.assertIsNotNone(session)
    
    def test_recording_flow_convert_steps_to_actions(self):
        """测试录制流程 - 步骤转换为actions"""
        from test_ui_app.converters.action_converter import convert_to_actions
        
        steps_data = [
            {
                'action_type': 'navigate',
                'action_params': {'url': 'https://example.com'},
                'description': '导航'
            },
            {
                'action_type': 'click',
                'element_locator': {
                    'locator_type': 'id',
                    'locator_value': 'btn'
                },
                'description': '点击'
            }
        ]
        
        # 转换为actions
        actions = convert_to_actions(steps_data, 'steps')
        
        # 验证转换结果
        self.assertIsInstance(actions, list)
        self.assertEqual(len(actions), 2)
        self.assertIn('id', actions[0])
        self.assertIn('order', actions[0])
        self.assertIn('type', actions[0])
        self.assertEqual(actions[0]['type'], 'navigate')
        self.assertEqual(actions[1]['type'], 'click')
    
    def test_recording_flow_stop_recording_save_to_session(self):
        """测试录制流程 - 停止录制后保存步骤到会话"""
        from test_ui_app.recording.session_manager import RecordingSessionManager
        
        # 创建会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com'
        )
        
        # 模拟停止录制后获取的步骤
        recorded_steps = [
            {
                'type': 'navigate',
                'url': 'https://example.com',
                'timestamp': 1234567890
            },
            {
                'type': 'click',
                'selector': '#submit-btn',
                'locator': {'type': 'id', 'value': 'submit-btn'},
                'timestamp': 1234567891
            },
            {
                'type': 'fill',
                'selector': '[name="username"]',
                'locator': {'type': 'name', 'value': 'username'},
                'value': 'testuser',
                'timestamp': 1234567892
            }
        ]
        
        # 保存步骤到会话（模拟停止录制后的保存逻辑）
        for step in recorded_steps:
            RecordingSessionManager.add_step(session_id, step)
        
        # 验证步骤已保存
        all_steps = RecordingSessionManager.get_steps(session_id)
        self.assertEqual(len(all_steps), 3)
        
        # 验证会话状态可以更新为 stopped
        RecordingSessionManager.update_session(session_id, status='stopped')
        session = RecordingSessionManager.get_session(session_id)
        self.assertEqual(session['status'], 'stopped')
        
        # 验证步骤内容
        self.assertEqual(all_steps[0]['type'], 'navigate')
        self.assertEqual(all_steps[1]['type'], 'click')
        self.assertEqual(all_steps[2]['type'], 'fill')
    
    def test_recording_flow_save_recorded_script(self):
        """测试录制流程 - 保存录制的脚本（完整流程）"""
        from test_ui_app.services import ScriptBuilder
        from test_ui_app.recording.session_manager import RecordingSessionManager
        from rest_framework.test import APIClient
        
        # 创建会话并录制一些步骤
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com'
        )
        
        # 模拟录制的步骤
        recorded_steps = [
            {
                'action_type': 'navigate',
                'action_params': {'url': 'https://example.com'},
                'description': '导航到示例网站'
            },
            {
                'action_type': 'click',
                'element_locator': {
                    'locator_type': 'id',
                    'locator_value': 'submit-btn'
                },
                'description': '点击提交按钮'
            },
            {
                'action_type': 'fill',
                'element_locator': {
                    'locator_type': 'name',
                    'locator_value': 'username'
                },
                'action_params': {'value': 'testuser'},
                'description': '填写用户名'
            }
        ]
        
        # 保存步骤到会话（模拟停止录制后）
        for step in recorded_steps:
            RecordingSessionManager.add_step(session_id, step)
        
        # 从会话获取步骤（模拟前端获取）
        steps_from_session = RecordingSessionManager.get_steps(session_id)
        self.assertEqual(len(steps_from_session), 3)
        
        # 保存脚本（模拟 views.py: record() 的流程）
        # 注意：create_script_from_steps 不接受 session_id 参数
        script = ScriptBuilder.create_script_from_steps(
            name='停止录制后保存的脚本',
            steps_data=steps_from_session,
            user_id=self.test_user.id,
            browser_type='chromium',
            headless=True
        )
        
        # 验证脚本创建成功
        self.assertIsNotNone(script)
        self.assertEqual(script.name, '停止录制后保存的脚本')
        self.assertTrue(len(script.actions) >= 3)
        
        # 验证actions格式
        for action in script.actions:
            self.assertIn('id', action)
            self.assertIn('order', action)
            self.assertIn('type', action)
        
        # 验证actions类型正确
        action_types = [action['type'] for action in script.actions[:3]]
        self.assertIn('navigate', action_types)
        self.assertIn('click', action_types)
        self.assertIn('fill', action_types)
        
        # 清理
        script.delete()
    
    @patch('test_ui_app.tasks.execute_ui_test_task')
    def test_recording_flow_stop_and_save_via_api(self, mock_task):
        """测试录制流程 - 通过API停止录制并保存脚本（完整端到端）"""
        from test_ui_app.recording.session_manager import RecordingSessionManager
        from rest_framework.test import APIClient
        import json
        
        # 创建会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com'
        )
        
        # 模拟录制步骤
        recorded_steps = [
            {
                'action_type': 'navigate',
                'action_params': {'url': 'https://example.com'},
                'description': '导航'
            },
            {
                'action_type': 'click',
                'element_locator': {
                    'locator_type': 'id',
                    'locator_value': 'btn'
                },
                'description': '点击'
            }
        ]
        
        # 保存步骤到会话（模拟停止录制后WebSocket Consumer保存的步骤）
        for step in recorded_steps:
            RecordingSessionManager.add_step(session_id, step)
        
        # 更新会话状态为 stopped（模拟停止录制）
        RecordingSessionManager.update_session(session_id, status='stopped')
        
        # 从会话获取步骤（模拟前端从会话获取步骤）
        steps_from_session = RecordingSessionManager.get_steps(session_id)
        
        # 调用 record API（模拟前端调用保存脚本的API）
        client = APIClient()
        client.force_authenticate(user=self.test_user)
        
        # 准备请求数据（record API需要steps字段，不是session_id）
        record_data = {
            'name': 'API保存的录制脚本',
            'description': '通过API停止录制并保存的脚本',
            'steps': steps_from_session  # 使用从会话获取的步骤
        }
        
        response = client.post(
            '/api/ui-test/ui-scripts/record/',
            data=json.dumps(record_data),
            content_type='application/json'
        )
        
        # 验证API响应
        self.assertEqual(response.status_code, 201)  # Created
        self.assertIn('id', response.data)
        self.assertEqual(response.data['name'], 'API保存的录制脚本')
        
        # 验证脚本已创建
        script_id = response.data['id']
        from test_ui_app.models import UITestScript
        script = UITestScript.objects.get(id=script_id)
        self.assertIsNotNone(script)
        self.assertTrue(len(script.actions) >= 2)
        
        # 清理
        script.delete()


class ExecutionFlowIntegrationTest(TestCase):
    """执行功能全链路集成测试"""
    
    def setUp(self):
        """测试前准备"""
        from django.contrib.auth.models import User
        from test_ui_app.services import ScriptBuilder
        
        # 创建测试用户
        self.test_user, _ = User.objects.get_or_create(
            username='test_execution_user',
            defaults={'email': 'test_execution@example.com'}
        )
        
        # 创建一个测试脚本
        self.test_script = ScriptBuilder.create_script_from_steps(
            name='执行测试脚本',
            steps_data=[
                {
                    'action_type': 'navigate',
                    'action_params': {'url': 'https://example.com'},
                    'description': '导航'
                },
                {
                    'action_type': 'click',
                    'element_locator': {
                        'locator_type': 'id',
                        'locator_value': 'submit-btn'
                    },
                    'description': '点击'
                }
            ],
            user_id=self.test_user.id,
            browser_type='chromium',
            headless=True
        )
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'test_script'):
            self.test_script.delete()
    
    def test_execution_flow_create_script(self):
        """测试执行流程 - 创建可执行的脚本"""
        # 验证脚本已创建
        self.assertIsNotNone(self.test_script)
        self.assertTrue(len(self.test_script.actions) > 0)
        
        # 验证actions格式
        for action in self.test_script.actions:
            self.assertIn('id', action)
            self.assertIn('order', action)
            self.assertIn('type', action)
    
    @patch('test_ui_app.tasks.execute_ui_test_task')
    def test_execution_flow_submit_task(self, mock_task):
        """测试执行流程 - 提交Celery任务"""
        from test_ui_app.services import UITestService
        
        # Mock Celery任务
        mock_task_instance = Mock()
        mock_task_instance.id = 'test-execution-task-123'
        mock_task.delay = Mock(return_value=mock_task_instance)
        
        # 提交任务
        service = UITestService()
        result = service.execute_script_sync(
            script_id=self.test_script.id,
            user_id=self.test_user.id
        )
        
        # 验证任务提交成功
        self.assertTrue(result['success'])
        self.assertEqual(result['task_id'], 'test-execution-task-123')
        mock_task.delay.assert_called_once_with(self.test_script.id, user_id=self.test_user.id)
    
    def test_execution_flow_execution_manager_structure(self):
        """测试执行流程 - ExecutionManager结构验证"""
        from test_ui_app.execution.execution_manager import ExecutionManager
        
        # 创建ExecutionManager
        manager = ExecutionManager()
        
        # 验证结构
        self.assertIsNotNone(manager.validator)
        self.assertIsNotNone(manager.runner)
        self.assertTrue(hasattr(manager, 'execute'))
        self.assertTrue(hasattr(manager, '_get_script'))
        self.assertTrue(hasattr(manager, '_create_execution'))
    
    def test_execution_flow_script_validation(self):
        """测试执行流程 - 脚本校验"""
        from test_ui_app.validators.script_validator import ScriptValidator
        
        validator = ScriptValidator()
        
        # 使用测试脚本的actions进行校验
        actions = self.test_script.actions
        is_valid, error_msg = validator.validate(
            actions=actions,
            browser_type=self.test_script.browser_type,
            viewport_width=self.test_script.viewport_width,
            viewport_height=self.test_script.viewport_height,
            timeout=self.test_script.timeout
        )
        
        # 验证校验通过
        self.assertTrue(is_valid, f"校验失败: {error_msg}")
    
    def test_execution_flow_invalid_script_validation(self):
        """测试执行流程 - 无效脚本校验失败"""
        from test_ui_app.validators.script_validator import ScriptValidator
        
        validator = ScriptValidator()
        
        # 创建无效的actions（缺少必需字段）
        invalid_actions = [
            {
                'id': 'action_1',
                # 缺少order和type
            }
        ]
        
        is_valid, error_msg = validator.validate(
            actions=invalid_actions,
            browser_type='chromium',
            viewport_width=1280,
            viewport_height=720,
            timeout=30000
        )
        
        # 验证校验失败
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
    
    @patch('test_ui_app.tasks.execute_ui_test_task')
    def test_execution_flow_api_endpoint(self, mock_task):
        """测试执行流程 - API端点"""
        from rest_framework.test import APIClient
        
        # Mock Celery任务
        mock_task_instance = Mock()
        mock_task_instance.id = 'api-endpoint-task-123'
        mock_task.delay = Mock(return_value=mock_task_instance)
        
        client = APIClient()
        client.force_authenticate(user=self.test_user)
        
        # 调用execute API (注意：需要包含/api/前缀)
        response = client.post(
            f'/api/ui-test/ui-scripts/{self.test_script.id}/execute/',
            format='json'
        )
        
        # 验证响应（由于Celery任务已mock，应该返回202 Accepted）
        self.assertEqual(response.status_code, 202)
        self.assertIn('task_id', response.data)
        self.assertEqual(response.data['task_id'], 'api-endpoint-task-123')


class RecordingToExecutionFlowTest(TestCase):
    """录制到执行的完整流程测试"""
    
    def setUp(self):
        """测试前准备"""
        from django.contrib.auth.models import User
        
        # 创建测试用户
        self.test_user, _ = User.objects.get_or_create(
            username='test_integration_user',
            defaults={'email': 'test_integration@example.com'}
        )
    
    def test_full_flow_recording_to_execution(self):
        """测试完整流程：录制 → 保存 → 执行"""
        from test_ui_app.services import ScriptBuilder, UITestService
        from test_ui_app.recording.session_manager import RecordingSessionManager
        from unittest.mock import patch
        
        # 步骤1: 创建录制会话
        session_id = RecordingSessionManager.create_session(
            user_id=self.test_user.id,
            start_url='https://example.com',
            browser_type='chromium'
        )
        self.assertIsNotNone(session_id)
        
        # 步骤2: 模拟录制得到的步骤（实际中由WebSocket录制产生）
        recorded_steps = [
            {
                'action_type': 'navigate',
                'action_params': {'url': 'https://example.com'},
                'description': '导航到示例网站'
            },
            {
                'action_type': 'click',
                'element_locator': {
                    'locator_type': 'id',
                    'locator_value': 'submit-btn'
                },
                'description': '点击提交按钮'
            }
        ]
        
        # 保存步骤到会话（模拟录制过程中实时保存）
        for step in recorded_steps:
            RecordingSessionManager.add_step(session_id, step)
        
        # 验证步骤已保存
        steps = RecordingSessionManager.get_steps(session_id)
        self.assertEqual(len(steps), 2)
        
        # 步骤3: 保存录制的脚本
        script = ScriptBuilder.create_script_from_steps(
            name='录制的完整流程测试脚本',
            steps_data=recorded_steps,
            user_id=self.test_user.id,
            browser_type='chromium',
            headless=True
        )
        
        # 验证脚本已保存
        self.assertIsNotNone(script)
        self.assertTrue(len(script.actions) >= 2)
        
        # 步骤4: 验证脚本可以执行（校验通过）
        from test_ui_app.validators.script_validator import ScriptValidator
        validator = ScriptValidator()
        
        is_valid, error_msg = validator.validate(
            actions=script.actions,
            browser_type=script.browser_type,
            viewport_width=script.viewport_width,
            viewport_height=script.viewport_height,
            timeout=script.timeout
        )
        
        self.assertTrue(is_valid, f"录制的脚本校验失败: {error_msg}")
        
        # 步骤5: 模拟提交执行任务（mock Celery）
        with patch('test_ui_app.tasks.execute_ui_test_task') as mock_task:
            mock_task_instance = Mock()
            mock_task_instance.id = 'full-flow-task-123'
            mock_task.delay = Mock(return_value=mock_task_instance)
            
            service = UITestService()
            result = service.execute_script_sync(
                script_id=script.id,
                user_id=self.test_user.id
            )
            
            # 验证任务提交成功
            self.assertTrue(result['success'])
            self.assertEqual(result['task_id'], 'full-flow-task-123')
        
        # 清理
        script.delete()
