"""
Test Planning Agent - Unified Planning Agent

This module provides the unified TestPlanningAgent for all test planning operations.
This is the recommended entry point for all test planning operations.
"""
from typing import Optional, Dict, Any, List
import uuid

from shared.exceptions import PlanningError, ValidationError
from shared.utils.logging_utils import get_logger, log_execution_time
from shared.utils.async_utils import with_timeout, retry_async
from shared.constants import TestType, TimeConstants
from core.config import get_settings

from ...flow.flow_ir import FlowIR, FlowNodeIR
from ..base_agent import BaseAgent
from ..rag.knowledge_rag_agent import KnowledgeRAGAgent

logger = get_logger(__name__)


class TestPlanningAgent(BaseAgent):
    """
    Unified Test Planning Agent

    This agent provides unified planning for all test types:
    - UI tests
    - API tests  
    - Integration tests
    - Auto-detection of test type

    Responsibilities:
    - Parse natural language test requirements
    - Generate FlowIR with proper structure
    - Validate FlowIR structure
    - Support multiple test types
    - Provide planning statistics
    """

    DEFAULT_CONFIG = {
        "default_test_type": TestType.AUTO,
        "use_rag": True,
        "validate_output": True,
        "timeout": 60,
        "max_retries": 3
    }

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        llm_service: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        knowledge_rag_agent: Optional[KnowledgeRAGAgent] = None
    ):
        """
        Initialize Test Planning Agent

        Args:
            agent_id: Agent unique identifier
            config: Agent configuration
            llm_service: LLM service for planning
            rag_service: RAG service for context retrieval
            knowledge_rag_agent: Knowledge RAG Agent for enhanced retrieval
        """
        # 合并配置
        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(agent_id, merged_config)
        
        # 服务依赖
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.knowledge_rag_agent = knowledge_rag_agent
        
        # 统计
        self._planning_stats = {
            "total_plans": 0,
            "successful_plans": 0,
            "failed_plans": 0,
            "ui_plans": 0,
            "api_plans": 0,
            "integration_plans": 0,
            "auto_detected_plans": 0,
            "average_planning_time": 0.0
        }
        
        logger.info(f"初始化TestPlanningAgent: {self.agent_id}")
    
    def get_planning_stats(self) -> Dict[str, Any]:
        """获取规划统计信息"""
        return self._planning_stats.copy()

    async def initialize(self) -> None:
        """初始化Agent"""
        try:
            # 初始化LLM服务
            if self.llm_service and hasattr(self.llm_service, 'initialize'):
                await self.llm_service.initialize()
            
            # 初始化RAG服务
            if self.rag_service and hasattr(self.rag_service, 'initialize'):
                await self.rag_service.initialize()
            
            self.update_state("ready")
            logger.info(f"TestPlanningAgent已就绪: {self.agent_id}")
            
        except Exception as e:
            self.update_state("error", initialization_error=str(e))
            logger.error(f"TestPlanningAgent初始化失败: {self.agent_id}, 错误: {str(e)}")
            raise PlanningError(f"Agent初始化失败: {str(e)}")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行测试规划
        
        Args:
            input_data: 输入数据，必须包含description字段
            
        Returns:
            规划结果，包含FlowIR和验证信息
        """
        # 验证输入
        validation_errors = self.validate_planning_input(input_data)
        if validation_errors:
            raise ValidationError("输入验证失败", details={"errors": validation_errors})
        
        # 提取参数
        description = input_data["description"]
        test_type = input_data.get("test_type", self.config["default_test_type"])
        additional_context = input_data.get("additional_context", {})
        use_rag = input_data.get("use_rag", self.config["use_rag"])
        
        # 执行规划
        result: Dict[str, Any] = await self.plan(
            description=description,
            test_type=test_type,
            additional_context=additional_context,
            use_rag=use_rag
        )
        
        return result

    @log_execution_time()
    @with_timeout(TimeConstants.DEFAULT_EXECUTION_TIMEOUT)
    async def plan(
        self,
        description: str,
        test_type: str = TestType.AUTO,
        additional_context: Optional[Dict[str, Any]] = None,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        规划测试流程
        
        Args:
            description: 测试场景的自然语言描述
            test_type: 测试类型 (ui, api, integration, auto)
            additional_context: 额外的上下文信息
            use_rag: 是否使用RAG检索上下文
            
        Returns:
            规划结果字典
        """
        # 验证参数
        if not description or not description.strip():
            raise ValidationError("描述不能为空")
        
        if test_type not in TestType.ALL:
            raise ValidationError(f"无效的测试类型: {test_type}")
        
        # 自动检测测试类型
        if test_type == TestType.AUTO:
            test_type = await self._detect_test_type(description)
            self._planning_stats["auto_detected_plans"] += 1
        
        # 更新统计
        self._update_planning_stats(test_type)
        
        logger.info(f"开始规划测试: 类型={test_type}, 描述长度={len(description)}")
        
        try:
            # 使用RAG检索上下文（如果启用）
            # 优先使用KnowledgeRAGAgent，其次使用基础RAG服务
            rag_context = {}
            use_rag_enabled = use_rag and (self.knowledge_rag_agent or self.rag_service)
            if use_rag_enabled:
                rag_context = await self._retrieve_rag_context(description, test_type, additional_context)
                logger.info(f"RAG上下文检索: 类型={rag_context.get('retrieval_type', 'none')}, "
                          f"文档数={rag_context.get('document_count', rag_context.get('count', 0))}")
            
            # 合并上下文
            context = {
                "description": description,
                "test_type": test_type,
                "additional_context": additional_context or {},
                "rag_context": rag_context
            }
            
            # 生成FlowIR
            flow_ir = await self._generate_flow_ir(context)
            
            # 验证FlowIR
            validation = flow_ir.validate(strict=True)
            
            # 构建结果
            result = {
                "success": True,
                "flow_ir": flow_ir.to_dict(),
                "validation": validation,
                "test_type": test_type,
                "planning_stats": self._planning_stats.copy(),
                "agent_id": self.agent_id
            }
            
            self._planning_stats["successful_plans"] += 1
            logger.info(f"测试规划成功: 生成{len(flow_ir.nodes)}个节点")
            
            return result
            
        except Exception as e:
            self._planning_stats["failed_plans"] += 1
            logger.error(f"测试规划失败: {str(e)}", exc_info=True)
            raise PlanningError(f"测试规划失败: {str(e)}", stage="planning")

    async def _detect_test_type(self, description: str) -> str:
        """
        自动检测测试类型
        
        Args:
            description: 测试描述
            
        Returns:
            检测到的测试类型
        """
        description_lower = description.lower()
        
        # 简单的关键词检测
        ui_keywords = ["ui", "界面", "页面", "按钮", "点击", "输入", "浏览器", "网页"]
        api_keywords = ["api", "接口", "请求", "响应", "http", "rest", "graphql", "端点"]
        
        ui_count = sum(1 for keyword in ui_keywords if keyword in description_lower)
        api_count = sum(1 for keyword in api_keywords if keyword in description_lower)
        
        if ui_count > api_count:
            return TestType.UI
        elif api_count > ui_count:
            return TestType.API
        else:
            # 默认使用UI测试
            return TestType.UI

    async def _retrieve_rag_context(
        self,
        description: str,
        test_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用RAG检索上下文
        
        Args:
            description: 测试描述
            test_type: 测试类型
            additional_context: 额外的上下文信息
            
        Returns:
            RAG检索结果，包含增强的上下文信息
        """
        additional_context = additional_context or {}
        
        # 优先使用KnowledgeRAGAgent进行增强检索
        if self.knowledge_rag_agent:
            return await self._retrieve_with_knowledge_agent(description, test_type, additional_context)
        
        # 回退到基础RAG服务
        if self.rag_service:
            return await self._retrieve_basic_rag(description, test_type)
        
        return {}
    
    async def _retrieve_with_knowledge_agent(
        self,
        description: str,
        test_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用KnowledgeRAGAgent进行增强检索
        
        Args:
            description: 测试描述
            test_type: 测试类型
            additional_context: 额外的上下文信息
            
        Returns:
            增强的检索结果
        """
        additional_context = additional_context or {}
        try:
            assert self.knowledge_rag_agent is not None, "knowledge_rag_agent should not be None in this context"
            
            # 根据测试类型选择文档类型
            document_type_map = {
                TestType.UI: "ui_test",
                TestType.API: "api_test",
                TestType.INTEGRATION: "integration_test"
            }
            document_type = document_type_map.get(test_type, "test_case")
            
            # 使用KnowledgeRAGAgent进行检索
            query = f"{test_type}测试: {description}"
            
            # 获取相关文档（不使用LLM生成答案，只获取文档）
            doc_result = await self.knowledge_rag_agent.query(
                query=query,
                top_k=5,
                document_type=document_type,
                use_llm=False
            )
            
            # 获取最佳实践
            best_practices = await self.knowledge_rag_agent.get_best_practices(
                topic=f"{test_type} testing",
                top_k=3
            )
            
            # 获取测试模式
            test_patterns = await self.knowledge_rag_agent.get_test_patterns(
                scenario=description,
                top_k=3
            )
            
            # 合并结果
            context_result = {
                "query": query,
                "documents": doc_result.get("documents", []),
                "document_count": len(doc_result.get("documents", [])),
                "best_practices": best_practices.get("documents", []),
                "test_patterns": test_patterns.get("documents", []),
                "retrieval_type": "knowledge_agent",
                "has_context": len(doc_result.get("documents", [])) > 0,
            }
            
            logger.info(f"KnowledgeRAG检索完成: 获取{context_result['document_count']}个文档, "
                       f"历史用例{context_result['similar_case_count']}个")
            return context_result
            
        except Exception as e:
            logger.warning(f"KnowledgeRAGAgent检索失败: {str(e)}")
            # 回退到基础RAG
            if self.rag_service:
                return await self._retrieve_basic_rag(description, test_type)
            return {}
    
    async def _retrieve_basic_rag(
        self,
        description: str,
        test_type: str
    ) -> Dict[str, Any]:
        """
        使用基础RAG服务检索上下文
        
        Args:
            description: 测试描述
            test_type: 测试类型
            
        Returns:
            基础检索结果
        """
        try:
            assert self.rag_service is not None, "rag_service should not be None in this context"
            query = f"{test_type}测试: {description}"
            
            results = await self.rag_service.retrieve(
                query=query,
                top_k=5,
                filters={"test_type": test_type}
            )
            
            return {
                "query": query,
                "results": results,
                "count": len(results),
                "retrieval_type": "basic_rag",
                "has_context": len(results) > 0
            }
            
        except Exception as e:
            logger.warning(f"RAG检索失败: {str(e)}")
            return {}

    async def _generate_flow_ir(self, context: Dict[str, Any]) -> FlowIR:
        """
        生成FlowIR
        
        Args:
            context: 规划上下文
            
        Returns:
            FlowIR对象
        """
        test_type = context["test_type"]
        description = context["description"]
        rag_context = context.get("rag_context", {})
        
        # 如果有LLM服务且有RAG上下文，使用LLM增强生成
        if self.llm_service and rag_context.get("has_context"):
            try:
                return await self._generate_flow_ir_with_llm(context)
            except Exception as e:
                logger.warning(f"LLM增强生成失败，回退到模板生成: {str(e)}")
        
        # 根据测试类型生成不同的流程
        if test_type == TestType.UI:
            return await self._generate_ui_test_flow(description, context)
        elif test_type == TestType.API:
            return await self._generate_api_test_flow(description, context)
        elif test_type == TestType.INTEGRATION:
            return await self._generate_integration_test_flow(description, context)
        else:
            raise ValidationError(f"不支持的测试类型: {test_type}")
    
    async def _generate_flow_ir_with_llm(self, context: Dict[str, Any]) -> FlowIR:
        """
        使用LLM和RAG上下文增强生成FlowIR
        
        Args:
            context: 规划上下文，包含rag_context
            
        Returns:
            FlowIR对象
        """
        test_type = context["test_type"]
        description = context["description"]
        rag_context = context.get("rag_context", {})
        
        # 构建增强提示
        system_message = self._build_flow_ir_system_message(test_type, rag_context)
        user_message = self._build_flow_ir_user_message(description, test_type, context)
        
        try:
            assert self.llm_service is not None, "llm_service should not be None in this context"
            # 调用LLM生成FlowIR结构
            response = await self.llm_service.generate(
                prompt=user_message,
                system_message=system_message
            )
            
            # 解析LLM响应为FlowIR
            flow_ir = await self._parse_llm_flow_ir_response(response, test_type, description)
            
            logger.info(f"LLM增强FlowIR生成成功: {len(flow_ir.nodes)}个节点")
            return flow_ir
            
        except Exception as e:
            logger.error(f"LLM FlowIR生成失败: {str(e)}")
            raise
    
    def _build_flow_ir_system_message(self, test_type: str, rag_context: Dict[str, Any]) -> str:
        """构建FlowIR生成的系统消息"""
        system_parts = [
            "你是一个测试流程规划专家，负责根据用户需求生成测试流程。",
            f"当前测试类型: {test_type}",
            "",
        ]
        
        # 添加最佳实践
        best_practices = rag_context.get("best_practices", [])
        if best_practices:
            system_parts.append("参考最佳实践:")
            for i, bp in enumerate(best_practices[:3], 1):
                content = bp.get("document", "")[:500]
                system_parts.append(f"{i}. {content}")
            system_parts.append("")
        
        # 添加测试模式
        test_patterns = rag_context.get("test_patterns", [])
        if test_patterns:
            system_parts.append("参考测试模式:")
            for i, tp in enumerate(test_patterns[:3], 1):
                content = tp.get("document", "")[:500]
                system_parts.append(f"{i}. {content}")
            system_parts.append("")
        
        system_parts.extend([
            "请生成符合以下JSON格式的测试流程:",
            '{"nodes": {...}, "start_node": "...", "metadata": {...}}',
            "节点类型包括: ui_navigate, ui_click, ui_input, ui_assert, api_request, api_validate等"
        ])
        
        return "\n".join(system_parts)
    
    def _build_flow_ir_user_message(self, description: str, test_type: str, context: Dict[str, Any]) -> str:
        """构建FlowIR生成的用户消息"""
        additional = context.get("additional_context", {})
        
        message_parts = [
            f"测试需求描述: {description}",
            f"测试类型: {test_type}",
        ]
        
        if additional.get("url"):
            message_parts.append(f"目标URL: {additional['url']}")
        
        if additional.get("endpoint"):
            message_parts.append(f"API端点: {additional['endpoint']}")
        
        if additional.get("method"):
            message_parts.append(f"HTTP方法: {additional['method']}")
        
        message_parts.append("请生成完整的测试流程JSON。")
        
        return "\n".join(message_parts)
    
    async def _parse_llm_flow_ir_response(
        self,
        response: str,
        test_type: str,
        description: str
    ) -> FlowIR:
        """解析LLM响应为FlowIR对象"""
        import json
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("LLM响应中未找到有效的JSON")
        
        try:
            flow_dict = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"解析LLM响应JSON失败: {e}")
        
        # 验证并构建FlowIR
        metadata = flow_dict.get("metadata", {})
        metadata["test_type"] = test_type
        metadata["description"] = description
        metadata["generated_by"] = self.agent_id
        metadata["llm_enhanced"] = True
        
        flow_ir = FlowIR(metadata=metadata)
        
        # 添加节点
        nodes = flow_dict.get("nodes", {})
        for node_id, node_data in nodes.items():
            node = FlowNodeIR(
                id=node_id,
                node_type=node_data.get("node_type", "unknown"),
                parameters=node_data.get("parameters", {}),
                depends_on=node_data.get("depends_on", []),
                on_success=node_data.get("on_success"),
                on_failure=node_data.get("on_failure"),
                metadata=node_data.get("metadata", {})
            )
            flow_ir.add_node(node)
        
        # 设置起始节点
        if flow_dict.get("start_node"):
            flow_ir.start_node = flow_dict["start_node"]
        
        return flow_ir

    async def _generate_ui_test_flow(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> FlowIR:
        """生成UI测试流程"""
        # 创建基础流程
        flow_ir = FlowIR(
            metadata={
                "name": f"UI测试: {description[:50]}...",
                "description": description,
                "test_type": TestType.UI,
                "generated_by": self.agent_id
            }
        )
        
        # 添加导航节点
        navigate_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="ui_navigate",
            parameters={
                "url": context.get("additional_context", {}).get("url", "https://example.com")
            },
            metadata={
                "name": "导航到页面",
                "description": "打开测试页面"
            }
        )
        
        # 添加操作节点
        action_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="ui_click",
            parameters={
                "selector": "button.submit",
                "wait_time": 2
            },
            depends_on=[navigate_node.id],
            metadata={
                "name": "点击提交按钮",
                "description": "点击页面上的提交按钮"
            }
        )
        
        # 添加断言节点
        assert_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="ui_assert",
            parameters={
                "selector": ".success-message",
                "expected_text": "操作成功"
            },
            depends_on=[action_node.id],
            metadata={
                "name": "验证成功消息",
                "description": "验证操作是否成功"
            }
        )
        
        # 设置节点关系
        navigate_node.on_success = action_node.id
        action_node.on_success = assert_node.id
        
        # 添加节点到流程
        flow_ir.add_node(navigate_node)
        flow_ir.add_node(action_node)
        flow_ir.add_node(assert_node)
        
        return flow_ir

    async def _generate_api_test_flow(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> FlowIR:
        """生成API测试流程"""
        # 创建基础流程
        flow_ir = FlowIR(
            metadata={
                "name": f"API测试: {description[:50]}...",
                "description": description,
                "test_type": TestType.API,
                "generated_by": self.agent_id
            }
        )
        
        # 添加API请求节点
        request_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="api_request",
            parameters={
                "method": "GET",
                "url": context.get("additional_context", {}).get("endpoint", "/api/test"),
                "headers": {"Content-Type": "application/json"}
            },
            metadata={
                "name": "发送API请求",
                "description": "发送HTTP请求到API端点"
            }
        )
        
        # 添加验证节点
        validate_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="api_validate",
            parameters={
                "status_code": 200,
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {"type": "object"}
                    },
                    "required": ["success"]
                }
            },
            depends_on=[request_node.id],
            metadata={
                "name": "验证API响应",
                "description": "验证响应状态码和数据结构"
            }
        )
        
        # 设置节点关系
        request_node.on_success = validate_node.id
        
        # 添加节点到流程
        flow_ir.add_node(request_node)
        flow_ir.add_node(validate_node)
        
        return flow_ir

    async def _generate_integration_test_flow(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> FlowIR:
        """生成集成测试流程"""
        # 创建基础流程
        flow_ir = FlowIR(
            metadata={
                "name": f"集成测试: {description[:50]}...",
                "description": description,
                "test_type": TestType.INTEGRATION,
                "generated_by": self.agent_id
            }
        )
        
        # 集成测试通常包含多个步骤
        # 这里创建一个简单的示例流程
        
        # 添加准备节点
        setup_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="setup",
            parameters={
                "environment": "test",
                "cleanup": True
            },
            metadata={
                "name": "测试环境准备",
                "description": "准备测试环境和数据"
            }
        )
        
        # 添加执行节点
        execute_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="execute",
            parameters={
                "steps": ["setup", "test", "verify"]
            },
            depends_on=[setup_node.id],
            metadata={
                "name": "执行测试步骤",
                "description": "执行集成测试的各个步骤"
            }
        )
        
        # 添加清理节点
        cleanup_node = FlowNodeIR(
            id=f"node_{uuid.uuid4().hex[:8]}",
            node_type="cleanup",
            parameters={
                "remove_data": True,
                "close_connections": True
            },
            depends_on=[execute_node.id],
            metadata={
                "name": "测试环境清理",
                "description": "清理测试环境和数据"
            }
        )
        
        # 设置节点关系
        setup_node.on_success = execute_node.id
        execute_node.on_success = cleanup_node.id
        
        # 添加节点到流程
        flow_ir.add_node(setup_node)
        flow_ir.add_node(execute_node)
        flow_ir.add_node(cleanup_node)
        
        return flow_ir

    def validate_planning_input(self, input_data: Dict[str, Any]) -> List[str]:
        """
        验证规划输入
        
        Args:
            input_data: 输入数据
            
        Returns:
            错误消息列表
        """
        errors = []
        
        # 检查必需字段
        if "description" not in input_data:
            errors.append("缺少必需字段: description")
        elif not input_data["description"] or not input_data["description"].strip():
            errors.append("description不能为空")
        
        # 检查test_type
        if "test_type" in input_data:
            test_type = input_data["test_type"]
            if test_type not in TestType.ALL:
                errors.append(f"无效的test_type: {test_type}")
        
        # 检查additional_context
        if "additional_context" in input_data:
            additional_context = input_data["additional_context"]
            if not isinstance(additional_context, dict):
                errors.append("additional_context必须是字典类型")
        
        return errors

    def _update_planning_stats(self, test_type: str) -> None:
        """更新规划统计"""
        self._planning_stats["total_plans"] += 1
        
        if test_type == TestType.UI:
            self._planning_stats["ui_plans"] += 1
        elif test_type == TestType.API:
            self._planning_stats["api_plans"] += 1
        elif test_type == TestType.INTEGRATION:
            self._planning_stats["integration_plans"] += 1

    async def refine_plan(
        self,
        flow_ir: FlowIR,
        feedback: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        优化现有规划
        
        Args:
            flow_ir: 现有的FlowIR
            feedback: 优化反馈
            additional_context: 额外的上下文
            
        Returns:
            优化后的规划结果
        """
        try:
            # 根据反馈优化流程
            # 这里可以实现具体的优化逻辑
            # 目前先返回原始流程
            optimized_ir = flow_ir.clone()
            
            # 验证优化后的流程
            validation = optimized_ir.validate(strict=True)
            
            return {
                "success": True,
                "original_flow_ir": flow_ir.to_dict(),
                "optimized_flow_ir": optimized_ir.to_dict(),
                "validation": validation,
                "feedback": feedback,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"规划优化失败: {str(e)}", exc_info=True)
            raise PlanningError(f"规划优化失败: {str(e)}", stage="refinement")

    def get_planning_statistics(self) -> Dict[str, Any]:
        """
        获取规划统计信息
        
        Returns:
            统计信息字典
        """
        stats = self._planning_stats.copy()
        
        # 计算成功率
        total = stats["total_plans"]
        successful = stats["successful_plans"]
        stats["success_rate"] = successful / total if total > 0 else 0.0
        
        return stats

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清理LLM服务
            if self.llm_service and hasattr(self.llm_service, 'cleanup'):
                await self.llm_service.cleanup()
            
            # 清理RAG服务
            if self.rag_service and hasattr(self.rag_service, 'cleanup'):
                await self.rag_service.cleanup()
            
            self.update_state("cleaned_up")
            logger.info(f"TestPlanningAgent已清理: {self.agent_id}")
            
        except Exception as e:
            logger.error(f"TestPlanningAgent清理失败: {self.agent_id}, 错误: {str(e)}")

    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力描述"""
        base_capabilities = super().get_capabilities()
        
        capabilities = {
            **base_capabilities,
            "planning_types": TestType.ALL,
            "supports_rag": self.rag_service is not None,
            "supports_knowledge_rag": self.knowledge_rag_agent is not None,
            "supports_llm": self.llm_service is not None,
            "supports_refinement": True,
            "max_nodes_per_flow": 50,
            "available_node_types": ["ui_navigate", "ui_click", "ui_input", "ui_assert", "api_request", "api_validate"]
        }
        
        return capabilities