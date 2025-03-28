<template>
  <div id="app">
    <header class="app-header">
      <nav>
        <router-link to="/" exact>首页</router-link>
        <router-link to="/sensors">传感器监控</router-link>
        <router-link to="/settings">设置</router-link>
      </nav>
    </header>
    <main>
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
/* 全局样式 */
body {
  font-family: Arial, sans-serif;
  margin: 0;
  padding: 0;
}
.app-header {
  background-color: #0077ff;
  padding: 1rem;
  color: white;
}
.app-header nav {
  display: flex;
  gap: 1rem;
}
.app-header nav a {
  color: white;
  text-decoration: none;
}
.app-header nav a.router-link-active {
  font-weight: bold;
  text-decoration: underline;
}
main {
  padding: 1rem;
}
</style>
