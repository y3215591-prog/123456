#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

if ! python -c "import PySide6" 2>/dev/null; then
    echo "安装依赖..."
    pip install -e .
fi

echo "启动硅锰合金库存管理系统..."
python -m silicon_manganese_inventory.main
