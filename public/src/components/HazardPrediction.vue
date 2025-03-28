<template>
  <div class="hazard-prediction">
    <div class="prediction-header">
      <h3>危险预测与风险评估</h3>
      <div class="time-selector">
        <span>预测时间范围：</span>
        <select v-model="timeRange">
          <option value="1">1小时</option>
          <option value="6">6小时</option>
          <option value="12">12小时</option>
          <option value="24">24小时</option>
        </select>
      </div>
    </div>

    <div class="prediction-content">
      <div class="prediction-map">
        <div class="map-container">
          <div class="map-overlay" :class="{'high-risk': highRiskZones.length > 0}">
            <div v-if="isLoading" class="loading-indicator">
              <div class="spinner"></div>
              <span>正在计算风险区域...</span>
            </div>
            <div v-else-if="highRiskZones.length > 0" class="risk-alert">
              <i class="fas fa-exclamation-triangle"></i>
              <span>检测到 {{ highRiskZones.length }} 个高风险区域</span>
            </div>
          </div>
          <canvas ref="mapCanvas" class="map-canvas"></canvas>
        </div>
        <div class="map-legend">
          <div class="legend-item">
            <div class="color-box safe"></div>
            <span>安全区域</span>
          </div>
          <div class="legend-item">
            <div class="color-box warning"></div>
            <span>警告区域</span>
          </div>
          <div class="legend-item">
            <div class="color-box danger"></div>
            <span>危险区域</span>
          </div>
          <div class="legend-item">
            <div class="color-box critical"></div>
            <span>严重危险</span>
          </div>
        </div>
      </div>

      <div class="prediction-details">
        <div class="risk-summary">
          <h4>风险概览</h4>
          <div class="risk-level" :class="overallRiskClass">
            <div class="risk-indicator">
              <div class="risk-bar" :style="{ width: `${overallRiskPercentage}%` }"></div>
            </div>
            <div class="risk-label">{{ overallRiskLabel }}</div>
          </div>
          <div class="risk-factors">
            <div class="factor" v-for="(factor, index) in riskFactors" :key="index">
              <div class="factor-name">{{ factor.name }}</div>
              <div class="factor-value" :class="factor.status">{{ factor.value }}</div>
            </div>
          </div>
        </div>

        <div class="prediction-zones">
          <h4>区域风险详情</h4>
          <div class="zones-list" v-if="zones.length > 0">
            <div 
              v-for="(zone, index) in zones" 
              :key="index" 
              class="zone-item"
              :class="zone.riskClass"
              @click="selectZone(zone)"
              :class="{ 'selected': selectedZone === zone }"
            >
              <div class="zone-name">{{ zone.name }}</div>
              <div class="zone-risk">
                <i :class="zone.icon"></i>
                <span>{{ zone.riskLevel }}</span>
              </div>
            </div>
          </div>
          <div class="no-zones" v-else>
            <p>暂无区域风险数据</p>
          </div>
        </div>
      </div>
    </div>

    <div class="prediction-actions">
      <button class="action-button primary" @click="runPrediction" :disabled="isLoading">
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
        {{ isLoading ? '计算中...' : '更新预测' }}
      </button>
      <button class="action-button secondary" @click="exportReport">
        <i class="fas fa-file-export"></i>
        导出报告
      </button>
    </div>

    <div class="zone-detail-panel" v-if="selectedZone">
      <div class="panel-header">
        <h4>{{ selectedZone.name }} - 详细信息</h4>
        <button class="close-button" @click="selectedZone = null">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="panel-content">
        <div class="detail-item">
          <div class="detail-label">风险等级</div>
          <div class="detail-value" :class="selectedZone.riskClass">{{ selectedZone.riskLevel }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">气体浓度</div>
          <div class="detail-value">{{ selectedZone.gasConcentration }} ppm</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">温度</div>
          <div class="detail-value">{{ selectedZone.temperature }}°C</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">湿度</div>
          <div class="detail-value">{{ selectedZone.humidity }}%</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">预测趋势</div>
          <div class="detail-value" :class="selectedZone.trendClass">
            <i :class="selectedZone.trendIcon"></i>
            {{ selectedZone.trend }}
          </div>
        </div>
        <div class="detail-chart">
          <canvas ref="detailChart"></canvas>
        </div>
        <div class="detail-recommendations">
          <h5>安全建议</h5>
          <ul>
            <li v-for="(rec, index) in selectedZone.recommendations" :key="index">
              {{ rec }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import Chart from 'chart.js/auto';

export default {
  name: 'HazardPrediction',
  
  setup() {
    // 状态变量
    const timeRange = ref('6');
    const isLoading = ref(false);
    const mapCanvas = ref(null);
    const detailChart = ref(null);
    const selectedZone = ref(null);
    let mapContext = null;
    let detailChartInstance = null;
    
    // 模拟数据
    const zones = ref([
      {
        id: 1,
        name: '主控制室',
        riskLevel: '低风险',
        riskClass: 'safe',
        icon: 'fas fa-check-circle',
        gasConcentration: 450,
        temperature: 22.5,
        humidity: 65,
        trend: '稳定',
        trendClass: 'stable',
        trendIcon: 'fas fa-arrows-alt-h',
        recommendations: [
          '保持正常监控',
          '定期检查通风系统'
        ]
      },
      {
        id: 2,
        name: '机械舱',
        riskLevel: '中等风险',
        riskClass: 'warning',
        icon: 'fas fa-exclamation-circle',
        gasConcentration: 850,
        temperature: 26.8,
        humidity: 72,
        trend: '上升',
        trendClass: 'rising',
        trendIcon: 'fas fa-arrow-up',
        recommendations: [
          '增加通风频率',
          '检查密封情况',
          '准备应急设备'
        ]
      },
      {
        id: 3,
        name: '储存区A',
        riskLevel: '高风险',
        riskClass: 'danger',
        icon: 'fas fa-radiation',
        gasConcentration: 1250,
        temperature: 29.2,
        humidity: 80,
        trend: '快速上升',
        trendClass: 'rising',
        trendIcon: 'fas fa-arrow-up',
        recommendations: [
          '立即疏散非必要人员',
          '启动紧急通风系统',
          '穿戴防护装备',
          '准备应急处置方案'
        ]
      },
      {
        id: 4,
        name: '生活区',
        riskLevel: '低风险',
        riskClass: 'safe',
        icon: 'fas fa-check-circle',
        gasConcentration: 420,
        temperature: 23.1,
        humidity: 60,
        trend: '稳定',
        trendClass: 'stable',
        trendIcon: 'fas fa-arrows-alt-h',
        recommendations: [
          '保持正常监控',
          '无需特别措施'
        ]
      },
      {
        id: 5,
        name: '甲板区域',
        riskLevel: '低风险',
        riskClass: 'safe',
        icon: 'fas fa-check-circle',
        gasConcentration: 380,
        temperature: 21.5,
        humidity: 75,
        trend: '下降',
        trendClass: 'falling',
        trendIcon: 'fas fa-arrow-down',
        recommendations: [
          '保持正常监控',
          '无需特别措施'
        ]
      }
    ]);
    
    // 风险因素
    const riskFactors = ref([
      { name: '气体浓度', value: '中等', status: 'warning' },
      { name: '温度', value: '正常', status: 'normal' },
      { name: '湿度', value: '偏高', status: 'warning' },
      { name: '通风状况', value: '良好', status: 'normal' }
    ]);
    
    // 计算属性
    const highRiskZones = computed(() => {
      return zones.value.filter(zone => 
        zone.riskClass === 'danger' || zone.riskClass === 'critical'
      );
    });
    
    const overallRiskPercentage = computed(() => {
      // 根据高风险区域数量计算总体风险百分比
      const zoneCount = zones.value.length;
      if (zoneCount === 0) return 0;
      
      let riskScore = 0;
      zones.value.forEach(zone => {
        if (zone.riskClass === 'safe') riskScore += 0;
        else if (zone.riskClass === 'warning') riskScore += 1;
        else if (zone.riskClass === 'danger') riskScore += 2;
        else if (zone.riskClass === 'critical') riskScore += 3;
      });
      
      return Math.min(100, Math.round((riskScore / (zoneCount * 3)) * 100));
    });
    
    const overallRiskClass = computed(() => {
      const percentage = overallRiskPercentage.value;
      if (percentage < 25) return 'safe';
      if (percentage < 50) return 'warning';
      if (percentage < 75) return 'danger';
      return 'critical';
    });
    
    const overallRiskLabel = computed(() => {
      const percentage = overallRiskPercentage.value;
      if (percentage < 25) return '安全';
      if (percentage < 50) return '需要注意';
      if (percentage < 75) return '危险';
      return '极度危险';
    });
    
    // 方法
    const initMap = () => {
      if (!mapCanvas.value) return;
      
      const canvas = mapCanvas.value;
      mapContext = canvas.getContext('2d');
      
      // 设置画布尺寸
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      
      // 绘制简单的平台示意图
      drawPlatformMap();
    };
    
    const drawPlatformMap = () => {
      if (!mapContext) return;
      
      const ctx = mapContext;
      const width = ctx.canvas.width;
      const height = ctx.canvas.height;
      
      // 清空画布
      ctx.clearRect(0, 0, width, height);
      
      // 绘制平台轮廓
      ctx.fillStyle = '#f8f9fa';
      ctx.strokeStyle = '#343a40';
      ctx.lineWidth = 2;
      
      // 主平台
      ctx.beginPath();
      ctx.rect(width * 0.1, height * 0.2, width * 0.8, height * 0.6);
      ctx.fill();
      ctx.stroke();
      
      // 分区
      // 主控制室
      ctx.fillStyle = getZoneColor(zones.value[0]);
      ctx.beginPath();
      ctx.rect(width * 0.15, height * 0.25, width * 0.25, height * 0.2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#000';
      ctx.font = '12px Arial';
      ctx.fillText('主控制室', width * 0.2, height * 0.35);
      
      // 机械舱
      ctx.fillStyle = getZoneColor(zones.value[1]);
      ctx.beginPath();
      ctx.rect(width * 0.45, height * 0.25, width * 0.4, height * 0.2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#000';
      ctx.fillText('机械舱', width * 0.65, height * 0.35);
      
      // 储存区A
      ctx.fillStyle = getZoneColor(zones.value[2]);
      ctx.beginPath();
      ctx.rect(width * 0.15, height * 0.5, width * 0.25, height * 0.25);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#000';
      ctx.fillText('储存区A', width * 0.2, height * 0.625);
      
      // 生活区
      ctx.fillStyle = getZoneColor(zones.value[3]);
      ctx.beginPath();
      ctx.rect(width * 0.45, height * 0.5, width * 0.2, height * 0.25);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#000';
      ctx.fillText('生活区', width * 0.5, height * 0.625);
      
      // 甲板区域
      ctx.fillStyle = getZoneColor(zones.value[4]);
      ctx.beginPath();
      ctx.rect(width * 0.7, height * 0.5, width * 0.15, height * 0.25);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#000';
      ctx.fillText('甲板', width * 0.75, height * 0.625);
    };
    
    const getZoneColor = (zone) => {
      if (!zone) return '#f8f9fa';
      
      switch (zone.riskClass) {
        case 'safe': return 'rgba(40, 167, 69, 0.3)';
        case 'warning': return 'rgba(255, 193, 7, 0.3)';
        case 'danger': return 'rgba(220, 53, 69, 0.3)';
        case 'critical': return 'rgba(136, 8, 8, 0.3)';
        default: return '#f8f9fa';
      }
    };
    
    const selectZone = (zone) => {
      selectedZone.value = zone;
      
      // 延迟一下，确保DOM已更新
      setTimeout(() => {
        if (detailChart.value && selectedZone.value) {
          initDetailChart();
        }
      }, 100);
    };
    
    const initDetailChart = () => {
      if (detailChartInstance) {
        detailChartInstance.destroy();
      }
      
      const ctx = detailChart.value.getContext('2d');
      
      // 生成模拟数据
      const hours = parseInt(timeRange.value);
      const labels = Array.from({ length: hours + 1 }, (_, i) => `+${i}h`);
      
      // 根据当前浓度和趋势生成预测数据
      const currentConcentration = selectedZone.value.gasConcentration;
      let trendFactor = 0;
      
      if (selectedZone.value.trend === '上升') {
        trendFactor = 50;
      } else if (selectedZone.value.trend === '快速上升') {
        trendFactor = 100;
      } else if (selectedZone.value.trend === '下降') {
        trendFactor = -30;
      }
      
      const concentrationData = [currentConcentration];
      for (let i = 1; i <= hours; i++) {
        // 添加一些随机波动
        const randomFactor = (Math.random() - 0.5) * 30;
        const newValue = Math.max(300, concentrationData[i-1] + trendFactor + randomFactor);
        concentrationData.push(newValue);
      }
      
      detailChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: '预测气体浓度 (ppm)',
            data: concentrationData,
            borderColor: '#0077ff',
            backgroundColor: 'rgba(0, 119, 255, 0.1)',
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            tooltip: {
              mode: 'index',
              intersect: false
            },
            legend: {
              position: 'top',
            }
          },
          scales: {
            y: {
              beginAtZero: false,
              min: 300,
              title: {
                display: true,
                text: '浓度 (ppm)'
              }
            }
          }
        }
      });
    };
    
    const runPrediction = async () => {
      isLoading.value = true;
      
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 更新风险数据（模拟）
      updateRiskData();
      
      // 重绘地图
      drawPlatformMap();
      
      isLoading.value = false;
    };
    
    const updateRiskData = () => {
      // 模拟数据更新
      zones.value = zones.value.map(zone => {
        // 随机调整风险等级
        const riskLevels = ['safe', 'warning', 'danger', 'critical'];
        const currentIndex = riskLevels.indexOf(zone.riskClass);
        
        // 70%概率保持不变，30%概率变化
        let newIndex = currentIndex;
        if (Math.random() < 0.3) {
          // 变化范围为±1
          const change = Math.random() < 0.5 ? -1 : 1;
          newIndex = Math.max(0, Math.min(riskLevels.length - 1, currentIndex + change));
        }
        
        const newRiskClass = riskLevels[newIndex];
        let newRiskLevel, newIcon;
        
        switch (newRiskClass) {
          case 'safe':
            newRiskLevel = '低风险';
            newIcon = 'fas fa-check-circle';
            break;
          case 'warning':
            newRiskLevel = '中等风险';
            newIcon = 'fas fa-exclamation-circle';
            break;
          case 'danger':
            newRiskLevel = '高风险';
            newIcon = 'fas fa-radiation';
            break;
          case 'critical':
            newRiskLevel = '严重风险';
            newIcon = 'fas fa-skull-crossbones';
            break;
          default:
            newRiskLevel = '未知';
            newIcon = 'fas fa-question-circle';
        }
        
        // 更新气体浓度
        let gasChange = 0;
        if (newRiskClass === 'safe') gasChange = -50;
        else if (newRiskClass === 'warning') gasChange = 50;
        else if (newRiskClass === 'danger') gasChange = 100;
        else if (newRiskClass === 'critical') gasChange = 200;
        
        const newGasConcentration = Math.max(350, Math.min(2000, 
          zone.gasConcentration + gasChange + (Math.random() - 0.5) * 100
        ));
        
        // 更新趋势
        let newTrend, newTrendClass, newTrendIcon;
        if (newGasConcentration > zone.gasConcentration + 100) {
          newTrend = '快速上升';
          newTrendClass = 'rising';
          newTrendIcon = 'fas fa-arrow-up';
        } else if (newGasConcentration > zone.gasConcentration + 20) {
          newTrend = '上升';
          newTrendClass = 'rising';
          newTrendIcon = 'fas fa-arrow-up';
        } else if (newGasConcentration < zone.gasConcentration - 100) {
          newTrend = '快速下降';
          newTrendClass = 'falling';
          newTrendIcon = 'fas fa-arrow-down';
        } else if (newGasConcentration < zone.gasConcentration - 20) {
          newTrend = '下降';
          newTrendClass = 'falling';
          newTrendIcon = 'fas fa-arrow-down';
        } else {
          newTrend = '稳定';
          newTrendClass = 'stable';
          newTrendIcon = 'fas fa-arrows-alt-h';
        }
        
        return {
          ...zone,
          riskClass: newRiskClass,
          riskLevel: newRiskLevel,
          icon: newIcon,
          gasConcentration: Math.round(newGasConcentration),
          temperature: Math.round((zone.temperature + (Math.random() - 0.5) * 2) * 10) / 10,
          humidity: Math.round(zone.humidity + (Math.random() - 0.5) * 5),
          trend: newTrend,
          trendClass: newTrendClass,
          trendIcon: newTrendIcon
        };
      });
      
      // 更新风险因素
      updateRiskFactors();
      
      // 如果有选中的区域，更新详情图表
      if (selectedZone.value) {
        const updatedZone = zones.value.find(z => z.id === selectedZone.value.id);
        if (updatedZone) {
          selectedZone.value = updatedZone;
          initDetailChart();
        }
      }
    };
    
    const updateRiskFactors = () => {
      // 计算平均气体浓度
      const avgConcentration = zones.value.reduce((sum, zone) => sum + zone.gasConcentration, 0) / zones.value.length;
      
      // 更新风险因素
      riskFactors.value = [
        { 
          name: '气体浓度', 
          value: avgConcentration < 600 ? '正常' : avgConcentration < 1000 ? '中等' : '危险', 
          status: avgConcentration < 600 ? 'normal' : avgConcentration < 1000 ? 'warning' : 'danger' 
        },
        { 
          name: '温度', 
          value: '正常', 
          status: 'normal' 
        },
        { 
          name: '湿度', 
          value: '偏高', 
          status: 'warning' 
        },
        { 
          name: '通风状况', 
          value: avgConcentration < 800 ? '良好' : '不足', 
          status: avgConcentration < 800 ? 'normal' : 'warning' 
        }
      ];
    };
    
    const exportReport = () => {
      // 模拟导出报告功能
      alert('风险评估报告已导出');
    };
    
    // 监听时间范围变化
    watch(timeRange, () => {
      if (selectedZone.value && detailChart.value) {
        initDetailChart();
      }
    });
    
    // 生命周期钩子
    onMounted(() => {
      // 初始化地图
      initMap();
      
      // 窗口大小变化时重绘地图
      window.addEventListener('resize', () => {
        if (mapCanvas.value) {
          mapCanvas.value.width = mapCanvas.value.clientWidth;
          mapCanvas.value.height = mapCanvas.value.clientHeight;
          drawPlatformMap();
        }
      });
    });
    
    onUnmounted(() => {
      // 清理
      if (detailChartInstance) {
        detailChartInstance.destroy();
      }
      window.removeEventListener('resize', () => {});
    });
    
    return {
      timeRange,
      isLoading,
      mapCanvas,
      detailChart,
      zones,
      selectedZone,
      highRiskZones,
      riskFactors,
      overallRiskPercentage,
      overallRiskClass,
      overallRiskLabel,
      selectZone,
      runPrediction,
      exportReport
    };
  }
};
</script>

