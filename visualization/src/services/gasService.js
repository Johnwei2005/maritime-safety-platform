import { asyncRequest, RequestStatus } from '@/services/asyncService';
import { apiClient } from '@/api';

/**
 * 气体服务 - 负责处理气体浓度数据的获取和分析
 * 异步优化版本：使用异步服务进行请求管理和状态跟踪
 */
export const gasService = {
  /**
   * 获取当前气体浓度数据
   * @param {String} zoneId 区域ID（可选）
   * @returns {Promise<Object>} 气体浓度数据
   */
  getCurrentGasData(zoneId = null) {
    const requestKey = zoneId ? `gas_data_${zoneId}` : 'gas_data_all';
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          const endpoint = zoneId ? `/gas/zones/${zoneId}` : '/gas/current';
          return await apiClient.get(endpoint);
        } catch (error) {
          console.error('获取气体数据失败:', error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        cacheDuration: 30000 // 缓存30秒
      }
    );
  },
  
  /**
   * 获取气体浓度历史数据
   * @param {Object} params 查询参数
   * @returns {Promise<Object>} 历史数据
   */
  getHistoricalData(params = {}) {
    const { zoneId, startTime, endTime, interval } = params;
    const requestKey = `gas_history_${zoneId || 'all'}_${startTime}_${endTime}_${interval}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get('/gas/historical', { params });
        } catch (error) {
          console.error('获取历史数据失败:', error);
          throw error;
        }
      },
      {
        priority: 1, // 低优先级
        cacheDuration: 300000 // 缓存5分钟
      }
    );
  },
  
  /**
   * 获取气体浓度预测数据
   * @param {Object} params 预测参数
   * @returns {Promise<Object>} 预测数据
   */
  getPredictionData(params = {}) {
    const { zoneId, hours } = params;
    const requestKey = `gas_prediction_${zoneId || 'all'}_${hours}`;
    
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 模拟预测计算进度
          if (progressUpdater) {
            let progress = 0;
            const interval = setInterval(() => {
              progress += 10;
              if (progress <= 100) {
                progressUpdater(progress);
              } else {
                clearInterval(interval);
              }
            }, 200);
            
            // 确保在请求完成时清除定时器
            setTimeout(() => clearInterval(interval), 2500);
          }
          
          return await apiClient.get('/gas/prediction', { params });
        } catch (error) {
          console.error('获取预测数据失败:', error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        cacheDuration: 60000 // 缓存1分钟
      }
    );
  },
  
  /**
   * 设置通风控制参数
   * @param {Object} params 控制参数
   * @returns {Promise<Object>} 设置结果
   */
  setVentilationControl(params) {
    const requestKey = `ventilation_control_${Date.now()}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.post('/gas/ventilation/control', params);
        } catch (error) {
          console.error('设置通风控制失败:', error);
          throw error;
        }
      },
      {
        priority: 3, // 高优先级
        forceRefresh: true, // 始终发送新请求
        cacheDuration: 0 // 不缓存控制请求
      }
    );
  },
  
  /**
   * 获取风险评估数据
   * @param {Object} params 评估参数
   * @returns {Promise<Object>} 风险评估数据
   */
  getRiskAssessment(params = {}) {
    const { modelId, timeRange } = params;
    const requestKey = `risk_assessment_${modelId}_${timeRange}`;
    
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 模拟风险评估计算进度
          if (progressUpdater) {
            let progress = 0;
            const interval = setInterval(() => {
              progress += 5;
              if (progress <= 100) {
                progressUpdater(progress);
              } else {
                clearInterval(interval);
              }
            }, 100);
            
            // 确保在请求完成时清除定时器
            setTimeout(() => clearInterval(interval), 2500);
          }
          
          return await apiClient.get('/gas/risk-assessment', { params });
        } catch (error) {
          console.error('获取风险评估失败:', error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        cacheDuration: 120000 // 缓存2分钟
      }
    );
  },
  
  /**
   * 实时订阅气体数据更新
   * @param {Function} callback 数据更新回调函数
   * @param {Number} interval 更新间隔（毫秒）
   * @returns {Object} 订阅控制对象
   */
  subscribeToGasUpdates(callback, interval = 5000) {
    let timerId = null;
    let isActive = false;
    
    const fetchAndUpdate = async () => {
      if (!isActive) return;
      
      try {
        const data = await this.getCurrentGasData();
        callback(data);
      } catch (error) {
        console.error('气体数据更新失败:', error);
      }
      
      if (isActive) {
        timerId = setTimeout(fetchAndUpdate, interval);
      }
    };
    
    const start = () => {
      isActive = true;
      fetchAndUpdate();
      return { stop };
    };
    
    const stop = () => {
      isActive = false;
      if (timerId) {
        clearTimeout(timerId);
        timerId = null;
      }
    };
    
    return { start };
  }
};

export default gasService;
