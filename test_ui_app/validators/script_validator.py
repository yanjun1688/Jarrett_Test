"""
脚本校验器 - 校验actions数组和脚本配置
"""
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """校验错误"""
    pass


class ScriptValidator:
    """脚本校验器"""
    
    # 必需字段
    REQUIRED_ACTION_FIELDS = ['id', 'order', 'type']
    
    # 支持的action类型
    SUPPORTED_ACTION_TYPES = [
        'navigate', 'click', 'fill', 'select', 'hover',
        'wait', 'screenshot', 'assert', 'extract', 'custom'
    ]
    
    # 需要selector的action类型
    ACTIONS_REQUIRING_SELECTOR = ['click', 'fill', 'select', 'hover', 'assert', 'extract']
    
    # 支持的选择器类型
    SUPPORTED_SELECTOR_TYPES = [
        'id', 'name', 'css', 'xpath', 'text', 'testid', 'role', 'label'
    ]
    
    # 支持的浏览器类型
    SUPPORTED_BROWSER_TYPES = ['chromium', 'firefox', 'webkit']
    
    def validate(self, actions: List[Dict[str, Any]], 
                 browser_type: str = 'chromium',
                 viewport_width: int = 1280,
                 viewport_height: int = 720,
                 timeout: int = 30000) -> Tuple[bool, Optional[str]]:
        """
        校验脚本
        
        Args:
            actions: actions列表
            browser_type: 浏览器类型
            viewport_width: 视口宽度
            viewport_height: 视口高度
            timeout: 超时时间
            
        Returns:
            Tuple[bool, Optional[str]]: (是否通过, 错误信息)
        """
        try:
            # 1. 校验actions数组
            self._validate_actions_list(actions)
            
            # 2. 校验每个action
            for action in actions:
                self._validate_action(action)
            
            # 3. 校验浏览器配置
            self._validate_browser_config(browser_type, viewport_width, viewport_height, timeout)
            
            # 4. 校验action顺序
            self._validate_action_order(actions)
            
            return True, None
            
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"校验过程中发生错误: {str(e)}", exc_info=True)
            return False, f"校验失败: {str(e)}"
    
    def _validate_actions_list(self, actions: List[Dict[str, Any]]):
        """校验actions列表"""
        if not isinstance(actions, list):
            raise ValidationError("actions必须是列表类型")
        
        if len(actions) == 0:
            raise ValidationError("actions列表不能为空")
        
        # 检查是否有重复的id或order
        ids = set()
        orders = set()
        
        for action in actions:
            action_id = action.get('id')
            order = action.get('order')
            
            if action_id and action_id in ids:
                raise ValidationError(f"发现重复的action id: {action_id}")
            if action_id:
                ids.add(action_id)
            
            if order and order in orders:
                raise ValidationError(f"发现重复的action order: {order}")
            if order:
                orders.add(order)
    
    def _validate_action(self, action: Dict[str, Any]):
        """校验单个action"""
        if not isinstance(action, dict):
            raise ValidationError(f"action必须是字典类型，实际类型: {type(action)}")
        
        # 检查必需字段
        for field in self.REQUIRED_ACTION_FIELDS:
            if field not in action:
                raise ValidationError(f"action缺少必需字段: {field}")
        
        # 校验action类型
        action_type = action.get('type')
        if action_type not in self.SUPPORTED_ACTION_TYPES:
            raise ValidationError(
                f"不支持的action类型: {action_type}，"
                f"支持的类型: {', '.join(self.SUPPORTED_ACTION_TYPES)}"
            )
        
        # 校验order
        order = action.get('order')
        if not isinstance(order, int) or order < 1:
            raise ValidationError(f"action的order必须是大于0的整数，当前值: {order}")
        
        # 校验params - 放宽要求，如果为None或缺失，后续会自动处理为字典
        params = action.get('params')
        if params is not None and not isinstance(params, dict):
            raise ValidationError(f"action的params必须是字典类型，当前类型: {type(params)}")
        
        # 校验selector
        if action_type in self.ACTIONS_REQUIRING_SELECTOR:
            selector = action.get('selector')
            # 放宽检查：selector可以是字符串或字典
            # 如果是空字符串或None，才报错
            if not selector or (isinstance(selector, str) and not selector.strip()):
                # 添加调试日志
                logger.warning(f"Action '{action_type}' 缺少有效的selector, action={action}")
                raise ValidationError(f"action类型'{action_type}'需要选择器(selector)")
            
            # 支持字典格式或简单的字符串格式
            if isinstance(selector, str):
                # 字符串格式合法
                pass
            elif isinstance(selector, dict):
                # 字典格式进行深入校验
                self._validate_selector(selector)
            else:
                raise ValidationError(f"不支持的选择器格式: {type(selector)}")
        elif action_type == 'navigate':
            # navigate需要url参数，放宽到既可以检查params也可以检查主对象（兼容录制模式）
            url = (params or {}).get('url') or action.get('url')
            if not url:
                raise ValidationError("navigate类型的action需要在params或对象主字段中提供url")
        
        # 类型特定的校验 - 仅作为建议，不强制阻塞
        try:
            self._validate_action_specific(action_type, action)
        except ValidationError as e:
            logger.warning(f"Action特定校验未通过(不阻塞): {str(e)}")
    
    def _validate_selector(self, selector: Dict[str, str]):
        """校验selector"""
        if not isinstance(selector, dict):
            raise ValidationError("selector必须是字典类型")
        
        selector_type = selector.get('type')
        selector_value = selector.get('value')
        
        if not selector_type:
            raise ValidationError("selector缺少type字段")
        
        if selector_type not in self.SUPPORTED_SELECTOR_TYPES:
            raise ValidationError(
                f"不支持的选择器类型: {selector_type}，"
                f"支持的类型: {', '.join(self.SUPPORTED_SELECTOR_TYPES)}"
            )
        
        if not selector_value:
            raise ValidationError("selector缺少value字段")
        
        if not isinstance(selector_value, str):
            raise ValidationError("selector的value必须是字符串类型")
    
    def _validate_action_specific(self, action_type: str, action: Dict[str, Any]):
        """类型特定的校验"""
        params = action.get('params', {})
        
        if action_type == 'fill':
            if 'value' not in params:
                raise ValidationError("fill类型的action需要在params中提供value")
        
        elif action_type == 'select':
            if 'value' not in params:
                raise ValidationError("select类型的action需要在params中提供value")
        
        elif action_type == 'wait':
            wait_type = params.get('type', 'timeout')
            if wait_type == 'timeout' and 'timeout' not in params:
                raise ValidationError("wait类型为timeout时，需要在params中提供timeout")
            elif wait_type == 'selector' and 'selector' not in params:
                raise ValidationError("wait类型为selector时，需要在params中提供selector")
        
        # 注意：MVP版本暂不支持assert、extract、screenshot等复杂操作
        # 这些类型在ActionRunner中会返回"不支持的操作类型"错误
        # 如果要支持这些类型，需要在校验器和ActionRunner中添加相应实现
    
    def _validate_browser_config(self, browser_type: str, viewport_width: int,
                                 viewport_height: int, timeout: int):
        """校验浏览器配置"""
        if browser_type not in self.SUPPORTED_BROWSER_TYPES:
            raise ValidationError(
                f"不支持的浏览器类型: {browser_type}，"
                f"支持的类型: {', '.join(self.SUPPORTED_BROWSER_TYPES)}"
            )
        
        if not isinstance(viewport_width, int) or viewport_width < 1:
            raise ValidationError(f"viewport_width必须是大于0的整数，当前值: {viewport_width}")
        
        if not isinstance(viewport_height, int) or viewport_height < 1:
            raise ValidationError(f"viewport_height必须是大于0的整数，当前值: {viewport_height}")
        
        if not isinstance(timeout, int) or timeout < 1:
            raise ValidationError(f"timeout必须是大于0的整数，当前值: {timeout}")
    
    def _validate_action_order(self, actions: List[Dict[str, Any]]):
        """校验action顺序"""
        orders = [action.get('order') for action in actions if action.get('order')]
        if orders:
            sorted_orders = sorted(orders)
            expected_orders = list(range(1, len(orders) + 1))
            if sorted_orders != expected_orders:
                raise ValidationError(
                    f"action的order不连续，期望: {expected_orders}，实际: {sorted_orders}"
                )

    # ===============================
    # 录制脚本质量检查 API（供外部调用）
    # ===============================
    def check_script_quality(
        self,
        actions: List[Dict[str, Any]],
        browser_type: str = "chromium",
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
    ) -> Dict[str, Any]:
        """
        录制脚本质量检查 API。

        与 validate() 不同，本方法不会在发现第一个错误后立即抛出异常，
        而是尽可能收集所有步骤中的问题，并返回给调用方，用于在前端逐步提示用户。

        返回结构示例:
            {
                "is_valid": False,
                "issues": [
                    {
                        "level": "error",        # error / warning
                        "code": "MISSING_SELECTOR",
                        "action_id": "action_3",
                        "order": 3,
                        "type": "click",
                        "message": "点击操作缺少有效的选择器",
                        "suggestion": "请重新录制该步骤，或为该元素配置稳定的 data-testid / id。"
                    },
                    ...
                ],
                "summary": {
                    "error_count": 1,
                    "warning_count": 2,
                    "total_actions": 5
                }
            }
        """
        issues: List[Dict[str, Any]] = []

        # -------- 1. 全局配置校验（浏览器配置等）--------
        try:
            self._validate_browser_config(
                browser_type=browser_type,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                timeout=timeout,
            )
        except ValidationError as e:
            issues.append(
                self._build_issue(
                    level="error",
                    code="BROWSER_CONFIG_INVALID",
                    action=None,
                    message=str(e),
                    suggestion="请检查浏览器类型、视口大小和超时时间配置是否正确。",
                )
            )

        # -------- 2. actions 列表结构校验（重复 id / order 等）--------
        try:
            self._validate_actions_list(actions)
        except ValidationError as e:
            issues.append(
                self._build_issue(
                    level="error",
                    code="ACTIONS_LIST_INVALID",
                    action=None,
                    message=str(e),
                    suggestion="请检查是否存在重复的步骤 id 或顺序值（order），并确保 actions 列表不为空。",
                )
            )

        # -------- 3. 逐个 action 进行结构 & 语义质量检查 --------
        for action in actions:
            # 3.1 基于原有 _validate_action 的强校验（字段缺失、类型错误等）
            try:
                self._validate_action(action)
            except ValidationError as e:
                issues.append(
                    self._build_issue(
                        level="error",
                        code="ACTION_INVALID",
                        action=action,
                        message=str(e),
                        suggestion="请根据提示补全必填字段或修正错误的参数类型，然后重新录制或编辑该步骤。",
                    )
                )
                # 出现结构性错误时，无需再做质量建议检查，继续下一个步骤
                continue

            # 3.2 额外的“质量建议”检查，不改变原有业务逻辑
            self._check_action_quality(action, issues)

        # -------- 4. 校验步骤顺序是否连续 --------
        try:
            self._validate_action_order(actions)
        except ValidationError as e:
            issues.append(
                self._build_issue(
                    level="warning",
                    code="ORDER_NOT_CONTINUOUS",
                    action=None,
                    message=str(e),
                    suggestion="建议保证步骤顺序从 1 开始并连续递增，以便后续维护和排查问题。",
                )
            )

        # -------- 5. 全局脚本级别质量建议（例如：第一个步骤是否为 navigate）--------
        self._check_global_script_quality(actions, issues)

        error_count = sum(1 for i in issues if i.get("level") == "error")
        warning_count = sum(1 for i in issues if i.get("level") == "warning")

        return {
            "is_valid": error_count == 0,
            "issues": issues,
            "summary": {
                "error_count": error_count,
                "warning_count": warning_count,
                "total_actions": len(actions),
            },
        }

    # ===============================
    # 质量检查内部辅助方法
    # ===============================
    def _build_issue(
        self,
        level: str,
        code: str,
        action: Optional[Dict[str, Any]],
        message: str,
        suggestion: str,
    ) -> Dict[str, Any]:
        """构造统一的质量问题结构，便于前端直接展示"""
        action_id = action.get("id") if isinstance(action, dict) else None
        order = action.get("order") if isinstance(action, dict) else None
        action_type = action.get("type") if isinstance(action, dict) else None

        return {
            "level": level,  # error / warning
            "code": code,
            "action_id": action_id,
            "order": order,
            "type": action_type,
            "message": message,
            "suggestion": suggestion,
        }

    def _check_action_quality(
        self, action: Dict[str, Any], issues: List[Dict[str, Any]]
    ):
        """
        针对单个 action 的“友好建议”级别质量检查。

        这些检查不会改变原有 validate() 的通过/失败逻辑，只提供更细粒度的提示。
        """
        action_type = action.get("type")
        selector = action.get("selector")
        params = action.get("params") or {}

        # 1. selector 质量检查（仅对需要 selector 的操作执行）
        if action_type in self.ACTIONS_REQUIRING_SELECTOR:
            if not selector:
                issues.append(
                    self._build_issue(
                        level="error",
                        code="MISSING_SELECTOR",
                        action=action,
                        message="该步骤需要选择器(selector)，但录制结果为空。",
                        suggestion="请重新录制该步骤，确保点击或输入的是页面上的稳定元素，例如带有 id 或 data-testid 的元素。",
                    )
                )
            else:
                if isinstance(selector, dict):
                    # 对 {type, value} 结构进行基础质量检查
                    sel_type = selector.get("type")
                    sel_value = selector.get("value", "")
                    
                    # 极弱选择器（纯标签名）：升级为 error，因为几乎必然失败
                    weak_tag_selectors = {"div", "span", "body", "p", "a", "button", "input", "li", "ul", "section", "article"}
                    
                    if sel_type == "css":
                        if sel_value in weak_tag_selectors:
                            issues.append(
                                self._build_issue(
                                    level="error",  # 升级为 error，因为这种选择器几乎一定会失败
                                    code="GENERIC_CSS_SELECTOR",
                                    action=action,
                                    message=f"该步骤使用了极弱的 CSS 选择器: '{sel_value}'，页面上可能有多个相同标签，执行时几乎必然失败。",
                                    suggestion="请删除此步骤并重新录制，确保点击的元素有稳定的 id 或 data-testid；或者手动编辑选择器，添加更精确的定位条件。",
                                )
                            )
                        # 简单启发式：没有类名、属性等，只有标签名（但不在常见弱标签列表中）
                        elif (
                            sel_value
                            and sel_value.isalpha()
                            and " " not in sel_value
                            and "#" not in sel_value
                            and "." not in sel_value
                            and "[" not in sel_value
                            and ":" not in sel_value  # 排除伪类如 :has-text()
                        ):
                            issues.append(
                                self._build_issue(
                                    level="warning",
                                    code="WEAK_CSS_SELECTOR",
                                    action=action,
                                    message=f"选择器 '{sel_value}' 可能过于宽泛，容易受到页面结构变化影响。",
                                    suggestion="建议使用包含 id / class / data-* 属性的更稳定选择器。",
                                )
                            )
                # 字符串选择器（兼容旧数据）
                elif isinstance(selector, str):
                    sel_stripped = selector.strip()
                    weak_tag_selectors_str = {"div", "span", "body", "p", "a", "button", "input", "li", "ul", "section", "article"}
                    if sel_stripped in weak_tag_selectors_str:
                        issues.append(
                            self._build_issue(
                                level="error",  # 升级为 error
                                code="GENERIC_STRING_SELECTOR",
                                action=action,
                                message=f"该步骤使用了极弱的选择器: '{sel_stripped}'，页面上可能有多个相同标签，执行时几乎必然失败。",
                                suggestion="请删除此步骤并重新录制，确保点击的元素有稳定的 id 或 data-testid；或者手动编辑选择器。",
                            )
                        )

        # 2. 针对部分类型给出更人性化的提示
        if action_type == "fill":
            value = params.get("value")
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(
                    self._build_issue(
                        level="warning",
                        code="EMPTY_FILL_VALUE",
                        action=action,
                        message="输入操作未填写任何内容，可能是录制时误触导致的空步骤。",
                        suggestion="如果该输入步骤是多余的，建议在用例中删除它；否则请重新录制并输入期望的值。",
                    )
                )

        if action_type == "wait":
            wait_type = (params or {}).get("type", "timeout")
            if wait_type == "timeout":
                timeout = params.get("timeout", 0)
                if isinstance(timeout, int) and timeout > 15000:
                    issues.append(
                        self._build_issue(
                            level="warning",
                            code="LONG_WAIT_TIMEOUT",
                            action=action,
                            message=f"该步骤设置了较长的固定等待时间: {timeout}ms。",
                            suggestion="建议优先使用基于元素出现的等待（type='selector'），可以显著提升用例稳定性和执行效率。",
                        )
                    )

        # 3. 对当前执行引擎暂不完全支持的类型给出预警（例如 assert / extract）
        if action_type in {"assert", "extract"}:
            issues.append(
                self._build_issue(
                    level="warning",
                    code="ACTION_NOT_FULLY_SUPPORTED",
                    action=action,
                    message=f"当前执行引擎对 '{action_type}' 类型的步骤支持有限，可能在执行时失败。",
                    suggestion="建议先使用基础操作（navigate / click / fill / select / wait / screenshot）完成主流程，"  # noqa: E501
                    "断言和数据提取功能可以在后续版本中逐步引入。",
                )
            )

    def _check_global_script_quality(
        self, actions: List[Dict[str, Any]], issues: List[Dict[str, Any]]
    ):
        """
        脚本级别的整体质量检查（不针对某一步骤，而是整体流程）。
        """
        if not actions:
            return

        # 1. 首个可执行步骤是否为 navigate，给出建议（但不强制）
        first_action = sorted(
            [a for a in actions if isinstance(a, dict)],
            key=lambda x: x.get("order", 0) or 0,
        )[0]
        if first_action.get("type") != "navigate":
            issues.append(
                self._build_issue(
                    level="warning",
                    code="FIRST_ACTION_NOT_NAVIGATE",
                    action=first_action,
                    message="推荐将第一个步骤设置为 'navigate'，显式打开起始页面。",
                    suggestion="建议在录制开始时，先从用例期望的起始地址执行一次页面跳转，以提高脚本可读性和可维护性。",
                )
            )


