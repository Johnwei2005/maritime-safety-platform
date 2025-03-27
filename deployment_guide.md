# 海洋安全平台部署指南

本文档提供了海洋安全平台的完整部署指南，包括在Windows 11环境下使用VSCode进行本地部署的详细步骤。

## 项目概述

海洋安全平台是一个用于监控和分析海上平台安全状况的综合解决方案。系统通过导入3D模型，结合气体浓度监测、风险评估和疏散路线规划等功能，为海洋平台的安全管理提供全面支持。

### 技术栈

- **前端**：Vue.js 3.x, Three.js (3D渲染)
- **后端**：Python 3.10+, FastAPI, OpenCASCADE (CAD模型处理)

## 部署前准备

### 系统要求

- Windows 11
- Visual Studio Code
- Node.js 16+ (推荐使用最新LTS版本)
- Python 3.10+
- Git

### 安装必要工具

1. **安装Node.js**
   ```
   winget install OpenJS.NodeJS.LTS
   ```

2. **安装Python 3.10+**
   ```
   winget install Python.Python.3.10
   ```

3. **安装Git**
   ```
   winget install Git.Git
   ```

4. **安装Visual Studio Code**
   ```
   winget install Microsoft.VisualStudioCode
   ```

5. **安装VSCode扩展**
   - Python
   - Pylance
   - Vetur (Vue工具)
   - ESLint
   - Prettier

## 克隆项目

1. 打开命令提示符或PowerShell
2. 克隆仓库
   ```
   git clone https://github.com/Johnwei2005/maritime-safety-platform.git
   cd maritime-safety-platform
   ```

## 前端部署

1. **进入前端目录**
   ```
   cd visualization
   ```

2. **安装依赖**
   ```
   npm install
   ```

3. **安装缺失的关键依赖**
   ```
   npm install --save axios three
   ```

4. **创建ESLint配置文件**
   
   在`visualization`目录下创建`.eslintrc.js`文件，内容如下：
   ```javascript
   module.exports = {
     root: true,
     env: {
       node: true
     },
     extends: [
       'plugin:vue/essential',
       'eslint:recommended'
     ],
     parserOptions: {
       parser: 'babel-eslint'
     },
     rules: {
       'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
       'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off'
     }
   }
   ```

5. **启动开发服务器**
   ```
   npm run serve -- --skip-plugins=eslint
   ```

   前端将在 http://localhost:8080 或 http://localhost:8081 运行

## 后端部署

后端部署需要特别注意OpenCASCADE依赖的安装，这是处理STEP格式3D模型所必需的。

### 方法1：使用Conda环境（推荐）

1. **安装Miniconda**
   
   下载并安装 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

2. **创建Conda环境**
   ```
   conda create -n maritime python=3.10
   conda activate maritime
   ```

3. **安装OpenCASCADE依赖**
   ```
   conda install -c conda-forge pythonocc-core
   ```

4. **安装其他依赖**
   ```
   pip install fastapi uvicorn trimesh numpy scipy pyvista
   ```

5. **修复代码中的相对导入问题**
   
   打开`src/main.py`文件，将相对导入修改为绝对导入：
   ```python
   # 将这些行
   from .config import get_config
   from .model_processing.format_parser import FormatParser
   from .model_processing.voxelizer import AdaptiveVoxelizer
   from .space_analysis.space_detector import SpaceDetector
   from .space_analysis.opening_detector import OpeningDetector
   from .ventilation.topology_builder import TopologyBuilder
   from .ventilation.ach_calculator import AchCalculator
   from .data_output.space_data_generator import SpaceDataGenerator
   
   # 修改为
   from config import get_config
   from model_processing.format_parser import FormatParser
   from model_processing.voxelizer import AdaptiveVoxelizer
   from space_analysis.space_detector import SpaceDetector
   from space_analysis.opening_detector import OpeningDetector
   from ventilation.topology_builder import TopologyBuilder
   from ventilation.ach_calculator import AchCalculator
   from data_output.space_data_generator import SpaceDataGenerator
   ```

6. **启动后端服务**
   ```
   cd src
   python -m uvicorn main:app --reload
   ```

### 方法2：使用Docker（适合团队协作）

1. **安装Docker Desktop**
   
   下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

2. **创建Dockerfile**
   
   在项目根目录创建`Dockerfile`：
   ```dockerfile
   FROM continuumio/miniconda3

   WORKDIR /app

   COPY . .

   RUN conda install -c conda-forge pythonocc-core && \
       pip install fastapi uvicorn trimesh numpy scipy pyvista

   EXPOSE 8000

   CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **构建并运行Docker容器**
   ```
   docker build -t maritime-safety-platform .
   docker run -p 8000:8000 maritime-safety-platform
   ```

## 添加3D模型

1. **准备STEP格式的3D模型**
   
   确保您的3D模型为STEP格式（.stp或.step文件扩展名）

2. **添加到项目**
   
   将3D模型文件复制到`models`目录：
   ```
   cp 您的模型文件.stp maritime-safety-platform/models/offshore_oil_platform.stp
   ```

## 常见问题及解决方案

### 1. OpenCASCADE依赖安装失败

**问题**：使用pip安装opencascade-wrapper包失败

**解决方案**：
- 使用Conda安装pythonocc-core包，这是OpenCASCADE的Python绑定
- 或使用预配置的Docker镜像

### 2. 前端依赖问题

**问题**：缺少axios和three.js依赖

**解决方案**：
```
npm install --save axios three
```

### 3. ESLint配置缺失

**问题**：启动前端时报ESLint配置错误

**解决方案**：
- 创建.eslintrc.js配置文件
- 或使用--skip-plugins=eslint选项启动

### 4. Python相对导入错误

**问题**：运行后端时出现"attempted relative import with no known parent package"错误

**解决方案**：
- 将相对导入（以点号开头的导入）修改为绝对导入
- 或将src目录设置为Python包（添加__init__.py文件）

## 测试部署

1. **启动前端和后端服务**

2. **访问前端界面**
   
   打开浏览器访问 http://localhost:8080 或 http://localhost:8081

3. **上传3D模型**
   
   使用界面上的"上传STEP文件"功能上传模型

4. **测试疏散路线规划功能**
   
   上传模型后，使用"规划路线"功能测试疏散路线规划

## 生产环境部署

对于生产环境，建议：

1. **前端构建**
   ```
   cd visualization
   npm run build
   ```

2. **使用Nginx部署前端**

3. **使用Gunicorn和Nginx部署后端**

4. **配置HTTPS**

## 总结

本部署指南详细介绍了海洋安全平台在Windows 11环境下使用VSCode进行本地部署的步骤。由于项目依赖特定的CAD处理库（OpenCASCADE），建议使用Conda环境或Docker容器进行部署，以确保所有依赖正确安装。

如有任何问题，请参考项目GitHub仓库的issues部分或联系项目维护者。
