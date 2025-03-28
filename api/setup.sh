#!/bin/bash
# setup.sh - 为Vercel部署创建虚拟环境

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 输出安装信息
echo "虚拟环境设置完成"
python --version
pip list