<style scoped>
.hazard-prediction {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.prediction-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e9ecef;
}

.prediction-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #343a40;
}

.time-selector {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}

.time-selector span {
  margin-right: 0.5rem;
  color: #495057;
}

.time-selector select {
  padding: 0.25rem 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
}

.prediction-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.prediction-map {
  background-color: white;
  border-radius: 6px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.map-container {
  position: relative;
  height: 300px;
  margin-bottom: 1rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  overflow: hidden;
}

.map-canvas {
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.1);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.map-overlay.high-risk {
  background-color: rgba(220, 53, 69, 0.1);
  opacity: 1;
}

.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 1rem;
  border-radius: 6px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(0, 119, 255, 0.3);
  border-radius: 50%;
  border-top-color: #0077ff;
  animation: spin 1s linear infinite;
  margin-bottom: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.risk-alert {
  display: flex;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  color: #dc3545;
  font-weight: 500;
}

.risk-alert i {
  margin-right: 0.5rem;
}

.map-legend {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 0.75rem;
  color: #6c757d;
}

.color-box {
  width: 12px;
  height: 12px;
  margin-right: 0.25rem;
  border: 1px solid #dee2e6;
}

.color-box.safe {
  background-color: rgba(40, 167, 69, 0.3);
}

.color-box.warning {
  background-color: rgba(255, 193, 7, 0.3);
}

.color-box.danger {
  background-color: rgba(220, 53, 69, 0.3);
}

.color-box.critical {
  background-color: rgba(136, 8, 8, 0.3);
}

.prediction-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.risk-summary {
  background-color: white;
  border-radius: 6px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.risk-summary h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #343a40;
}

.risk-level {
  margin-bottom: 1rem;
}

.risk-indicator {
  height: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.risk-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.risk-level.safe .risk-bar {
  background-color: #28a745;
}

.risk-level.warning .risk-bar {
  background-color: #ffc107;
}

.risk-level.danger .risk-bar {
  background-color: #dc3545;
}

.risk-level.critical .risk-bar {
  background-color: #880808;
}

.risk-label {
  text-align: right;
  font-size: 0.875rem;
  font-weight: 500;
}

.risk-level.safe .risk-label {
  color: #28a745;
}

.risk-level.warning .risk-label {
  color: #ffc107;
}

.risk-level.danger .risk-label {
  color: #dc3545;
}

.risk-level.critical .risk-label {
  color: #880808;
}

.risk-factors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.factor {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  font-size: 0.875rem;
}

.factor-name {
  color: #495057;
}

.factor-value {
  font-weight: 500;
}

.factor-value.normal {
  color: #28a745;
}

.factor-value.warning {
  color: #ffc107;
}

.factor-value.danger {
  color: #dc3545;
}

.prediction-zones {
  background-color: white;
  border-radius: 6px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  flex: 1;
}

.prediction-zones h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #343a40;
}

.zones-list {
  max-height: 200px;
  overflow-y: auto;
}

.zone-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.zone-item:hover {
  background-color: #f8f9fa;
}

.zone-item.selected {
  background-color: #e9ecef;
  border-left: 3px solid #0077ff;
}

.zone-item.safe {
  border-left: 3px solid #28a745;
}

.zone-item.warning {
  border-left: 3px solid #ffc107;
}

.zone-item.danger {
  border-left: 3px solid #dc3545;
}

.zone-item.critical {
  border-left: 3px solid #880808;
}

.zone-name {
  font-weight: 500;
  color: #343a40;
}

.zone-risk {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
}

.zone-risk i {
  margin-right: 0.25rem;
}

.zone-item.safe .zone-risk {
  color: #28a745;
}

.zone-item.warning .zone-risk {
  color: #ffc107;
}

.zone-item.danger .zone-risk {
  color: #dc3545;
}

.zone-item.critical .zone-risk {
  color: #880808;
}

.no-zones {
  text-align: center;
  padding: 2rem 0;
  color: #6c757d;
}

.prediction-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.action-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background-color 0.2s;
}

