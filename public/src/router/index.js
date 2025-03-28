import { createRouter, createWebHistory } from 'vue-router'
import MainView from '@/views/MainView.vue'
import Settings from '@/views/Settings.vue'
import SensorDashboard from '@/views/SensorDashboard.vue'

const routes = [
  { path: '/', name: 'Home', component: MainView },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/sensors', name: 'Sensors', component: SensorDashboard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
