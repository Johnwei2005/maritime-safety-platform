<template>
  <div class="main-view">
    <!-- 头部区域 -->
    <header class="header">
      <div class="logo-container">
        <img class="logo" src="@/assets/logo1.png" alt="Logo 1" />
        <img class="logo" src="@/assets/logo2.png" alt="Logo 2" />
      </div>
      <h1>海上平台安全检测系统</h1>
    </header>

    <!-- 空间模型展示区域（全宽） -->
    <section class="space-model-display">
      <h2>空间模型展示</h2>
      <div class="space-model-container">
        <Dashboard />
        <SpaceMap />
      </div>
    </section>

    <!-- 中间区域：2×2 网格 -->
    <div class="grid-container">
      <!-- 左下：STEP 文件上传 -->
      <div class="grid-item model-upload">
        <h2>STEP 文件上传</h2>
        <section class="model-panel">
          <div class="upload-area">
            <label for="modelFile">上传 STEP 文件 (.step/.stp):</label>
            <input type="file" id="modelFile" @change="handleFileUpload" accept=".step,.stp" />
          </div>
          <!-- 3D 模型预览区域 -->
          <div ref="viewer" class="viewer" v-if="modelLoaded"></div>
          <!-- 开始解算按钮 -->
          <button @click="startSolving" :disabled="!modelLoaded" v-if="modelLoaded" class="solve-button">
            开始解算
          </button>
          <!-- 解算结果展示 -->
          <div class="solve-result" v-if="solveResult">
            <h3>解算结果</h3>
            <pre>{{ solveResult }}</pre>
          </div>
        </section>
      </div>
      <!-- 右下：疏散路线规划 -->
      <div class="grid-item evacuation">
        <h2>疏散路线规划</h2>
        <RoutePlanner />
      </div>
    </div>

    <!-- 底部区域：总体趋势图 -->
    <section class="charts-section">
      <h2>总体气体检测参数趋势</h2>
      <div class="charts-container">
        <canvas id="chart1"></canvas>
        <canvas id="chart2"></canvas>
      </div>
    </section>
  </div>
</template>

<script>
import Dashboard from '@/components/Dashboard.vue'
import SpaceMap from '@/components/SpaceMap.vue'
import RoutePlanner from '@/components/RoutePlanner.vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import modelService from '@/services/modelService.js'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

