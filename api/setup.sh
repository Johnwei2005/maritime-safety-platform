#!/bin/bash
# setup.sh - 为Vercel部署创建虚拟环境

# 使用python -m pip而不是直接使用pip命令
echo "使用python -m pip安装依赖"
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt

# 输出安装信息
echo "依赖安装完成"
python --version
python -m pip list
