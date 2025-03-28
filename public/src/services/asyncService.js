/**
 * 异步服务 - 提供异步操作管理和状态跟踪
 * 用于优化前端异步请求处理，提高用户体验
 */

// 请求状态常量
export const RequestStatus = {
  IDLE: 'idle',
  PENDING: 'pending',
  SUCCESS: 'success',
  ERROR: 'error'
};

// 请求缓存，用于存储请求结果和状态
const requestCache = new Map();

// 请求队列，用于管理并发请求
const requestQueue = [];
const MAX_CONCURRENT_REQUESTS = 3; // 最大并发请求数
let activeRequests = 0;

/**
 * 异步请求包装器
 * @param {string} key - 请求的唯一标识符
 * @param {Function} requestFn - 执行实际请求的函数
 * @param {Object} options - 配置选项
 * @returns {Promise} 请求结果
 */
export const asyncRequest = async (key, requestFn, options = {}) => {
  const {
    forceRefresh = false,
    cacheDuration = 60000, // 默认缓存1分钟
    priority = 1, // 优先级：1-低，2-中，3-高
    onProgress = null // 进度回调函数
  } = options;

  // 检查缓存
  if (!forceRefresh && requestCache.has(key)) {
    const cachedData = requestCache.get(key);
    if (cachedData.status === RequestStatus.SUCCESS && 
        Date.now() - cachedData.timestamp < cacheDuration) {
      return cachedData.data;
    }
  }

  // 更新请求状态为pending
  updateRequestStatus(key, RequestStatus.PENDING);

  // 创建请求项
  const requestItem = {
    key,
    priority,
    execute: async () => {
      try {
        activeRequests++;
        
        // 如果提供了进度回调，创建进度更新函数
        const progressUpdater = onProgress ? 
          (progress) => onProgress(key, progress) : 
          null;
        
        // 执行请求
        const result = await requestFn(progressUpdater);
        
        // 更新缓存和状态
        updateRequestCache(key, result);
        updateRequestStatus(key, RequestStatus.SUCCESS);
        
        return result;
      } catch (error) {
        updateRequestStatus(key, RequestStatus.ERROR, error);
        throw error;
      } finally {
        activeRequests--;
        processNextRequest();
      }
    }
  };

  // 添加到队列并处理
  return await enqueueRequest(requestItem);
};

/**
 * 将请求添加到队列
 * @param {Object} requestItem - 请求项
 * @returns {Promise} 请求结果
 */
const enqueueRequest = async (requestItem) => {
  return new Promise((resolve, reject) => {
    // 添加resolve和reject到请求项
    requestItem.resolve = resolve;
    requestItem.reject = reject;
    
    // 按优先级插入队列
    const insertIndex = requestQueue.findIndex(item => item.priority < requestItem.priority);
    if (insertIndex === -1) {
      requestQueue.push(requestItem);
    } else {
      requestQueue.splice(insertIndex, 0, requestItem);
    }
    
    // 尝试处理队列
    processNextRequest();
  });
};

/**
 * 处理队列中的下一个请求
 */
const processNextRequest = () => {
  if (requestQueue.length === 0 || activeRequests >= MAX_CONCURRENT_REQUESTS) {
    return;
  }
  
  const nextRequest = requestQueue.shift();
  nextRequest.execute()
    .then(result => nextRequest.resolve(result))
    .catch(error => nextRequest.reject(error));
};

/**
 * 更新请求缓存
 * @param {string} key - 请求的唯一标识符
 * @param {*} data - 请求结果数据
 */
const updateRequestCache = (key, data) => {
  requestCache.set(key, {
    data,
    status: RequestStatus.SUCCESS,
    timestamp: Date.now(),
    error: null
  });
};

/**
 * 更新请求状态
 * @param {string} key - 请求的唯一标识符
 * @param {string} status - 请求状态
 * @param {Error} error - 错误对象（如果有）
 */
const updateRequestStatus = (key, status, error = null) => {
  const existingData = requestCache.get(key) || { data: null, timestamp: Date.now() };
  
  requestCache.set(key, {
    ...existingData,
    status,
    error
  });
};

/**
 * 获取请求状态
 * @param {string} key - 请求的唯一标识符
 * @returns {Object} 请求状态对象
 */
export const getRequestStatus = (key) => {
  if (!requestCache.has(key)) {
    return { status: RequestStatus.IDLE, data: null, error: null };
  }
  
  const { status, data, error } = requestCache.get(key);
  return { status, data, error };
};

/**
 * 清除请求缓存
 * @param {string} key - 请求的唯一标识符（如果不提供则清除所有缓存）
 */
export const clearRequestCache = (key = null) => {
  if (key) {
    requestCache.delete(key);
  } else {
    requestCache.clear();
  }
};

/**
 * 批量执行请求
 * @param {Array} requests - 请求配置数组
 * @param {Object} options - 批量请求选项
 * @returns {Promise} 所有请求结果的数组
 */
export const batchRequests = async (requests, options = {}) => {
  const {
    concurrency = MAX_CONCURRENT_REQUESTS,
    abortOnError = false
  } = options;
  
  // 临时设置最大并发数
  const originalMaxConcurrent = MAX_CONCURRENT_REQUESTS;
  MAX_CONCURRENT_REQUESTS = concurrency;
  
  try {
    if (abortOnError) {
      // 如果任何请求失败则中止
      const results = await Promise.all(
        requests.map(req => asyncRequest(req.key, req.requestFn, req.options))
      );
      return results;
    } else {
      // 即使部分请求失败也返回所有结果
      const results = await Promise.allSettled(
        requests.map(req => asyncRequest(req.key, req.requestFn, req.options))
      );
      
      return results.map(result => {
        if (result.status === 'fulfilled') {
          return { success: true, data: result.value };
        } else {
          return { success: false, error: result.reason };
        }
      });
    }
  } finally {
    // 恢复原始最大并发数
    MAX_CONCURRENT_REQUESTS = originalMaxConcurrent;
  }
};

/**
 * 取消请求
 * @param {string} key - 请求的唯一标识符
 * @returns {boolean} 是否成功取消
 */
export const cancelRequest = (key) => {
  const index = requestQueue.findIndex(item => item.key === key);
  if (index !== -1) {
    const [removed] = requestQueue.splice(index, 1);
    removed.reject(new Error('Request cancelled'));
    return true;
  }
  return false;
};

/**
 * 重试失败的请求
 * @param {string} key - 请求的唯一标识符
 * @param {Object} options - 重试选项
 * @returns {Promise} 重试结果
 */
export const retryRequest = async (key, options = {}) => {
  if (!requestCache.has(key)) {
    throw new Error(`No request found with key: ${key}`);
  }
  
  const cachedRequest = requestCache.get(key);
  if (!cachedRequest.requestFn) {
    throw new Error(`Cannot retry request: ${key}, original request function not available`);
  }
  
  return asyncRequest(key, cachedRequest.requestFn, {
    ...options,
    forceRefresh: true
  });
};

export default {
  asyncRequest,
  getRequestStatus,
  clearRequestCache,
  batchRequests,
  cancelRequest,
  retryRequest,
  RequestStatus
};
