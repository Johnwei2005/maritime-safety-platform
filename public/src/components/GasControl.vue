<template>
  <div class="gas-control">
    <div class="control-header">
      <h3>气体浓度监控与控制</h3>
      <div class="status-indicator" :class="statusClass">
        <span class="status-dot"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>

    <div class="control-body">
      <div class="readings-panel">
        <div class="reading-card" :class="{'alert': isCO2Alert}">
          <div class="reading-icon">
            <i class="fas fa-cloud"></i>
          </div>
          <div class="reading-data">
            <div class="reading-label">CO<sub>2</sub> 浓度</div>
            <div class="reading-value">{{ co2Level }} <span class="unit">ppm</span></div>
            <div class="reading-trend" :class="co2TrendClass">
              <i :class="co2TrendIcon"></i>
              <span>{{ co2TrendText }}</span>
            </div>
          </div>
        </div>

        <div class="reading-card" :class="{'alert': isO2Alert}">
          <div class="reading-icon">
            <i class="fas fa-wind"></i>
          </div>
          <div class="reading-data">
            <div class="reading-label">O<sub>2</sub> 浓度</div>
            <div class="reading-value">{{ o2Level }} <span class="unit">%</span></div>
            <div class="reading-trend" :class="o2TrendClass">
              <i :class="o2TrendIcon"></i>
              <span>{{ o2TrendText }}</span>
            </div>
          </div>
        </div>

        <div class="reading-card">
          <div class="reading-icon">
            <i class="fas fa-thermometer-half"></i>
          </div>
          <div class="reading-data">
            <div class="reading-label">温度</div>
            <div class="reading-value">{{ temperature }} <span class="unit">°C</span></div>
            <div class="reading-trend" :class="tempTrendClass">
              <i :class="tempTrendIcon"></i>
              <span>{{ tempTrendText }}</span>
            </div>
          </div>
        </div>

        <div class="reading-card">
          <div class="reading-icon">
            <i class="fas fa-tint"></i>
          </div>
          <div class="reading-data">
            <div class="reading-label">湿度</div>
            <div class="reading-value">{{ humidity }} <span class="unit">%</span></div>
            <div class="reading-trend" :class="humidityTrendClass">
              <i :class="humidityTrendIcon"></i>
              <span>{{ humidityTrendText }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="control-panel">
        <h4>通风控制</h4>
        <div class="control-group">
          <label for="ventilation-mode">通风模式</label>
          <select id="ventilation-mode" v-model="ventilationMode">
            <option value="auto">自动</option>
            <option value="manual">手动</option>
          </select>
        </div>

        <div class="control-group" v-if="ventilationMode === 'manual'">
          <label for="ventilation-level">通风强度</label>
          <div class="slider-container">
            <input 
              type="range" 
              id="ventilation-level" 
              v-model="ventilationLevel" 
              min="0" 
              max="100" 
              step="5"
            />
            <div class="slider-value">{{ ventilationLevel }}%</div>
          </div>
        </div>

        <div class="control-actions">
          <button 
            class="action-button primary" 
            @click="applySettings"
            :disabled="!settingsChanged"
          >
            应用设置
          </button>
          <button 
            class="action-button secondary" 
            @click="resetSettings"
            :disabled="!settingsChanged"
          >
            重置
          </button>
        </div>
      </div>
    </div>

    <div class="alert-panel" v-if="hasAlerts">
      <div class="alert-header">
        <i class="fas fa-exclamation-triangle"></i>
        <span>警报信息</span>
      </div>
      <div class="alert-list">
        <div class="alert-item" v-for="(alert, index) in activeAlerts" :key="index">
          <div class="alert-time">{{ formatAlertTime(alert.time) }}</div>
          <div class="alert-message">{{ alert.message }}</div>
          <button class="alert-dismiss" @click="dismissAlert(index)">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';

export default {
  name: 'GasControl',
  
  setup() {
    const store = useStore();
    
    // 气体浓度数据
    const co2Level = ref(450);
    const o2Level = ref(20.9);
    const temperature = ref(22.5);
    const humidity = ref(65);
    
    // 趋势数据
    const co2Trend = ref('stable');
    const o2Trend = ref('stable');
    const tempTrend = ref('rising');
    const humidityTrend = ref('falling');
    
    // 控制设置
    const ventilationMode = ref('auto');
    const ventilationLevel = ref(50);
    const originalSettings = ref({
      mode: 'auto',
      level: 50
    });
    
    // 警报数据
    const activeAlerts = ref([]);
    
    // 模拟数据更新
    let dataUpdateInterval;
    
    // 计算属性
    const isCO2Alert = computed(() => co2Level.value > 1000);
    const isO2Alert = computed(() => o2Level.value < 19.5);
    const hasAlerts = computed(() => activeAlerts.value.length > 0);
    
    const statusClass = computed(() => {
      if (isCO2Alert.value || isO2Alert.value) return 'danger';
      if (co2Level.value > 800) return 'warning';
      return 'normal';
    });
    
    const statusText = computed(() => {
      if (isCO2Alert.value || isO2Alert.value) return '危险';
      if (co2Level.value > 800) return '警告';
      return '正常';
    });
    
    // 趋势计算属性
    const co2TrendClass = computed(() => `trend-${co2Trend.value}`);
    const co2TrendIcon = computed(() => {
      if (co2Trend.value === 'rising') return 'fas fa-arrow-up';
      if (co2Trend.value === 'falling') return 'fas fa-arrow-down';
      return 'fas fa-arrows-alt-h';
    });
    const co2TrendText = computed(() => {
      if (co2Trend.value === 'rising') return '上升';
      if (co2Trend.value === 'falling') return '下降';
      return '稳定';
    });
    
    const o2TrendClass = computed(() => `trend-${o2Trend.value}`);
    const o2TrendIcon = computed(() => {
      if (o2Trend.value === 'rising') return 'fas fa-arrow-up';
      if (o2Trend.value === 'falling') return 'fas fa-arrow-down';
      return 'fas fa-arrows-alt-h';
    });
    const o2TrendText = computed(() => {
      if (o2Trend.value === 'rising') return '上升';
      if (o2Trend.value === 'falling') return '下降';
      return '稳定';
    });
    
    const tempTrendClass = computed(() => `trend-${tempTrend.value}`);
    const tempTrendIcon = computed(() => {
      if (tempTrend.value === 'rising') return 'fas fa-arrow-up';
      if (tempTrend.value === 'falling') return 'fas fa-arrow-down';
      return 'fas fa-arrows-alt-h';
    });
    const tempTrendText = computed(() => {
      if (tempTrend.value === 'rising') return '上升';
      if (tempTrend.value === 'falling') return '下降';
      return '稳定';
    });
    
    const humidityTrendClass = computed(() => `trend-${humidityTrend.value}`);
    const humidityTrendIcon = computed(() => {
      if (humidityTrend.value === 'rising') return 'fas fa-arrow-up';
      if (humidityTrend.value === 'falling') return 'fas fa-arrow-down';
      return 'fas fa-arrows-alt-h';
    });
    const humidityTrendText = computed(() => {
      if (humidityTrend.value === 'rising') return '上升';
      if (humidityTrend.value === 'falling') return '下降';
      return '稳定';
    });
    
    const settingsChanged = computed(() => {
      return ventilationMode.value !== originalSettings.value.mode || 
             (ventilationMode.value === 'manual' && 
              ventilationLevel.value !== originalSettings.value.level);
    });
    
    // 方法
    const updateData = () => {
      // 模拟数据变化
      const randomChange = () => (Math.random() - 0.5) * 2;
      
      // 更新CO2
      co2Level.value = Math.max(350, Math.min(1200, co2Level.value + randomChange() * 20));
      if (co2Level.value > 1000 && !isCO2Alert.value) {
        addAlert(`CO2浓度过高 (${co2Level.value.toFixed(0)} ppm)，请检查通风系统`);
      }
      
      // 更新O2
      o2Level.value = Math.max(18, Math.min(21.5, o2Level.value + randomChange() * 0.1));
      if (o2Level.value < 19.5 && !isO2Alert.value) {
        addAlert(`氧气浓度过低 (${o2Level.value.toFixed(1)}%)，存在安全隐患`);
      }
      
      // 更新温度和湿度
      temperature.value = Math.max(18, Math.min(28, temperature.value + randomChange() * 0.3));
      humidity.value = Math.max(30, Math.min(90, humidity.value + randomChange() * 2));
      
      // 更新趋势
      updateTrend();
    };
    
    const updateTrend = () => {
      // 简单模拟趋势变化
      const trends = ['rising', 'falling', 'stable'];
      if (Math.random() < 0.1) {
        co2Trend.value = trends[Math.floor(Math.random() * 3)];
      }
      if (Math.random() < 0.1) {
        o2Trend.value = trends[Math.floor(Math.random() * 3)];
      }
      if (Math.random() < 0.1) {
        tempTrend.value = trends[Math.floor(Math.random() * 3)];
      }
      if (Math.random() < 0.1) {
        humidityTrend.value = trends[Math.floor(Math.random() * 3)];
      }
    };
    
    const addAlert = (message) => {
      activeAlerts.value.push({
        time: new Date(),
        message
      });
    };
    
    const dismissAlert = (index) => {
      activeAlerts.value.splice(index, 1);
    };
    
    const formatAlertTime = (time) => {
      return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };
    
    const applySettings = () => {
      // 保存设置
      originalSettings.value = {
        mode: ventilationMode.value,
        level: ventilationLevel.value
      };
      
      // 模拟API调用
      console.log('应用通风设置:', {
        mode: ventilationMode.value,
        level: ventilationMode.value === 'auto' ? 'auto' : ventilationLevel.value
      });
      
      // 如果是手动模式且CO2浓度高，模拟通风效果
      if (ventilationMode.value === 'manual' && ventilationLevel.value > 70 && co2Level.value > 800) {
        co2Level.value = Math.max(400, co2Level.value - 100);
        co2Trend.value = 'falling';
      }
    };
    
    const resetSettings = () => {
      ventilationMode.value = originalSettings.value.mode;
      ventilationLevel.value = originalSettings.value.level;
    };
    
    // 生命周期钩子
    onMounted(() => {
      // 保存初始设置
      originalSettings.value = {
        mode: ventilationMode.value,
        level: ventilationLevel.value
      };
      
      // 启动数据更新
      dataUpdateInterval = setInterval(updateData, 3000);
    });
    
    onUnmounted(() => {
      // 清除定时器
      clearInterval(dataUpdateInterval);
    });
    
    return {
      // 数据
      co2Level,
      o2Level,
      temperature,
      humidity,
      ventilationMode,
      ventilationLevel,
      activeAlerts,
      
      // 计算属性
      isCO2Alert,
      isO2Alert,
      hasAlerts,
      statusClass,
      statusText,
      co2TrendClass,
      co2TrendIcon,
      co2TrendText,
      o2TrendClass,
      o2TrendIcon,
      o2TrendText,
      tempTrendClass,
      tempTrendIcon,
      tempTrendText,
      humidityTrendClass,
      humidityTrendIcon,
      humidityTrendText,
      settingsChanged,
      
      // 方法
      applySettings,
      resetSettings,
      dismissAlert,
      formatAlertTime
    };
  }
};
</script>

<style scoped>
.gas-control {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e9ecef;
}

.control-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #343a40;
}

