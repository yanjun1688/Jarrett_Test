"""
Test planning API views
"""
from __future__ import annotations
from typing import Any
from rest_framework.request import Request

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging
import json
from typing import Optional, Dict, Any

from core.agents.planning.test_planning_agent import TestPlanningAgent
from core.flow.flow_ir import FlowIR
from shared.exceptions import ValidationError, PlanningError
from shared.utils.validation import validate_required_fields

logger = logging.getLogger(__name__)


class PlanTestView(APIView):
    """
    Plan test flow from natural language description
    POST /api/v1/planning/plan
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """Plan test flow"""
        logger.info(f"[PLANNING] Plan test request from user: {request.user}")
        
        try:
            data = request.data
            description = data.get('description')
            project_id = data.get('project_id')
            test_type = data.get('test_type', 'auto')
            additional_context = data.get('additional_context', {})
            use_rag = data.get('use_rag', True)
            validate = data.get('validate', True)
            complexity = data.get('complexity', 'medium')  # low, medium, high
            
            # Validate required fields
            validate_required_fields(data, ['description'])
            
            if not description or not description.strip():
                return Response(
                    {'error': 'Description cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"[PLANNING] Planning test: {description[:100]}...")
            logger.info(f"[PLANNING] Test type: {test_type}, Complexity: {complexity}")
            
            # Direct async execution
            result = await self._async_plan(
                description=str(description) if description else "",
                project_id=int(project_id) if project_id else None,
                test_type=str(test_type),
                additional_context=dict(additional_context) if isinstance(additional_context, dict) else {},
                use_rag=bool(use_rag),
                validate=bool(validate),
                complexity=str(complexity),
                user=request.user
            )
            
            logger.info(f"[PLANNING] Planning completed: {result.get('success', False)}")
            return Response(result)
            
        except ValidationError as e:
            logger.warning(f"[PLANNING] Validation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[PLANNING] Failed to plan test: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_plan(
        self,
        description: str,
        project_id: Optional[int],
        test_type: str,
        additional_context: Dict[str, Any],
        use_rag: bool,
        validate: bool,
        complexity: str,
        user: Any
    ) -> Dict[str, Any]:
        """Async plan test flow"""
        try:
            logger.info(f"[PLANNING] Starting async planning for: {description[:50]}...")
            
            # Initialize planning agent
            agent = TestPlanningAgent(
                llm_service=None,  # Would be injected in production
                rag_retriever=None if not use_rag else None,  # type: ignore[call-arg]  # Would be injected
                config={
                    'project_id': project_id,
                    'test_type': test_type,
                    'complexity': complexity,
                    'timeout': 60
                }
            )
            
            # Plan test flow
            planning_result = await agent.plan_test(  # type: ignore[attr-defined]
                description=description,
                additional_context=additional_context,
                validate=validate
            )
            
            if not planning_result.get('success', False):
                raise PlanningError(planning_result.get('error', 'Planning failed'))
            
            # Extract FlowIR from result
            flow_ir_dict = planning_result.get('flow_ir')
            if not flow_ir_dict:
                raise PlanningError('No flow generated')
            
            # Create FlowIR object for validation
            flow_ir = FlowIR.from_dict(flow_ir_dict)
            
            # Validate flow if requested
            validation_result = None
            if validate:
                validation_result = flow_ir.validate()
            
            # Calculate statistics
            statistics = {
                'nodes_count': len(flow_ir.nodes),
                'edges_count': len(flow_ir.edges),  # type: ignore[attr-defined]
                'has_cycles': flow_ir.has_cycles(),  # type: ignore[attr-defined]
                'categories': self._count_node_categories(flow_ir)
            }
            
            # Build response
            result = {
                'success': True,
                'flow_ir': flow_ir_dict,
                'validation': validation_result,
                'statistics': statistics,
                'planning_metadata': {
                    'description': description,
                    'test_type': test_type,
                    'complexity': complexity,
                    'planning_time': planning_result.get('execution_time', 0),
                    'agent_version': planning_result.get('agent_version', '1.0.0')
                }
            }
            
            logger.info(f"[PLANNING] Planning successful: {statistics['nodes_count']} nodes")
            return result
            
        except PlanningError as e:
            logger.error(f"[PLANNING] Planning error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'description': description,
                'test_type': test_type
            }
        except Exception as e:
            logger.error(f"[PLANNING] Async planning failed: {str(e)}")
            return {
                'success': False,
                'error': 'Planning failed',
                'description': description,
                'test_type': test_type
            }
    
    def _count_node_categories(self, flow_ir: FlowIR) -> Dict[str, int]:
        """Count node categories in flow"""
        categories: dict[str, int] = {}
        
        for node in flow_ir.nodes.values():
            node_type = node.get('type', 'unknown')  # type: ignore[attr-defined]
            # Extract category from node type (e.g., 'api_test' -> 'api')
            category = node_type.split('_')[0] if '_' in node_type else 'general'
            categories[category] = categories.get(category, 0) + 1
        
        return categories


class RefinePlanView(APIView):
    """
    Refine existing test plan
    POST /api/v1/planning/refine
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """Refine test plan"""
        logger.info(f"[PLANNING] Refine plan request from user: {request.user}")
        
        try:
            data = request.data
            flow_ir = data.get('flow_ir')
            feedback = data.get('feedback')
            refinement_type = data.get('refinement_type', 'general')
            constraints = data.get('constraints', {})
            
            # Validate required fields
            validate_required_fields(data, ['flow_ir', 'feedback'])
            
            if not isinstance(flow_ir, dict):
                return Response(
                    {'error': 'flow_ir must be a dictionary'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not feedback or not feedback.strip():
                return Response(
                    {'error': 'Feedback cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"[PLANNING] Refining plan with feedback: {feedback[:100]}...")
            
            # Direct async execution
            result = await self._async_refine(
                flow_ir=flow_ir,
                feedback=str(feedback) if feedback else "",
                refinement_type=str(refinement_type),
                constraints=dict(constraints) if isinstance(constraints, dict) else {},
                user=request.user
            )
            
            logger.info(f"[PLANNING] Refinement completed: {result.get('success', False)}")
            return Response(result)
            
        except ValidationError as e:
            logger.warning(f"[PLANNING] Validation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[PLANNING] Failed to refine plan: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_refine(
        self,
        flow_ir: Dict[str, Any],
        feedback: str,
        refinement_type: str,
        constraints: Dict[str, Any],
        user: Any
    ) -> Dict[str, Any]:
        """Async refine test plan"""
        try:
            logger.info(f"[PLANNING] Starting async refinement")
            
            # Initialize planning agent
            agent = TestPlanningAgent(
                llm_service=None,  # Would be injected in production
                rag_retriever=None,  # type: ignore[call-arg]  # Would be injected
                config={
                    'refinement_type': refinement_type,
                    'timeout': 45
                }
            )
            
            # Refine plan
            flow_ir_obj = FlowIR.from_dict(flow_ir)
            refinement_result = await agent.refine_plan(
                flow_ir=flow_ir_obj,
                feedback=feedback,
                additional_context=constraints
            )
            
            if not refinement_result.get('success', False):
                raise PlanningError(refinement_result.get('error', 'Refinement failed'))
            
            # Extract refined FlowIR
            refined_flow_ir = refinement_result.get('refined_flow_ir')
            if not refined_flow_ir:
                raise PlanningError('No refined flow generated')
            
            # Create FlowIR object for validation
            flow_ir_obj = FlowIR.from_dict(refined_flow_ir)
            
            # Validate refined flow
            validation_result = flow_ir_obj.validate()
            
            # Calculate changes
            original_nodes = len(flow_ir.get('nodes', {}))
            refined_nodes = len(refined_flow_ir.get('nodes', {}))
            
            changes = {
                'nodes_added': max(0, refined_nodes - original_nodes),
                'nodes_removed': max(0, original_nodes - refined_nodes),
                'nodes_modified': refinement_result.get('nodes_modified', 0),
                'total_changes': refinement_result.get('total_changes', 0)
            }
            
            # Build response
            result = {
                'success': True,
                'original_flow_ir': flow_ir,
                'refined_flow_ir': refined_flow_ir,
                'validation': validation_result,
                'changes': changes,
                'refinement_metadata': {
                    'feedback': feedback,
                    'refinement_type': refinement_type,
                    'refinement_time': refinement_result.get('execution_time', 0),
                    'constraints_applied': list(constraints.keys()) if constraints else []
                }
            }
            
            logger.info(f"[PLANNING] Refinement successful: {changes['total_changes']} changes")
            return result
            
        except PlanningError as e:
            logger.error(f"[PLANNING] Refinement error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'feedback': feedback,
                'refinement_type': refinement_type
            }
        except Exception as e:
            logger.error(f"[PLANNING] Async refinement failed: {str(e)}")
            return {
                'success': False,
                'error': 'Refinement failed',
                'feedback': feedback,
                'refinement_type': refinement_type
            }