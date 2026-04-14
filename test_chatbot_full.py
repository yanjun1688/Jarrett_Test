"""
测试 ChatBot API - 完整流程
1. 登录获取token
2. 测试聊天API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def login(username: str, password: str) -> str:
    """登录获取token"""
    print("\n========== 登录 ==========")
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        print(f"登录成功！Token: {token[:20]}...")
        return token
    else:
        print(f"登录失败: {response.text}")
        raise Exception("登录失败")

def test_chat(message: str, token: str, conversation_id: str = None):
    """测试聊天API"""
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": message,
        "provider": "zhipu",
        "model": "glm-5",
        "conversation_id": conversation_id
    }
    
    print(f"\n{'='*60}")
    print(f"测试: {message}")
    print(f"{'='*60}")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/chatbot/chat/",
        headers=headers,
        json=data,
        timeout=30
    )
    elapsed = time.time() - start_time
    
    print(f"耗时: {elapsed:.2f}s")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"工具调用: {result.get('tool_used', False)}")
        
        response_text = result.get('response', '')
        if len(response_text) > 300:
            print(f"响应: {response_text[:300]}...")
        else:
            print(f"响应: {response_text}")
        
        if result.get('tool_used'):
            tool_result = result.get('tool_result', '')
            if len(tool_result) > 150:
                print(f"工具结果: {tool_result[:150]}...")
            else:
                print(f"工具结果: {tool_result}")
        
        return result.get('conversation_id'), result
    else:
        print(f"错误: {response.text}")
        return None, None

def main():
    """完整测试流程"""
    # 1. 登录（使用测试账号）
    try:
        token = login("admin", "admin123")
    except Exception as e:
        print(f"跳过登录，使用环境变量中的token")
        import os
        token = os.environ.get("TEST_TOKEN", "")
        if not token:
            print("无token，退出测试")
            return
    
    # 2. 运行测试用例
    print("\n\n========== 开始测试 ==========")
    
    conv_id = None
    
    # 测试1：调研问题（应该直接回答）
    print("\n\n【测试1】调研问题（核心问题）")
    conv_id, _ = test_chat("调研一下市面上的实现方式", token, conv_id)
    
    # 测试2：打开百度（应该调用browser_navigate）
    print("\n\n【测试2】打开百度")
    conv_id, _ = test_chat("打开百度", token, conv_id)
    
    # 测试3：打开GitHub（应该调用browser_navigate）
    print("\n\n【测试3】打开GitHub trending")
    conv_id, _ = test_chat("打开 https://github.com/trending", token, conv_id)
    
    # 测试4：项目文档查询（应该调用query_knowledge）
    print("\n\n【测试4】项目文档查询")
    conv_id, _ = test_chat("项目中有没有关于API测试的文档？", token, conv_id)
    
    # 测试5：通用知识（应该直接回答）
    print("\n\n【测试5】Playwright使用")
    conv_id, _ = test_chat("Playwright 怎么使用？", token, conv_id)
    
    print("\n\n========== 测试完成 ==========")

if __name__ == "__main__":
    main()