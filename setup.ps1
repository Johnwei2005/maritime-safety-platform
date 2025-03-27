@echo off
echo 正在设置海洋平台安全检测系统开发环境...

REM 检查Python安装
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python未安装，请先安装Python 3.10或更高版本
    exit /b 1
)

REM 检查Node.js安装
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Node.js未安装，请先安装Node.js
    exit /b 1
)

REM 创建Python虚拟环境
if not exist venv (
    echo 创建Python虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
echo 安装Python依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM 安装前端依赖
echo 安装前端依赖...
cd visualization
npm install
cd ..

echo 环境设置完成！
echo.
echo 启动说明:
echo 1. 启动后端: python api_server.py
echo 2. 启动前端: cd visualization ^&^& npm run serve
echo.
echo 开发环境已准备就绪！
