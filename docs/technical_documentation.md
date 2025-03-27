# 海洋平台安全检测系统 - 技术文档

## 1. 系统概述

海洋平台安全检测系统是一个用于监控和分析海上平台安全状况的综合解决方案。系统通过导入3D模型，结合气体浓度监测、风险评估和疏散路线规划等功能，为海洋平台的安全管理提供全面支持。

### 1.1 系统架构

系统采用前后端分离的架构设计：

- **前端**：基于Vue.js框架，使用Three.js进行3D模型渲染，Chart.js进行数据可视化
- **后端**：基于Python FastAPI框架，提供RESTful API服务
- **数据处理**：使用OpenCASCADE和trimesh库进行3D模型处理和分析

### 1.2 核心功能模块

- 3D模型导入与解析
- 空间分析与检测
- 气体浓度监测与预警
- 风险评估与预测
- 疏散路线规划
- 数据可视化与报告生成

## 2. 技术栈详情

### 2.1 前端技术栈

| 技术/库 | 版本 | 用途 |
|--------|------|------|
| Vue.js | 3.x | 前端框架 |
| Three.js | 最新版 | 3D模型渲染 |
| Chart.js | 最新版 | 数据可视化 |
| Axios | 最新版 | HTTP客户端 |
| Vue Router | 4.x | 前端路由 |
| Vuex | 4.x | 状态管理 |

### 2.2 后端技术栈

| 技术/库 | 版本 | 用途 |
|--------|------|------|
| Python | 3.10+ | 编程语言 |
| FastAPI | 最新版 | Web框架 |
| OpenCASCADE | 最新版 | CAD模型处理 |
| trimesh | 最新版 | 3D网格处理 |
| NumPy | 最新版 | 数值计算 |
| SciPy | 最新版 | 科学计算 |
| Uvicorn | 最新版 | ASGI服务器 |

## 3. 系统依赖要求

### 3.1 运行环境要求

- **操作系统**：Linux (推荐Ubuntu 20.04+)、Windows 10+、macOS 10.15+
- **内存**：最低8GB，推荐16GB以上
- **存储**：最低10GB可用空间
- **处理器**：现代多核处理器，推荐4核以上
- **显卡**：支持WebGL的显卡（用于3D渲染）

### 3.2 软件依赖

#### 前端依赖

```bash
# 安装Node.js和npm
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装Vue CLI
npm install -g @vue/cli

# 安装项目依赖
cd visualization
npm install
```

#### 后端依赖

```bash
# 安装Python和pip
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev

# 安装OpenCASCADE依赖
sudo apt-get install -y libocct-foundation-dev libocct-data-exchange-dev

# 安装Python依赖
pip3 install fastapi uvicorn python-occ-core trimesh numpy scipy

# 如果使用conda环境（推荐）
conda create -n maritime-safety python=3.10
conda activate maritime-safety
conda install -c conda-forge pythonocc-core
pip install fastapi uvicorn trimesh numpy scipy
```

