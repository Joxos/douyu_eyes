<script setup>
import ToastHost from './components/ToastHost.vue'
</script>

<template>
  <div id="app">
    <nav>
      <router-link to="/stats">统计</router-link>
      <router-link to="/search">搜索</router-link>
      <router-link to="/random">随机</router-link>
    </nav>
    <main>
      <router-view />
    </main>
    <ToastHost />
  </div>
</template>

<style>
nav {
  padding: 18px 22px;
  margin-bottom: 20px;
  text-align: left;
  border: 1px solid #dbe2f0;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

nav a {
  font-weight: 700;
  color: #1f2937;
  text-decoration: none;
  margin-right: 14px;
  padding: 6px 10px;
  border-radius: 8px;
}

nav a.router-link-active {
  color: #0f172a;
  background: #dbeafe;
}
</style>