export default {
  name: 'MainView',
  components: {
    Dashboard,
    SpaceMap,
    RoutePlanner
  },
  data() {
    return {
      modelLoaded: false,
      modelId: '',
      solveResult: null,
      scene: null,
      renderer: null,
      camera: null,
      controls: null,
      animationId: null,
      chart1: null,
      chart2: null,
      chartInterval: null,
      // 模拟的传感器数据（此处不再显示，独立页面处理）
      sensorList: [],
      sensorCharts: {},
      uploadedMeshData: null
    }
  },
  methods: {
    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return
      try {
        const response = await modelService.uploadModel(file)
        if (response.error) {
          console.error('上传或解析错误：', response.error)
          alert('模型上传失败，请检查文件格式或网络连接')
          return
        }
        this.modelId = response.modelId
        this.uploadedMeshData = response
        this.loadModel(response)
      } catch (error) {
        console.error('上传或解析异常：', error)
        alert('模型上传失败，请检查文件格式或网络连接')
      }
    },
    loadModel(meshData) {
      const viewer = this.$refs.viewer
      const width = viewer.clientWidth || 800
      const height = viewer.clientHeight || 400

      this.scene = new THREE.Scene()
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
      this.camera.position.set(0, 0, 100)
      this.renderer = new THREE.WebGLRenderer({ antialias: true })
      this.renderer.setSize(width, height)
      viewer.innerHTML = ''
      viewer.appendChild(this.renderer.domElement)

      this.controls = new OrbitControls(this.camera, this.renderer.domElement)

      const geometry = new THREE.BufferGeometry()
      const vertices = new Float32Array(meshData.vertices.flat())
      geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
      const indices = meshData.faces.flat()
      geometry.setIndex(indices)
      geometry.computeVertexNormals()

      const material = new THREE.MeshStandardMaterial({ color: 0x0077ff, side: THREE.DoubleSide })
      const mesh = new THREE.Mesh(geometry, material)
      this.scene.add(mesh)

      const light = new THREE.DirectionalLight(0xffffff, 1)
      light.position.set(50, 50, 50)
      this.scene.add(light)

      this.modelLoaded = true
      this.animate()
    },
    animate() {
      this.animationId = requestAnimationFrame(this.animate)
      if (this.controls) this.controls.update()
      if (this.renderer && this.scene && this.camera) {
        this.renderer.render(this.scene, this.camera)
      }
    },
    async startSolving() {
      if (!this.modelLoaded || !this.modelId) return
      try {
        const result = await modelService.startSolve(this.modelId)
        this.solveResult = result
      } catch (error) {
        console.error('解算失败：', error)
      }
    },
    initializeCharts() {
      const ctx1 = document.getElementById('chart1').getContext('2d')
      const ctx2 = document.getElementById('chart2').getContext('2d')
      this.chart1 = new Chart(ctx1, {
        type: 'line',
        data: {
          labels: Array.from({ length: 20 }, (_, i) => i + 1),
          datasets: [{
            label: '总体气体浓度 (ppm)',
            data: Array.from({ length: 20 }, () => (Math.random() * 5 + 1).toFixed(2)),
            borderColor: 'rgba(75,192,192,1)',
            backgroundColor: 'rgba(75,192,192,0.2)',
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: '时间点' } },
            y: { title: { display: true, text: '浓度 (ppm)' } }
          }
        }
      })
      this.chart2 = new Chart(ctx2, {
        type: 'line',
        data: {
          labels: Array.from({ length: 20 }, (_, i) => i + 1),
          datasets: [{
            label: '总体温度 (°C)',
            data: Array.from({ length: 20 }, () => (Math.random() * 10 + 20).toFixed(1)),
            borderColor: 'rgba(255,99,132,1)',
            backgroundColor: 'rgba(255,99,132,0.2)',
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: '时间点' } },
            y: { title: { display: true, text: '温度 (°C)' } }
          }
        }
      })
    },
    updateCharts() {
      if (this.chart1) {
        this.chart1.data.datasets[0].data = Array.from({ length: 20 }, () => (Math.random() * 5 + 1).toFixed(2))
        this.chart1.update()
      }
      if (this.chart2) {
        this.chart2.data.datasets[0].data = Array.from({ length: 20 }, () => (Math.random() * 10 + 20).toFixed(1))
        this.chart2.update()
      }
    }
  },
  mounted() {
    this.initializeCharts()
    this.chartInterval = setInterval(this.updateCharts, 5000)
  },
  beforeDestroy() {
    if (this.animationId) cancelAnimationFrame(this.animationId)
    if (this.chartInterval) clearInterval(this.chartInterval)
  }
}
</script>

<style scoped>
.main-view {
  padding: 1rem;
  font-family: "Helvetica Neue", Arial, sans-serif;
}
.header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  border-bottom: 2px solid #ddd;
  padding-bottom: 0.5rem;
}
.logo-container {
  display: flex;
  align-items: center;
  margin-right: 1rem;
}
.logo {
  height: 40px;
  margin-right: 0.5rem;
}
.header h1 {
  font-size: 1.8rem;
  color: #333;
}
.space-model-display {
  margin-bottom: 1rem;
}
.space-model-display h2 {
  font-size: 1.6rem;
  margin-bottom: 0.5rem;
  color: #444;
}
.space-model-container {
  display: flex;
  gap: 1rem;
  background: #fff;
  border: 1px solid #ddd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 1rem;
  height: 400px;
  overflow: auto;
}
.grid-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 300px;
  gap: 1rem;
  margin-bottom: 2rem;
}
.grid-item {
  background: #fff;
  border: 1px solid #ddd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 1rem;
  overflow: auto;
}
.model-panel {
  background: #f9f9f9;
  padding: 1rem;
  border: 1px solid #ddd;
}
.upload-area {
  margin-bottom: 1rem;
}
.viewer {
  width: 100%;
  height: 200px;
  border: 1px solid #ccc;
  margin-bottom: 1rem;
}
.solve-button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  margin-bottom: 1rem;
  background: #0077ff;
  color: #fff;
  border: none;
  cursor: pointer;
}
.solve-button:disabled {
  background: #aaa;
  cursor: not-allowed;
}
.solve-result {
  background: #f7f7f7;
  padding: 1rem;
  border: 1px solid #ccc;
  white-space: pre-wrap;
}
.charts-section {
  margin-bottom: 2rem;
}
.charts-section h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: #444;
}
.charts-container {
  display: flex;
  gap: 1rem;
}
.charts-container canvas {
  background: #fff;
  border: 1px solid #ccc;
  flex: 1;
  height: 200px;
}
</style>