> **重要提示**：OpenCASCADE库(python-occ-core)的安装可能比较复杂，建议使用conda环境进行安装。如果直接使用pip安装失败，请参考[PythonOCC官方文档](https://github.com/tpaviot/pythonocc-core)获取详细安装指南。

## 4. 系统组件详解

### 4.1 前端组件结构

```
visualization/
├── public/
├── src/
│   ├── api/
│   │   └── index.js         # API客户端配置
│   ├── assets/              # 静态资源
│   ├── components/          # Vue组件
│   │   ├── Dashboard.vue    # 仪表盘组件
│   │   ├── GasControl.vue   # 气体控制组件
│   │   ├── HazardPrediction.vue # 危险预测组件
│   │   └── ModelUploader.vue # 模型上传组件
│   ├── composables/
│   │   └── useAsync.js      # 异步操作钩子
│   ├── services/            # 服务层
│   │   ├── asyncService.js  # 异步服务
│   │   ├── gasService.js    # 气体服务
│   │   ├── modelService.js  # 模型服务
│   │   └── spaceService.js  # 空间服务
│   ├── store/               # Vuex状态管理
│   ├── views/               # 页面视图
│   │   └── MainView.vue     # 主视图
│   ├── App.vue              # 根组件
│   └── main.js              # 入口文件
└── package.json             # 项目配置
```

### 4.2 后端模块结构

```
maritime-safety/
├── api_server.py            # API服务器入口
├── src/
│   ├── config.py            # 配置管理
│   ├── main.py              # 主程序入口
│   ├── model_processing/    # 模型处理模块
│   │   ├── format_parser.py # 格式解析器
│   │   └── voxelizer.py     # 体素化工具
│   ├── space_analysis/      # 空间分析模块
│   │   ├── space_detector.py # 空间检测器
│   │   └── opening_detector.py # 开口检测器
│   ├── ventilation/         # 通风分析模块
│   │   ├── topology_builder.py # 拓扑构建器
│   │   └── ach_calculator.py # 通风率计算器
│   └── data_output/         # 数据输出模块
│       └── space_data_generator.py # 空间数据生成器
└── requirements.txt         # 依赖列表
```

## 5. API接口文档

### 5.1 模型管理接口

#### 上传模型

- **URL**: `/api/upload-model`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **参数**:
  - `model_file`: STEP格式的3D模型文件
- **响应**:
  ```json
  {
    "model_id": "string",
    "filename": "string",
    "size": 0,
    "upload_time": "string",
    "status": "success"
  }
  ```

#### 获取模型信息

- **URL**: `/api/models/{model_id}`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "model_id": "string",
    "filename": "string",
    "size": 0,
    "upload_time": "string",
    "spaces_count": 0,
    "openings_count": 0
  }
  ```

#### 启动模型解算

- **URL**: `/api/start-solve`
- **方法**: `POST`
- **Content-Type**: `application/json`
- **参数**:
  ```json
  {
    "model_id": "string"
  }
  ```
- **响应**:
  ```json
  {
    "task_id": "string",
    "status": "processing",
    "estimated_time": 0
  }
  ```

#### 获取解算结果

- **URL**: `/api/solve-result/{model_id}`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "model_id": "string",
    "status": "completed",
    "spaces": [],
    "openings": [],
    "completion_time": "string"
  }
  ```

### 5.2 空间信息接口

#### 获取空间信息

- **URL**: `/api/space-info/{model_id}`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "model_id": "string",
    "spaces": [
      {
        "id": "string",
        "name": "string",
        "volume": 0,
        "area": 0,
        "adjacent_spaces": []
      }
    ]
  }
  ```

#### 获取空间布局

- **URL**: `/api/space/{model_id}/layout`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "model_id": "string",
    "layout": {
      "vertices": [],
      "faces": [],
      "spaces": []
    }
  }
  ```

### 5.3 气体监控接口

#### 获取当前气体数据

- **URL**: `/api/gas/current`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "timestamp": "string",
    "zones": [
      {
        "zone_id": "string",
        "name": "string",
        "co2_level": 0,
        "o2_level": 0,
        "temperature": 0,
        "humidity": 0,
        "risk_level": "string"
      }
    ]
  }
  ```

#### 获取气体预测数据

- **URL**: `/api/gas/prediction`
- **方法**: `GET`
- **参数**:
  - `zoneId`: 区域ID（可选）
  - `hours`: 预测小时数
- **响应**:
  ```json
  {
    "zone_id": "string",
    "predictions": [
      {
        "timestamp": "string",
        "co2_level": 0,
        "o2_level": 0,
        "risk_level": "string"
      }
    ]
  }
  ```

## 6. 数据模型

### 6.1 空间数据模型

```json
{
  "id": "string",
  "name": "string",
  "type": "room|corridor|stairwell",
  "volume": 0,
  "area": 0,
  "height": 0,
  "position": {
    "x": 0,
    "y": 0,
    "z": 0
  },
  "dimensions": {
    "length": 0,
    "width": 0,
    "height": 0
  },
  "adjacent_spaces": [
    {
      "space_id": "string",
      "connection_type": "door|opening|wall"
    }
  ]
}
```

### 6.2 开口数据模型

```json
{
  "id": "string",
  "type": "door|window|vent",
  "area": 0,
  "position": {
    "x": 0,
    "y": 0,
    "z": 0
  },
  "dimensions": {
    "width": 0,
    "height": 0
  },
  "connected_spaces": [
    "space_id_1",
    "space_id_2"
  ]
}
```

### 6.3 气体数据模型

```json
{
  "zone_id": "string",
  "timestamp": "string",
  "measurements": {
    "co2": {
      "value": 0,
      "unit": "ppm",
      "threshold": 1000
    },
    "o2": {
      "value": 0,
      "unit": "%",
      "threshold": 19.5
    },
    "temperature": {
      "value": 0,
      "unit": "°C"
    },
    "humidity": {
      "value": 0,
      "unit": "%"
    }
  },
  "risk_assessment": {
    "level": "safe|warning|danger|critical",
    "factors": [
      {
        "name": "string",
        "value": "string",
        "status": "normal|warning|danger"
      }
    ]
  }
}
```

## 7. 异步优化设计

系统实现了全面的异步优化，提高了响应性能和用户体验：

### 7.1 异步服务核心功能

- **请求队列管理**：控制并发请求数量，避免服务器过载
- **请求优先级**：确保重要请求优先处理
- **缓存机制**：减少重复请求，提高响应速度
- **进度跟踪**：提供实时进度反馈，改善用户体验

### 7.2 Vue组合式API钩子

- **useAsyncState**：管理异步请求状态
- **useAsyncData**：加载和管理异步数据
- **useAsyncPolling**：定期轮询数据
- **useAsyncForm**：处理表单异步提交

### 7.3 异步优化示例代码

```javascript
// 使用异步数据钩子加载模型数据
const { data: modelData, isLoading, error } = useAsyncData(
  () => modelService.getModelData(modelId),
  {
    immediate: true,
    onSuccess: (data) => {
      console.log('模型数据加载成功:', data);
    },
    onError: (err) => {
      console.error('模型数据加载失败:', err);
    }
  }
);

