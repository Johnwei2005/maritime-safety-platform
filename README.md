# 海洋平台安全检测系统

这是一个用于监控和分析海上平台安全状况的综合解决方案。系统通过导入3D模型，结合气体浓度监测、风险评估和疏散路线规划等功能，为海洋平台的安全管理提供全面支持。

## 系统特点

- **3D模型可视化**：支持STEP格式模型导入和渲染
- **气体浓度监测**：实时监控各区域气体浓度
- **风险评估与预测**：基于数据分析的风险评估和预测
- **疏散路线规划**：智能规划最优疏散路线
- **数据可视化**：直观的图表和热力图展示

## 技术栈

### 前端
- Vue.js 3.x
- Three.js (3D渲染)
- Chart.js (数据可视化)
- Vuex (状态管理)
- Vue Router (路由管理)

### 后端
- Python 3.10+
- FastAPI (Web框架)
- OpenCASCADE (CAD模型处理)
- trimesh (3D网格处理)
- NumPy/SciPy (数值计算)

## 项目结构

```
maritime-safety-platform/
├── docs/                    # 文档
│   ├── technical_documentation.md  # 技术文档
│   └── user_manual.md              # 用户手册
├── models/                  # 3D模型
│   └── offshore_platform_sample.stp  # 示例模型
├── src/                     # 后端源代码
│   ├── model_processing/    # 模型处理模块
│   ├── space_analysis/      # 空间分析模块
│   ├── ventilation/         # 通风分析模块
│   └── data_output/         # 数据输出模块
├── visualization/           # 前端源代码
│   ├── public/              # 静态资源
│   └── src/                 # 源代码
│       ├── api/             # API客户端
│       ├── assets/          # 静态资源
│       ├── components/      # Vue组件
│       ├── composables/     # Vue组合式API
│       ├── services/        # 服务层
│       ├── store/           # Vuex状态管理
│       └── views/           # 页面视图
├── .gitignore               # Git忽略文件
├── requirements.txt         # Python依赖
├── setup.ps1                # Windows安装脚本
└── README.md                # 项目说明
```

## Windows 11 VSCode部署指南

### 前端部署

1. 安装Node.js (推荐v16+)
   ```
   winget install OpenJS.NodeJS.LTS
   ```

2. 安装Vue CLI
   ```
   npm install -g @vue/cli
   ```

3. 安装依赖并启动开发服务器
   ```
   cd visualization
   npm install
   npm run serve
   ```

### 后端部署

1. 安装Python 3.10+
   ```
   winget install Python.Python.3.10
   ```

2. 创建虚拟环境
   ```
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. 安装依赖
   ```
   pip install -r requirements.txt
   ```

4. 启动API服务器
   ```
   python api_server.py
   ```

## VSCode配置

推荐安装以下VSCode扩展：
- Python
- Pylance
- Vetur (Vue工具)
- ESLint
- Prettier

## 系统优化

本项目已进行以下优化：
- 前端界面设计优化，提升用户体验
- 实现异步优化，提高系统响应性能
- 优化模型上传和处理流程
- 优化数据可视化效果

## 文档

详细文档请参阅：
- [技术文档](docs/technical_documentation.md)
- [用户手册](docs/user_manual.md)

## 许可证

私有项目，未经授权不得使用或分发。
