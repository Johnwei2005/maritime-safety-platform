@echo off
REM Windows 11 VSCode部署脚本 - 海洋安全平台
REM 此脚本将自动设置开发环境并部署海洋安全平台

echo ===== 海洋安全平台 Windows 11 部署脚本 =====
echo.

REM 检查是否已安装Conda
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到Conda。请先安装Miniconda或Anaconda。
    echo 下载地址: https://docs.conda.io/en/latest/miniconda.html
    exit /b 1
)

REM 检查是否已安装Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到Node.js。请先安装Node.js。
    echo 下载地址: https://nodejs.org/
    exit /b 1
)

REM 检查是否已安装Git
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到Git。请先安装Git。
    echo 下载地址: https://git-scm.com/download/win
    exit /b 1
)

echo [信息] 环境检查通过，开始部署...
echo.

REM 创建Conda环境
echo [步骤1] 创建Conda环境并安装依赖...
call conda create -n maritime python=3.10 -y
call conda activate maritime

REM 安装OpenCASCADE依赖
echo [步骤2] 安装OpenCASCADE依赖...
call conda install -c conda-forge pythonocc-core -y
call conda install -c conda-forge -y numpy scipy trimesh pyvista

REM 安装Python依赖
echo [步骤3] 安装Python依赖...
call pip install fastapi uvicorn

REM 安装前端依赖
echo [步骤4] 安装前端依赖...
cd visualization
call npm install

echo.
echo ===== 部署完成 =====
echo.
echo 启动后端服务:
echo   conda activate maritime
echo   cd src
echo   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 启动前端服务:
echo   cd visualization
echo   npm run serve
echo.
echo 如需帮助，请参考部署文档。
