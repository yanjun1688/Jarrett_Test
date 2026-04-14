"""
测试 ChatBot API
验证工具调用修复效果
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/chatbot"
TOKEN = "your_token_here"  # 需要替换为实际token

def test_api(message: str, conversation_id: str = None):
    """测试聊天API"""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": message,
        "provider": "zhipu",
        "model": "glm-5",
        "conversation_id": conversation_id
    }
    
    print(f"\n{'='*60}")
    print(f"测试消息: {message}")
    print(f"{'='*60}")
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/chat/", headers=headers, json=data)
    elapsed = time.time() - start_time
    
    print(f"耗时: {elapsed:.2f}s")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应: {result.get('response', '')[:200]}...")
        print(f"工具调用: {result.get('tool_used', False)}")
        if result.get('tool_used'):
            print(f"工具结果: {result.get('tool_result', '')[:100]}...")
        return result
    else:
        print(f"错误: {response.text}")
        return None

def main():
    """运行测试用例"""
    print("开始测试...")
    
    # 测试1：调研问题（应该直接回答，不调用工具）
    print("\n\n测试1: 调研问题（核心问题）")
    test_api("调研一下市面上的实现方式")
    
    # 测试2：打开百度（应该调用browser_navigate）
    print("\n\n测试2: 打开百度")
    test_api("打开百度")
    
    # 测试3：打开GitHub trending（应该调用browser_navigate）
    print("\n\n测试3: 打开GitHub trending")
    test_api("打开 https://github.com/trending")
    
    # 测试4：项目文档查询（应该调用query_knowledge）
    print("\n\n测试4: 项目文档查询")
    test_api("项目中有没有关于API测试的文档？")
    
    # 测试5：通用知识问题（应该直接回答）
    print("\n\n测试5: Playwright使用")
    test_api("Playwright 怎么使用？")

if __name__ == "__main__":
    main()