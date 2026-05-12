from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from .validators.script_validator import ScriptValidator

if TYPE_CHECKING:
    from test_ui_app.models import UITestScript


def validate_script_actions(script: UITestScript) -> Tuple[bool, str | None]:
    """
    统一的脚本验证逻辑
    
    Args:
        script: UITestScript 实例
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    validator = ScriptValidator()
    actions = script.actions or []
    
    if not actions:
        return False, "script actions is empty"
    
    result: Tuple[bool, str | None] = validator.validate(
        actions=actions,
        browser_type=script.browser_type,
        viewport_width=script.viewport_width,
        viewport_height=script.viewport_height,
        timeout=script.timeout
    )
    return result