.action-button i {
  margin-right: 0.5rem;
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-button.primary {
  background-color: #0077ff;
  color: white;
}

.action-button.primary:hover:not(:disabled) {
  background-color: #0066cc;
}

.action-button.secondary {
  background-color: #e9ecef;
  color: #495057;
}

.action-button.secondary:hover:not(:disabled) {
  background-color: #dee2e6;
}

.zone-detail-panel {
  margin-top: 1.5rem;
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.panel-header h4 {
  margin: 0;
  font-size: 1rem;
  color: #343a40;
}

.close-button {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  padding: 0.25rem;
}

.close-button:hover {
  color: #343a40;
}

.panel-content {
  padding: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f1f3f5;
}

.detail-label {
  color: #6c757d;
  font-size: 0.875rem;
}

.detail-value {
  font-weight: 500;
  color: #343a40;
}

.detail-value.safe {
  color: #28a745;
}

.detail-value.warning {
  color: #ffc107;
}

.detail-value.danger {
  color: #dc3545;
}

.detail-value.critical {
  color: #880808;
}

.detail-value.rising {
  color: #dc3545;
}

.detail-value.falling {
  color: #28a745;
}

.detail-value.stable {
  color: #6c757d;
}

.detail-chart {
  height: 200px;
  margin: 1rem 0;
}

.detail-recommendations {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  margin-top: 1rem;
}

.detail-recommendations h5 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: #343a40;
}

.detail-recommendations ul {
  margin: 0;
  padding-left: 1.25rem;
}

.detail-recommendations li {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  color: #495057;
}

@media (max-width: 992px) {
  .prediction-content {
    grid-template-columns: 1fr;
  }
}
</style>
