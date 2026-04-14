"""
验证智谱 GLM-5 配置是否正确

测试内容：
1. 环境变量是否正确设置
2. API 连接是否正常
3. 模型是否能正常响应
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_env_config():
    """测试环境变量配置"""
    print("=" * 60)
    print("1. 检查环境变量配置")
    print("=" * 60)
    
    api_key = os.getenv('ZHIPU_API_KEY')
    model_name = os.getenv('ZHIPU_MODEL_NAME')
    base_url = os.getenv('ZHIPU_BASE_URL')
    
    print(f"ZHIPU_API_KEY: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")
    print(f"ZHIPU_MODEL_NAME: {model_name}")
    print(f"ZHIPU_BASE_URL: {base_url}")
    
    if not api_key:
        print("[FAIL] API Key 未设置")
        return False
    
    if not model_name:
        print("[FAIL] Model Name 未设置")
        return False
    
    print("[PASS] 环境变量配置正确")
    return True

def test_api_connection():
    """测试 API 连接"""
    print("\n" + "=" * 60)
    print("2. 测试 API 连接")
    print("=" * 60)
    
    try:
        import openai
        
        api_key = os.getenv('ZHIPU_API_KEY')
        base_url = os.getenv('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
        model_name = os.getenv('ZHIPU_MODEL_NAME', 'glm-5')
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print(f"正在测试模型: {model_name}")
        print(f"API 端点: {base_url}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个有用的AI助手。"},
                {"role": "user", "content": "你好，请用一句话介绍自己。"}
            ],
            temperature=0.7,
            max_tokens=100,
            stream=False
        )
        
        print(f"\n[PASS] API 连接成功！")
        print(f"模型响应: {response.choices[0].message.content}")
        print(f"Token 使用: 输入={response.usage.prompt_tokens}, 输出={response.usage.completion_tokens}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] API 连接失败")
        print(f"错误信息: {str(e)}")
        return False

def test_project_config():
    """测试项目配置"""
    print("\n" + "=" * 60)
    print("3. 测试项目配置")
    print("=" * 60)
    
    try:
        from core.config import get_settings
        
        settings = get_settings()
        
        print(f"LLM Provider: {settings.llm_provider}")
        print(f"LLM Model: {settings.llm_model}")
        print(f"LLM API Key: {settings.llm_api_key[:20]}...{settings.llm_api_key[-10:] if settings.llm_api_key else 'None'}")
        
        if settings.llm_provider != 'zhipu':
            print(f"[WARNING] Provider 不是 zhipu，当前为: {settings.llm_provider}")
            return False
        
        if settings.llm_model != 'glm-5':
            print(f"[WARNING] Model 不是 glm-5，当前为: {settings.llm_model}")
            return False
        
        print("[PASS] 项目配置正确")
        return True
        
    except Exception as e:
        print(f"[FAIL] 项目配置加载失败")
        print(f"错误信息: {str(e)}")
        return False

def main():
    """主测试流程"""
    print("\n" + ">>> 开始验证智谱 GLM-5 配置")
    
    results = []
    
    # 测试 1: 环境变量
    results.append(("环境变量配置", test_env_config()))
    
    # 测试 2: API 连接
    results.append(("API 连接测试", test_api_connection()))
    
    # 测试 3: 项目配置
    results.append(("项目配置测试", test_project_config()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{name}: {status}")
    
    all_success = all(result[1] for result in results)
    
    if all_success:
        print("\n[SUCCESS] 所有测试通过！配置成功切换到智谱 GLM-5（免费模型）")
    else:
        print("\n[WARNING] 部分测试失败，请检查配置")
    
    return all_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)