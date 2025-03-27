# Windows 11 VSCode部署指南 - 海洋安全平台

本指南将帮助您在Windows 11的Visual Studio Code环境中成功部署海洋安全平台项目。

## 前置条件

在开始部署前，请确保您的系统已安装以下软件：

1. **Git** - 用于克隆和管理代码仓库
   - 下载地址：https://git-scm.com/download/win

2. **Miniconda或Anaconda** - 用于创建Python环境和安装OpenCASCADE依赖
   - 下载地址：https://docs.conda.io/en/latest/miniconda.html

3. **Node.js** - 用于运行前端Vue.js应用
   - 下载地址：https://nodejs.org/
   - 推荐版本：LTS (长期支持版)

4. **Visual Studio Code** - 开发环境
   - 下载地址：https://code.visualstudio.com/

5. **VSCode扩展**
   - Python扩展：用于Python开发
   - Vetur或Vue Language Features (Volar)：用于Vue.js开发
   - ESLint：用于代码质量检查

## 部署步骤

### 1. 克隆仓库

打开命令提示符或PowerShell，执行以下命令：

```bash
git clone https://github.com/Johnwei2005/maritime-safety-platform.git
cd maritime-safety-platform
```

### 2. 使用部署脚本（推荐）

项目中包含了Windows 11专用的部署脚本，可以自动完成环境配置：

1. 在资源管理器中找到项目目录下的`deploy_win11.bat`文件
2. 双击运行，或在命令提示符中执行该脚本
3. 脚本将自动检查依赖、创建环境并安装必要的包

### 3. 手动部署（如果脚本执行失败）

#### 后端部署

1. 创建并激活Conda环境：

```bash
conda create -n maritime python=3.10
conda activate maritime
```

2. 安装OpenCASCADE依赖（关键步骤）：

```bash
conda install -c conda-forge pythonocc-core
```

3. 安装其他Python依赖：

```bash
conda install -c conda-forge numpy scipy trimesh pyvista
pip install fastapi uvicorn
```

4. 启动后端服务：

```bash
cd src
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端部署

1. 安装前端依赖：

```bash
cd visualization
npm install
```

2. 启动前端开发服务器：

```bash
npm run serve
```

3. 在浏览器中访问：`http://localhost:8080`

## 常见问题及解决方案

### 1. OpenCASCADE安装问题

**问题**：安装OpenCASCADE依赖时出错

**解决方案**：
- 确保使用conda而不是pip安装：`conda install -c conda-forge pythonocc-core`
- 如果安装过程中出现冲突，尝试创建全新的环境：
  ```bash
  conda create -n maritime_new python=3.10
  conda activate maritime_new
  conda install -c conda-forge pythonocc-core
  ```

### 2. 路径问题

**问题**：Windows路径分隔符导致文件无法找到

**解决方案**：
- 代码已经修改为使用`pathlib.Path`处理路径，确保跨平台兼容性
- 如果仍然遇到路径问题，请检查文件路径是否包含特殊字符或非英文字符

### 3. 前端构建问题

**问题**：前端构建失败或显示ESLint错误

**解决方案**：
- 使用`npm run serve -- --skip-plugins=eslint`跳过ESLint检查
- 或修复ESLint配置：`npm install eslint --save-dev`

### 4. 3D模型加载问题

**问题**：无法加载或显示3D模型

**解决方案**：
- 确保已正确安装OpenCASCADE依赖
- 检查模型文件格式是否为STEP格式
- 尝试使用项目中提供的示例模型进行测试

## VSCode配置建议

为获得最佳开发体验，建议在VSCode中进行以下配置：

1. 设置Python解释器为conda环境：
   - 按`Ctrl+Shift+P`打开命令面板
   - 输入`Python: Select Interpreter`
   - 选择`maritime`环境

2. 配置终端使用conda环境：
   - 在VSCode中打开新终端
   - 确保终端能够识别conda命令
   - 执行`conda activate maritime`

3. 配置调试设置：
   - 创建`.vscode/launch.json`文件
   - 添加Python和Chrome调试配置

## 部署验证

成功部署后，您应该能够：

1. 在浏览器中访问前端界面：`http://localhost:8080`
2. 上传和查看3D模型
3. 执行空间分析和通风计算

如果遇到任何问题，请参考上述常见问题解决方案，或查看项目GitHub仓库中的issues。
