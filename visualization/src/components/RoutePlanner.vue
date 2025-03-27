<!-- visualization/src/components/RoutePlanner.vue -->
<template>
    <div class="route-planner">
      <h2>疏散路线规划</h2>
      <!-- 这里可以添加输入起始点、出口等功能 -->
      <button @click="planRoute">规划路线</button>
      <div v-if="route">
        <h3>规划结果</h3>
        <pre>{{ route }}</pre>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'RoutePlanner',
    data() {
      return {
        route: null
      }
    },
    methods: {
      planRoute() {
        // 调用路由规划服务接口，更新 route 数据
        // 例如：this.$store.dispatch('routing/planRoute', { start: ..., destination: ... })
        console.log('规划路线')
        this.route = { id: 'demo', steps: ['A', 'B', 'C'] }
      }
    }
  }
  </script>
  
  <style scoped>
  .route-planner {
    padding: 1rem;
  }
  </style>
  