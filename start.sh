#!/bin/bash
# ============================================
# JTest 一键启动脚本 (Linux/Mac)
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  JTest 测试管理平台 - 启动脚本${NC}"
echo -e "${GREEN}======================================${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] 未找到 Python，请先安装 Python 3.10+${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} 使用 Python: $($PYTHON_CMD --version)"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo -e "${GREEN}[INFO]${NC} 激活虚拟环境..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}[INFO]${NC} 激活虚拟环境..."
    source .venv/bin/activate
else
    echo -e "${YELLOW}[WARN]${NC} 未找到虚拟环境，建议创建: $PYTHON_CMD -m venv venv"
fi

# 调用 Python 启动脚本
echo -e "${GREEN}[INFO]${NC} 启动服务..."
$PYTHON_CMD start.py "$@"
