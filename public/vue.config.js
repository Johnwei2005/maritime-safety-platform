module.exports = {
  devServer: {
    disableHostCheck: true,
    // 通用配置，适用于所有环境
    port: 8080,
    // 允许所有主机访问
    allowedHosts: 'all',
    // 配置API代理，解决跨域问题
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    }
  },
  // 确保在Windows环境中正确处理路径
  configureWebpack: {
    resolve: {
      symlinks: false
    }
  }
}
