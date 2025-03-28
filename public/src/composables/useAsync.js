import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { asyncRequest, RequestStatus } from '@/services/asyncService';

/**
 * 异步状态管理钩子 - 用于在Vue组件中管理异步请求状态
 * @param {Function} requestFn 执行请求的函数
 * @param {Object} options 配置选项
 * @returns {Object} 状态管理对象
 */
export function useAsyncState(requestFn, options = {}) {
  const {
    immediate = false,
    resetOnExecute = true,
    initialData = null,
    onSuccess = null,
    onError = null,
    onProgress = null
  } = options;

  const data = ref(initialData);
  const error = ref(null);
  const status = ref(RequestStatus.IDLE);
  const progress = ref(0);
  
  // 计算属性
  const isIdle = computed(() => status.value === RequestStatus.IDLE);
  const isPending = computed(() => status.value === RequestStatus.PENDING);
  const isSuccess = computed(() => status.value === RequestStatus.SUCCESS);
  const isError = computed(() => status.value === RequestStatus.ERROR);
  
  // 执行请求
  const execute = async (...args) => {
    if (resetOnExecute) {
      error.value = null;
      if (initialData !== undefined) {
        data.value = initialData;
      }
    }
    
    status.value = RequestStatus.PENDING;
    progress.value = 0;
    
    try {
      // 创建进度更新函数
      const progressUpdater = (progressValue) => {
        progress.value = progressValue;
        if (onProgress) {
          onProgress(progressValue);
        }
      };
      
      // 执行请求
      const result = await requestFn(...args, progressUpdater);
      
      data.value = result;
      status.value = RequestStatus.SUCCESS;
      progress.value = 100;
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      error.value = err;
      status.value = RequestStatus.ERROR;
      
      if (onError) {
        onError(err);
      }
      
      throw err;
    }
  };
  
  // 重置状态
  const reset = () => {
    status.value = RequestStatus.IDLE;
    data.value = initialData;
    error.value = null;
    progress.value = 0;
  };
  
  // 如果immediate为true，则立即执行请求
  onMounted(() => {
    if (immediate) {
      execute();
    }
  });
  
  return {
    data,
    error,
    status,
    progress,
    isIdle,
    isPending,
    isSuccess,
    isError,
    execute,
    reset
  };
}

/**
 * 异步数据加载钩子 - 用于在Vue组件中加载和管理异步数据
 * @param {Function} loadFn 加载数据的函数
 * @param {Object} options 配置选项
 * @returns {Object} 数据加载对象
 */
export function useAsyncData(loadFn, options = {}) {
  const {
    immediate = true,
    watch: watchSource = null,
    watchOptions = { immediate: true },
    initialData = null,
    resetOnLoad = true,
    onSuccess = null,
    onError = null
  } = options;
  
  const asyncState = useAsyncState(loadFn, {
    immediate: false,
    resetOnExecute: resetOnLoad,
    initialData,
    onSuccess,
    onError
  });
  
  // 如果提供了监听源，则在源变化时重新加载数据
  if (watchSource) {
    watch(watchSource, () => {
      asyncState.execute();
    }, watchOptions);
  }
  
  // 如果immediate为true，则立即加载数据
  onMounted(() => {
    if (immediate) {
      asyncState.execute();
    }
  });
  
  return {
    ...asyncState,
    load: asyncState.execute
  };
}

/**
 * 异步轮询钩子 - 用于在Vue组件中定期轮询数据
 * @param {Function} pollFn 轮询函数
 * @param {Object} options 配置选项
 * @returns {Object} 轮询控制对象
 */
export function useAsyncPolling(pollFn, options = {}) {
  const {
    interval = 5000,
    immediate = true,
    stopOnError = false,
    maxRetries = 3,
    retryDelay = 1000,
    onSuccess = null,
    onError = null
  } = options;
  
  const isPolling = ref(false);
  const retryCount = ref(0);
  let timerId = null;
  
  const asyncState = useAsyncState(pollFn, {
    immediate: false,
    onSuccess: (result) => {
      retryCount.value = 0;
      if (onSuccess) {
        onSuccess(result);
      }
    },
    onError: (error) => {
      if (onError) {
        onError(error);
      }
      
      if (stopOnError) {
        stop();
      } else if (retryCount.value < maxRetries) {
        retryCount.value++;
        timerId = setTimeout(executePoll, retryDelay);
      } else {
        stop();
      }
    }
  });
  
  const executePoll = async () => {
    if (!isPolling.value) return;
    
    try {
      await asyncState.execute();
      
      if (isPolling.value) {
        timerId = setTimeout(executePoll, interval);
      }
    } catch (error) {
      // 错误已在asyncState.onError中处理
    }
  };
  
  const start = () => {
    if (isPolling.value) return;
    
    isPolling.value = true;
    retryCount.value = 0;
    executePoll();
  };
  
  const stop = () => {
    isPolling.value = false;
    
    if (timerId) {
      clearTimeout(timerId);
      timerId = null;
    }
  };
  
  // 组件卸载时停止轮询
  onUnmounted(() => {
    stop();
  });
  
  // 如果immediate为true，则立即开始轮询
  onMounted(() => {
    if (immediate) {
      start();
    }
  });
  
  return {
    ...asyncState,
    isPolling,
    retryCount,
    start,
    stop,
    restart: () => {
      stop();
      start();
    }
  };
}

/**
 * 异步表单提交钩子 - 用于在Vue组件中处理表单提交
 * @param {Function} submitFn 提交函数
 * @param {Object} options 配置选项
 * @returns {Object} 表单提交对象
 */
export function useAsyncForm(submitFn, options = {}) {
  const {
    initialValues = {},
    resetOnSuccess = false,
    onSuccess = null,
    onError = null,
    onProgress = null,
    validateFn = null
  } = options;
  
  const values = ref({...initialValues});
  const isDirty = ref(false);
  const errors = ref({});
  const isValid = computed(() => Object.keys(errors.value).length === 0);
  
  // 监听值变化
  watch(values, () => {
    isDirty.value = true;
  }, { deep: true });
  
  const asyncState = useAsyncState(
    async (formValues, progressUpdater) => {
      // 如果提供了验证函数，则先验证
      if (validateFn) {
        const validationErrors = await validateFn(formValues);
        if (validationErrors && Object.keys(validationErrors).length > 0) {
          errors.value = validationErrors;
          throw new Error('表单验证失败');
        }
      }
      
      errors.value = {};
      return await submitFn(formValues, progressUpdater);
    },
    {
      onSuccess: (result) => {
        if (resetOnSuccess) {
          reset();
        } else {
          isDirty.value = false;
        }
        
        if (onSuccess) {
          onSuccess(result);
        }
      },
      onError: (error) => {
        if (onError) {
          onError(error);
        }
      },
      onProgress
    }
  );
  
  const submit = async () => {
    return await asyncState.execute(values.value);
  };
  
  const reset = () => {
    values.value = {...initialValues};
    errors.value = {};
    isDirty.value = false;
    asyncState.reset();
  };
  
  const setFieldValue = (field, value) => {
    values.value[field] = value;
  };
  
  const setFieldError = (field, error) => {
    if (error) {
      errors.value[field] = error;
    } else {
      delete errors.value[field];
    }
  };
  
  return {
    values,
    errors,
    isDirty,
    isValid,
    ...asyncState,
    submit,
    reset,
    setFieldValue,
    setFieldError
  };
}

export default {
  useAsyncState,
  useAsyncData,
  useAsyncPolling,
  useAsyncForm
};
