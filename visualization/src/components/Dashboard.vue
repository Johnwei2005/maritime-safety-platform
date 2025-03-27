<template>
  <div class="dashboard">
    <!-- 气体浓度与风险评估 -->
    <section class="gas-section">
      <h2>气体浓度与风险评估</h2>
      <div class="gas-info">
        <p>当前浓度：{{ gasData.currentConcentration }}</p>
        <p>危险等级：{{ gasData.hazardLevel }}</p>
      </div>
    </section>

    <!-- 空间模型展示 -->
    <section class="space-model-section">
      <h2>空间模型展示</h2>
      <!-- 预留一个 canvas 用于 3D 模型展示 -->
      <canvas id="spaceModelCanvas"></canvas>
    </section>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export default {
  name: 'Dashboard',
  computed: {
    ...mapState({
      gasData: state => state.gas
    })
  },
  mounted() {
    // 初始化 Three.js 渲染，用于展示空间模型
    this.initSpaceModelRenderer()
  },
  methods: {
    initSpaceModelRenderer() {
      const canvas = document.getElementById('spaceModelCanvas')
      if (!canvas) return

      // 初始化渲染器、场景和相机
      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
      renderer.setSize(canvas.clientWidth, canvas.clientHeight)
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(75, canvas.clientWidth / canvas.clientHeight, 0.1, 1000)
      camera.position.z = 5

      // 示例：创建一个旋转立方体
      const geometry = new THREE.BoxGeometry()
      const material = new THREE.MeshStandardMaterial({ color: 0x0077ff, side: THREE.DoubleSide })
      const cube = new THREE.Mesh(geometry, material)
      scene.add(cube)

      // 添加光源
      const light = new THREE.DirectionalLight(0xffffff, 1)
      light.position.set(5, 5, 5)
      scene.add(light)

      // 添加轨道控制器
      const controls = new OrbitControls(camera, renderer.domElement)

      // 渲染动画循环
      function animate() {
        requestAnimationFrame(animate)
        cube.rotation.x += 0.01
        cube.rotation.y += 0.01
        controls.update()
        renderer.render(scene, camera)
      }
      animate()
    }
  }
}
</script>

<style scoped>
.dashboard {
  padding: 1rem;
}
.gas-section,
.space-model-section {
  margin-bottom: 2rem;
}
.gas-section h2,
.space-model-section h2 {
  font-size: 1.6rem;
  margin-bottom: 0.5rem;
  color: #444;
}
.gas-info p {
  margin: 0.3rem 0;
  font-size: 1rem;
}
#spaceModelCanvas {
  width: 100%;
  height: 400px;
  background-color: #eee;
  border: 1px solid #ccc;
}
</style>
