import { asyncRequest, RequestStatus } from '@/services/asyncService';
import { apiClient } from '@/api';

/**
 * 空间服务 - 负责处理3D空间数据和可视化
 * 异步优化版本：使用异步服务进行请求管理和状态跟踪
 */
export const spaceService = {
  /**
   * 获取空间布局数据
   * @param {String} modelId 模型ID
   * @returns {Promise<Object>} 空间布局数据
   */
  getSpaceLayout(modelId) {
    const requestKey = `space_layout_${modelId}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get(`/space/${modelId}/layout`);
        } catch (error) {
          console.error(`获取空间布局失败 (ID: ${modelId}):`, error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        cacheDuration: 300000 // 缓存5分钟
      }
    );
  },
  
  /**
   * 获取空间路径规划
   * @param {Object} params 路径规划参数
   * @returns {Promise<Object>} 路径规划结果
   */
  getPathPlanning(params) {
    const { modelId, startPoint, endPoint, avoidZones } = params;
    const requestKey = `path_planning_${modelId}_${startPoint}_${endPoint}_${JSON.stringify(avoidZones)}`;
    
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 模拟路径规划计算进度
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
          
          return await apiClient.post('/space/path-planning', params);
        } catch (error) {
          console.error('路径规划失败:', error);
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
   * 获取空间热力图数据
   * @param {Object} params 热力图参数
   * @returns {Promise<Object>} 热力图数据
   */
  getHeatmapData(params) {
    const { modelId, dataType, resolution } = params;
    const requestKey = `heatmap_${modelId}_${dataType}_${resolution}`;
    
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 对于高分辨率请求，模拟进度更新
          if (resolution === 'high' && progressUpdater) {
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
          
          return await apiClient.get('/space/heatmap', { params });
        } catch (error) {
          console.error('获取热力图数据失败:', error);
          throw error;
        }
      },
      {
        priority: 1, // 低优先级
        cacheDuration: 120000 // 缓存2分钟
      }
    );
  },
  
  /**
   * 获取空间截面数据
   * @param {Object} params 截面参数
   * @returns {Promise<Object>} 截面数据
   */
  getSectionData(params) {
    const { modelId, plane, position } = params;
    const requestKey = `section_${modelId}_${plane}_${position}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get('/space/section', { params });
        } catch (error) {
          console.error('获取截面数据失败:', error);
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
   * 获取空间可视化配置
   * @returns {Promise<Object>} 可视化配置
   */
  getVisualizationConfig() {
    const requestKey = 'visualization_config';
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get('/space/visualization/config');
        } catch (error) {
          console.error('获取可视化配置失败:', error);
          throw error;
        }
      },
      {
        priority: 1, // 低优先级
        cacheDuration: 600000 // 缓存10分钟
      }
    );
  },
  
  /**
   * 保存空间可视化配置
   * @param {Object} config 可视化配置
   * @returns {Promise<Object>} 保存结果
   */
  saveVisualizationConfig(config) {
    const requestKey = `save_config_${Date.now()}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.post('/space/visualization/config', config);
        } catch (error) {
          console.error('保存可视化配置失败:', error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        forceRefresh: true, // 始终发送新请求
        cacheDuration: 0 // 不缓存保存请求
      }
    );
  },
  
  /**
   * 获取空间对象详情
   * @param {String} objectId 对象ID
   * @returns {Promise<Object>} 对象详情
   */
  getObjectDetails(objectId) {
    const requestKey = `object_details_${objectId}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get(`/space/objects/${objectId}`);
        } catch (error) {
          console.error(`获取对象详情失败 (ID: ${objectId}):`, error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        cacheDuration: 300000 // 缓存5分钟
      }
    );
  },
  
  /**
   * 批量获取多个空间对象的详情
   * @param {Array<String>} objectIds 对象ID数组
   * @returns {Promise<Array<Object>>} 对象详情数组
   */
  batchGetObjectDetails(objectIds) {
    const requests = objectIds.map(objectId => ({
      key: `object_details_${objectId}`,
      requestFn: async () => await apiClient.get(`/space/objects/${objectId}`),
      options: { priority: 1, cacheDuration: 300000 }
    }));
    
    return asyncRequest.batchRequests(requests, {
      concurrency: 5, // 最多5个并发请求
      abortOnError: false // 即使部分请求失败也继续其他请求
    });
  }
};

export default spaceService;