.status-indicator {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 0.5rem;
}

.status-indicator.normal .status-dot {
  background-color: #28a745;
}

.status-indicator.warning .status-dot {
  background-color: #ffc107;
}

.status-indicator.danger .status-dot {
  background-color: #dc3545;
}

.status-indicator.normal {
  color: #28a745;
}

.status-indicator.warning {
  color: #ffc107;
}

.status-indicator.danger {
  color: #dc3545;
}

.control-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.readings-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.reading-card {
  background-color: white;
  border-radius: 6px;
  padding: 1rem;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.reading-card.alert {
  background-color: #fff8f8;
  border-left: 3px solid #dc3545;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4);
  }
  70% {
    box-shadow: 0 0 0 5px rgba(220, 53, 69, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
  }
}

.reading-icon {
  font-size: 1.5rem;
  color: #6c757d;
  margin-right: 1rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  border-radius: 50%;
}

.reading-data {
  flex: 1;
}

.reading-label {
  font-size: 0.75rem;
  color: #6c757d;
  margin-bottom: 0.25rem;
}

.reading-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #343a40;
}

.unit {
  font-size: 0.875rem;
  color: #6c757d;
  font-weight: normal;
}

.reading-trend {
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  margin-top: 0.25rem;
}

.reading-trend i {
  margin-right: 0.25rem;
}

