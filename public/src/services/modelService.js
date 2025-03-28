import { asyncRequest, RequestStatus } from '@/services/asyncService';
import { apiClient } from '@/api';

/**
 * 模型服务 - 负责处理3D模型文件的上传、获取和解算
 * 优化版本：使用异步服务进行请求管理和状态跟踪
 */
export const modelService = {
  /**
   * 上传模型文件
   * @param {File} file 模型文件
   * @param {Function} onProgress 进度回调函数
   * @returns {Promise<Object>} 上传结果
   */
  uploadModel(file, onProgress) {
    const formData = new FormData();
    formData.append('model_file', file);
    
    // 生成请求唯一标识符
    const requestKey = `upload_model_${file.name}_${Date.now()}`;
    
    // 使用异步服务包装请求
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 创建上传请求
          const response = await apiClient.post('/upload-model', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            },
            onUploadProgress: (progressEvent) => {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              // 更新进度
              if (progressUpdater) {
                progressUpdater(percentCompleted);
              }
              if (onProgress) {
                onProgress(percentCompleted);
              }
            }
          });
          
          return response;
        } catch (error) {
          console.error('模型上传失败:', error);
          throw error;
        }
      },
      {
        priority: 3, // 高优先级
        forceRefresh: true, // 始终发送新请求，不使用缓存
        cacheDuration: 0 // 不缓存上传请求
      }
    );
  },
  
  /**
   * 获取模型数据
   * @param {String} modelId 模型ID
   * @returns {Promise<Object>} 模型数据
   */
  getModelData(modelId) {
    const requestKey = `get_model_${modelId}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get(`/models/${modelId}`);
        } catch (error) {
          console.error(`获取模型数据失败 (ID: ${modelId}):`, error);
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
   * 启动模型解算
   * @param {String} modelId 模型ID
   * @param {Function} onProgress 进度回调函数
   * @returns {Promise<Object>} 解算结果
   */
  startSolve(modelId, onProgress) {
    const requestKey = `solve_model_${modelId}`;
    
    return asyncRequest(
      requestKey,
      async (progressUpdater) => {
        try {
          // 启动解算
          const response = await apiClient.post('/start-solve', { modelId });
          
          // 模拟解算进度更新
          if (progressUpdater || onProgress) {
            let progress = 0;
            const interval = setInterval(() => {
              progress += 5;
              if (progress <= 100) {
                if (progressUpdater) progressUpdater(progress);
                if (onProgress) onProgress(progress);
              } else {
                clearInterval(interval);
              }
            }, 500);
            
            // 确保在请求完成时清除定时器
            setTimeout(() => clearInterval(interval), 12000);
          }
          
          return response;
        } catch (error) {
          console.error(`模型解算失败 (ID: ${modelId}):`, error);
          throw error;
        }
      },
      {
        priority: 2, // 中优先级
        forceRefresh: true, // 始终发送新请求
        cacheDuration: 0 // 不缓存解算请求
      }
    );
  },
  
  /**
   * 获取解算结果
   * @param {String} modelId 模型ID
   * @returns {Promise<Object>} 解算结果
   */
  getSolveResult(modelId) {
    const requestKey = `solve_result_${modelId}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get(`/solve-result/${modelId}`);
        } catch (error) {
          console.error(`获取解算结果失败 (ID: ${modelId}):`, error);
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
   * 获取模型的空间信息
   * @param {String} modelId 模型ID
   * @returns {Promise<Object>} 空间信息
   */
  getSpaceInfo(modelId) {
    const requestKey = `space_info_${modelId}`;
    
    return asyncRequest(
      requestKey,
      async () => {
        try {
          return await apiClient.get(`/space-info/${modelId}`);
        } catch (error) {
          console.error(`获取空间信息失败 (ID: ${modelId}):`, error);
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
   * 批量获取多个模型的基本信息
   * @param {Array<String>} modelIds 模型ID数组
   * @returns {Promise<Array<Object>>} 模型信息数组
   */
  batchGetModelsInfo(modelIds) {
    const requests = modelIds.map(modelId => ({
      key: `model_info_${modelId}`,
      requestFn: async () => await apiClient.get(`/models/${modelId}/info`),
      options: { priority: 1, cacheDuration: 300000 }
    }));
    
    return asyncRequest.batchRequests(requests, {
      concurrency: 3, // 最多3个并发请求
      abortOnError: false // 即使部分请求失败也继续其他请求
    });
  },
  
  /**
   * 获取模型上传或解算的请求状态
   * @param {String} requestKey 请求标识符
   * @returns {Object} 请求状态对象
   */
  getRequestStatus(requestKey) {
    return asyncRequest.getRequestStatus(requestKey);
  },
  
  /**
   * 取消模型上传或解算请求
   * @param {String} requestKey 请求标识符
   * @returns {Boolean} 是否成功取消
   */
  cancelRequest(requestKey) {
    return asyncRequest.cancelRequest(requestKey);
  }
};

export default modelService;
