#!/bin/bash
# StockOracle 一键启动脚本（macOS / Linux）
# 用法：chmod +x start.sh && ./start.sh

set -e

cd "$(dirname "$0")"

echo "🚀 StockOracle 启动中..."
echo ""

# 1. 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ 未找到 Python，请先安装 Python 3.8 或更高版本"
    exit 1
fi

echo "使用: $($PYTHON --version)"

# 2. 检查并安装依赖
REQUIRED="PySide6 pandas numpy akshare pyqtgraph plyer requests"
NEED_INSTALL=0

for pkg in $REQUIRED; do
    if ! $PYTHON -c "import $pkg" &> /dev/null; then
        echo "⚠️  缺少依赖: $pkg"
        NEED_INSTALL=1
    fi
done

if [ $NEED_INSTALL -eq 1 ]; then
    echo ""
    echo "📦 正在安装依赖（首次运行可能需要 5-10 分钟）..."
    $PYTHON -m pip install --user $REQUIRED
    echo "✅ 依赖安装完成"
else
    echo "✅ 所有依赖已就绪"
fi

# 3. 启动应用
echo ""
echo "🎯 正在启动 StockOracle..."
PYTHONPATH=src $PYTHON run.py
