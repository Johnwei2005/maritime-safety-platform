<template>
    <div class="sensor-dashboard">
      <header class="dashboard-header">
        <h1>传感器数据监控</h1>
        <div class="region-selector">
          <label for="region-select">选择区域：</label>
          <select id="region-select" v-model="selectedRegion">
            <option v-for="region in regions" :key="region.name" :value="region.name">
              {{ region.name }}
            </option>
          </select>
        </div>
      </header>
      <div class="sensor-list">
        <div class="sensor-card" v-for="sensor in currentSensors" :key="sensor.id">
          <h2>{{ sensor.name }}</h2>
          <div class="sensor-values">
            <div class="sensor-param">
              <h3>温度 (°C)</h3>
              <p>当前：{{ sensor.current.temperature.toFixed(1) }}</p>
              <p>平均：{{ sensor.analysis.temperature.avg.toFixed(1) }}</p>
              <p>最高：{{ sensor.analysis.temperature.max.toFixed(1) }}</p>
              <p>最低：{{ sensor.analysis.temperature.min.toFixed(1) }}</p>
            </div>
            <div class="sensor-param">
              <h3>压力 (kPa)</h3>
              <p>当前：{{ sensor.current.pressure.toFixed(1) }}</p>
              <p>平均：{{ sensor.analysis.pressure.avg.toFixed(1) }}</p>
              <p>最高：{{ sensor.analysis.pressure.max.toFixed(1) }}</p>
              <p>最低：{{ sensor.analysis.pressure.min.toFixed(1) }}</p>
            </div>
            <div class="sensor-param">
              <h3>浓度 (ppm)</h3>
              <p>当前：{{ sensor.current.concentration.toFixed(2) }}</p>
              <p>平均：{{ sensor.analysis.concentration.avg.toFixed(2) }}</p>
              <p>最高：{{ sensor.analysis.concentration.max.toFixed(2) }}</p>
              <p>最低：{{ sensor.analysis.concentration.min.toFixed(2) }}</p>
            </div>
          </div>
          <div class="sensor-history">
            <h4>历史数据 (最近 10 次)</h4>
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>温度 (°C)</th>
                  <th>压力 (kPa)</th>
                  <th>浓度 (ppm)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in sensor.history.slice(-10)" :key="record.time">
                  <td>{{ record.time }}</td>
                  <td>{{ record.temperature.toFixed(1) }}</td>
                  <td>{{ record.pressure.toFixed(1) }}</td>
                  <td>{{ record.concentration.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: "SensorDashboard",
    data() {
      return {
        regions: [
          {
            name: "生产作业区",
            sensors: [
              { id: "prod-sensor-1", name: "传感器1" },
              { id: "prod-sensor-2", name: "传感器2" },
              { id: "prod-sensor-3", name: "传感器3" },
              { id: "prod-sensor-4", name: "传感器4" }
            ]
          },
          {
            name: "生活区",
            sensors: [
              { id: "life-sensor-1", name: "传感器1" },
              { id: "life-sensor-2", name: "传感器2" },
              { id: "life-sensor-3", name: "传感器3" },
              { id: "life-sensor-4", name: "传感器4" }
            ]
          }
        ],
        selectedRegion: "生产作业区",
        sensorsData: {}
      }
    },
    computed: {
      currentSensors() {
        const region = this.regions.find(r => r.name === this.selectedRegion)
        if (!region) return []
        return region.sensors.map(sensor => {
          // 如果传感器数据未初始化，则直接赋值（Vue 3 下不再需要 this.$set）
          if (!this.sensorsData[sensor.id]) {
            this.sensorsData[sensor.id] = {
              current: { temperature: 0, pressure: 0, concentration: 0 },
              history: [],
              analysis: {
                temperature: { avg: 0, max: 0, min: Infinity },
                pressure: { avg: 0, max: 0, min: Infinity },
                concentration: { avg: 0, max: 0, min: Infinity }
              }
            }
          }
          return { ...sensor, ...this.sensorsData[sensor.id] }
        })
      }
    },
    methods: {
      updateSensorData() {
        const now = new Date().toLocaleTimeString()
        this.regions.forEach(region => {
          region.sensors.forEach(sensor => {
            const data = this.sensorsData[sensor.id]
            if (!data) return
            // 模拟数据范围：温度 20-30°C、压力 95-105 kPa、浓度 1-5 ppm
            const temp = 20 + Math.random() * 10
            const pressure = 95 + Math.random() * 10
            const conc = 1 + Math.random() * 4
  
            data.current.temperature = temp
            data.current.pressure = pressure
            data.current.concentration = conc
  
            data.history.push({
              time: now,
              temperature: temp,
              pressure: pressure,
              concentration: conc
            })
            if (data.history.length > 50) {
              data.history.shift()
            }
            this.computeAnalysis(data)
          })
        })
      },
      computeAnalysis(sensorData) {
        const fields = ["temperature", "pressure", "concentration"]
        fields.forEach(field => {
          const values = sensorData.history.map(record => record[field])
          const sum = values.reduce((acc, val) => acc + val, 0)
          const avg = values.length ? sum / values.length : 0
          const max = Math.max(...values)
          const min = Math.min(...values)
          sensorData.analysis[field] = { avg, max, min }
        })
      }
    },
    mounted() {
      console.log("SensorDashboard mounted")
      // 初始化每个区域的传感器数据（确保初始数据不为空）
      this.regions.forEach(region => {
        region.sensors.forEach(sensor => {
          if (!this.sensorsData[sensor.id]) {
            this.sensorsData[sensor.id] = {
              current: { temperature: 0, pressure: 0, concentration: 0 },
              history: [],
              analysis: {
                temperature: { avg: 0, max: 0, min: Infinity },
                pressure: { avg: 0, max: 0, min: Infinity },
                concentration: { avg: 0, max: 0, min: Infinity }
              }
            }
          }
        })
      })
      // 每2秒更新一次数据
      setInterval(this.updateSensorData, 2000)
    }
  }
  </script>
  
  <style scoped>
  .sensor-dashboard {
    padding: 1rem;
    font-family: "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f5;
  }
  
  .dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #ddd;
  }
  
  .dashboard-header h1 {
    font-size: 1.8rem;
    color: #333;
  }
  
  .region-selector {
    display: flex;
    align-items: center;
  }
  
  .region-selector label {
    margin-right: 0.5rem;
    font-size: 1rem;
    color: #555;
  }
  
  .region-selector select {
    padding: 0.3rem;
    font-size: 1rem;
  }
  
  .sensor-list {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .sensor-card {
    background: #fff;
    border: 1px solid #ddd;
    padding: 1rem;
    width: calc(50% - 1rem);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
  
  .sensor-card h2 {
    font-size: 1.4rem;
    margin-bottom: 0.5rem;
    color: #0077ff;
  }
  
  .sensor-values {
    display: flex;
    justify-content: space-between;
    margin-bottom: 1rem;
  }
  
  .sensor-param {
    flex: 1;
    margin-right: 0.5rem;
  }
  
  .sensor-param:last-child {
    margin-right: 0;
  }
  
  .sensor-param h3 {
    font-size: 1.2rem;
    margin-bottom: 0.3rem;
    color: #333;
  }
  
  .sensor-param p {
    margin: 0.2rem 0;
    font-size: 0.95rem;
    color: #555;
  }
  
  .sensor-history {
    margin-top: 1rem;
  }
  
  .sensor-history h4 {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    color: #333;
  }
  
  .sensor-history table {
    width: 100%;
    border-collapse: collapse;
  }
  
  .sensor-history th,
  .sensor-history td {
    border: 1px solid #ccc;
    padding: 0.3rem;
    font-size: 0.9rem;
    text-align: center;
    color: #333;
  }
  </style>
  