// 使用异步轮询监控气体数据
const { 
  data: gasData, 
  isPolling,
  start: startPolling,
  stop: stopPolling
} = useAsyncPolling(
  () => gasService.getCurrentGasData(),
  {
    interval: 5000, // 每5秒更新一次
    immediate: true
  }
);
```

## 8. 部署指南

### 8.1 开发环境部署

#### 前端开发环境

```bash
# 克隆仓库
git clone <repository-url>
cd maritime-safety/visualization

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

#### 后端开发环境

```bash
# 克隆仓库
git clone <repository-url>
cd maritime-safety

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动API服务器
python api_server.py
```

### 8.2 生产环境部署

#### 前端生产部署

```bash
# 构建生产版本
cd visualization
npm run build

# 部署到Web服务器
cp -r dist/* /var/www/html/
```

#### 后端生产部署

```bash
# 使用Gunicorn和Uvicorn部署
pip install gunicorn

# 启动服务
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app
```

#### Docker部署（推荐）

```bash
# 构建Docker镜像
docker build -t maritime-safety .

# 运行容器
docker run -d -p 8000:8000 --name maritime-safety-app maritime-safety
```

## 9. 测试指南

### 9.1 单元测试

```bash
# 前端单元测试
cd visualization
npm run test:unit

# 后端单元测试
cd maritime-safety
python -m pytest tests/unit/
```

### 9.2 集成测试

```bash
# 后端集成测试
cd maritime-safety
python -m pytest tests/integration/
```

### 9.3 端到端测试

```bash
# 端到端测试
cd visualization
npm run test:e2e
```

## 10. 故障排除

### 10.1 常见问题

#### 模型上传失败

- 检查文件格式是否为STEP格式(.step, .stp)
- 确认文件大小不超过100MB
- 验证服务器存储空间是否充足

#### OpenCASCADE依赖安装失败

- 尝试使用conda安装：`conda install -c conda-forge pythonocc-core`
- 检查系统是否安装了必要的开发库：`apt-get install libocct-foundation-dev`
- 参考[PythonOCC官方文档](https://github.com/tpaviot/pythonocc-core)获取详细安装指南

#### 3D渲染性能问题

- 确保使用支持WebGL的现代浏览器
- 检查显卡驱动是否最新
- 对于大型模型，考虑使用模型简化功能

### 10.2 日志位置

- 前端日志：浏览器控制台
- 后端日志：`maritime-safety/logs/api_server.log`
- 系统日志：`maritime-safety/logs/system.log`

## 11. 性能优化建议

- 对于大型STEP模型，建议使用模型简化功能减少面数
- 启用API响应压缩以减少网络传输量
- 考虑使用Redis缓存频繁请求的数据
- 对于高并发场景，增加API服务器实例数量
- 使用CDN分发前端静态资源

## 12. 安全注意事项

- API服务器应配置HTTPS
- 实施适当的认证和授权机制
- 对上传的文件进行安全验证
- 定期更新依赖库以修复安全漏洞
- 实施API请求速率限制以防止滥用

## 13. 未来开发计划

- 添加机器学习模型进行更准确的风险预测
- 支持更多3D模型格式(如IFC, OBJ)
- 实现实时协作功能
- 开发移动应用版本
- 集成物联网传感器数据

---

文档版本: 1.0.0  
最后更新: 2025年3月27日  
作者: Manus AI