.trend-rising {
  color: #dc3545;
}

.trend-falling {
  color: #28a745;
}

.trend-stable {
  color: #6c757d;
}

.control-panel {
  background-color: white;
  border-radius: 6px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.control-panel h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #343a40;
}

.control-group {
  margin-bottom: 1.25rem;
}

.control-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #495057;
}

.control-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: #fff;
  font-size: 0.875rem;
}

.slider-container {
  display: flex;
  align-items: center;
}

.slider-container input[type="range"] {
  flex: 1;
  margin-right: 1rem;
}

.slider-value {
  min-width: 40px;
  text-align: right;
  font-size: 0.875rem;
  color: #495057;
}

.control-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.action-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s;
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

.alert-panel {
  margin-top: 1.5rem;
  background-color: #fff8f8;
  border-radius: 6px;
  padding: 1rem;
  border: 1px solid #f5c6cb;
}

.alert-header {
  display: flex;
  align-items: center;
  color: #721c24;
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.alert-header i {
  margin-right: 0.5rem;
}

.alert-list {
  max-height: 150px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f5c6cb;
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-time {
  font-size: 0.75rem;
  color: #6c757d;
  margin-right: 0.75rem;
  min-width: 60px;
}

.alert-message {
  flex: 1;
  font-size: 0.875rem;
}

.alert-dismiss {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  padding: 0.25rem;
  margin-left: 0.5rem;
}

.alert-dismiss:hover {
  color: #343a40;
}

@media (max-width: 768px) {
  .control-body {
    grid-template-columns: 1fr;
  }
  
  .readings-panel {
    grid-template-columns: 1fr;
  }
}
</style>
