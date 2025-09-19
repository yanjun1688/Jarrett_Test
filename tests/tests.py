from django.test import TestCase
from django.contrib.auth.models import User
from .models import Project, Module, TestCase as TestModel, TestExecution


class ProjectModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name='测试项目',
            description='这是一个测试项目'
        )
    
    def test_project_creation(self):
        self.assertEqual(self.project.name, '测试项目')
        self.assertEqual(self.project.description, '这是一个测试项目')
        self.assertTrue(self.project.is_active)
    
    def test_project_str(self):
        self.assertEqual(str(self.project), '测试项目')


class ModuleModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='测试项目')
        self.module = Module.objects.create(
            project=self.project,
            name='登录模块',
            description='处理用户登录功能'
        )
    
    def test_module_creation(self):
        self.assertEqual(self.module.project, self.project)
        self.assertEqual(self.module.name, '登录模块')
        self.assertEqual(self.module.description, '处理用户登录功能')
    
    def test_module_str(self):
        expected = '测试项目 - 登录模块'
        self.assertEqual(str(self.module), expected)


class TestCaseModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.project = Project.objects.create(name='测试项目')
        self.module = Module.objects.create(project=self.project, name='登录模块')
        self.testcase = TestModel.objects.create(
            title='测试登录功能',
            project=self.project,
            module=self.module,
            priority='high',
            precondition='用户已注册',
            steps='1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮',
            expected_result='登录成功，跳转到首页',
            created_by=self.user
        )
    
    def test_testcase_creation(self):
        self.assertEqual(self.testcase.title, '测试登录功能')
        self.assertEqual(self.testcase.project, self.project)
        self.assertEqual(self.testcase.module, self.module)
        self.assertEqual(self.testcase.priority, 'high')
        self.assertEqual(self.testcase.precondition, '用户已注册')
        self.assertEqual(self.testcase.steps, '1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮')
        self.assertEqual(self.testcase.expected_result, '登录成功，跳转到首页')
        self.assertEqual(self.testcase.created_by, self.user)
    
    def test_testcase_str(self):
        self.assertEqual(str(self.testcase), '测试登录功能')


class TestExecutionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.project = Project.objects.create(name='测试项目')
        self.module = Module.objects.create(project=self.project, name='登录模块')
        self.testcase = TestModel.objects.create(
            title='测试登录功能',
            project=self.project,
            module=self.module,
            steps='1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮',
            expected_result='登录成功，跳转到首页'
        )
        self.execution = TestExecution.objects.create(
            testcase=self.testcase,
            executor=self.user,
            status='passed',
            actual_result='登录成功',
            comments='测试通过'
        )
    
    def test_execution_creation(self):
        self.assertEqual(self.execution.testcase, self.testcase)
        self.assertEqual(self.execution.executor, self.user)
        self.assertEqual(self.execution.status, 'passed')
        self.assertEqual(self.execution.actual_result, '登录成功')
        self.assertEqual(self.execution.comments, '测试通过')
    
    def test_execution_str(self):
        expected = '测试登录功能 - 通过'
        self.assertEqual(str(self.execution), expected)
