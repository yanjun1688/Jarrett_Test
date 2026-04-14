# -*- coding: utf-8 -*-
"""
完整的 GLM-5 配置验证测试脚本
测试所有配置更改是否正确
"""
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

def test_budget_manager():
    """测试预算管理器配置"""
    print("\n" + "="*60)
    print("测试 1: 预算管理器配置")
    print("="*60)
    
    from core.context.token_economics.budget_manager import TokenBudgetManager
    
    manager = TokenBudgetManager('glm-5')
    
    print(f"总预算: {manager.total_budget}")
    print(f"预期: 2944 (4096 - 1024 - 128)")
    
    assert manager.total_budget == 2944, f"预算错误: {manager.total_budget}"
    
    print("[PASS] 预算配置正确")
    return True

def test_token_calculator():
    """测试 Token 计算器配置"""
    print("\n" + "="*60)
    print("测试 2: Token 计算器配置")
    print("="*60)
    
    from core.context.token_economics.token_calculator import TokenCalculator
    
    calc = TokenCalculator('glm-5')
    
    print(f"模型: {calc.model_name}")
    print(f"上下文窗口: {calc.get_context_window()}")
    print(f"计算方式: {calc.get_calculation_method()}")
    
    assert calc.get_context_window() == 4096, f"窗口错误: {calc.get_context_window()}"
    
    print("[PASS] Token 计算器配置正确")
    return True

def test_llm_service_creation():
    """测试 LLM 服务创建"""
    print("\n" + "="*60)
    print("测试 3: LLM 服务创建")
    print("="*60)
    
    from core.agents.llm.base_llm import LLMProvider, LLMConfig, create_llm_service
    
    api_key = os.getenv('ZHIPU_API_KEY')
    service = create_llm_service('zhipu', model_name='glm-5', api_key=api_key)
    
    print(f"Provider: {service.config.provider}")
    print(f"Model: {service.config.model_name}")
    print(f"Base URL: {getattr(service, 'base_url', 'N/A')}")
    
    assert service.config.provider == LLMProvider.ZHIPU, "Provider 错误"
    assert service.config.model_name == 'glm-5', "Model 错误"
    assert hasattr(service, 'base_url'), "缺少 base_url 属性"
    
    print("[PASS] LLM 服务创建成功")
    return True

def test_real_api_call():
    """测试实际 API 调用"""
    print("\n" + "="*60)
    print("测试 4: 实际 API 调用")
    print("="*60)
    
    from core.agents.llm.zhipu_llm import ZhipuLLMService
    from core.agents.llm.base_llm import LLMConfig, LLMProvider
    
    api_key = os.getenv('ZHIPU_API_KEY')
    config = LLMConfig(
        provider=LLMProvider.ZHIPU,
        model_name='glm-5',
        api_key=api_key,
        max_tokens=100
    )
    
    service = ZhipuLLMService(config=config)
    
    async def test_call():
        response = await service.generate(prompt='你好，请用一句话介绍自己')
        return response
    
    response = asyncio.run(test_call())
    
    print(f"响应: {response[:100]}..." if len(response) > 100 else f"响应: {response}")
    
    assert response, "响应为空"
    assert len(response) > 0, "响应长度为 0"
    
    print("[PASS] 实际 API 调用成功")
    return True

def test_config_pricing():
    """测试定价配置"""
    print("\n" + "="*60)
    print("测试 5: 定价配置")
    print("="*60)
    
    from core.agents.llm.base_llm import LLMProvider, LLMConfig
    from core.agents.llm.zhipu_llm import ZhipuLLMService
    
    config = LLMConfig(
        provider=LLMProvider.ZHIPU,
        model_name='glm-5',
        api_key='test-key'
    )
    
    service = ZhipuLLMService(config=config)
    
    # 测试定价估算
    cost = service.estimate_cost(1000, 500)
    
    print(f"输入 1000 tokens, 输出 500 tokens")
    print(f"估算费用: ${cost}")
    print(f"预期: $0.00 (免费模型)")
    
    assert cost == 0.0, f"费用错误: {cost}, 应该为 0"
    
    print("[PASS] 定价配置正确（免费模型）")
    return True

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始 GLM-5 完整配置验证")
    print("="*60)
    
    tests = [
        ("预算管理器", test_budget_manager),
        ("Token 计算器", test_token_calculator),
        ("LLM 服务创建", test_llm_service_creation),
        ("实际 API 调用", test_real_api_call),
        ("定价配置", test_config_pricing),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"[FAIL] {name} 测试失败: {e}")
    
    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, success, error in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
        if error:
            print(f"  错误: {error}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！GLM-5 配置正确！")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit(main())