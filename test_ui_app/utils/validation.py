from .validators.script_validator import ScriptValidator, ValidationError

def validate_script_actions(script):
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
    
    return validator.validate(
        actions=actions,
        browser_type=script.browser_type,
        viewport_width=script.viewport_width,
        viewport_height=script.viewport_height,
        timeout=script.timeout
    )
