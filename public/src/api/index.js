import axios from 'axios';

/**
 * API客户端配置
 * 用于与后端API进行通信
 */

// 创建axios实例
export const apiClient = axios.create({
  // 根据环境变量设置基础URL，默认为本地开发环境
  baseURL: process.env.VUE_APP_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 30000 // 请求超时时间：30秒
});

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 在发送请求前可以做一些处理，如添加认证信息等
    return config;
  },
  error => {
    // 请求错误处理
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    // 对响应数据进行处理
    return response.data;
  },
  error => {
    // 响应错误处理
    if (error.response) {
      // 服务器返回错误状态码
      console.error('响应错误:', error.response.status, error.response.data);
      
      // 可以根据不同的错误状态码进行不同的处理
      switch (error.response.status) {
        case 401:
          // 未授权处理
          console.error('未授权访问');
          break;
        case 404:
          // 资源不存在处理
          console.error('请求的资源不存在');
          break;
        case 500:
          // 服务器错误处理
          console.error('服务器内部错误');
          break;
        default:
          // 其他错误处理
          console.error('请求失败');
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('未收到响应:', error.request);
    } else {
      // 请求配置出错
      console.error('请求配置错误:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
