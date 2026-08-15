<script setup>
import { ref } from 'vue'
import ToastHost from './components/ToastHost.vue'

const THEME_STORAGE_KEY = 'dy_theme_mode'
const themeMode = ref('system')

const applyThemeMode = (mode) => {
  const root = document.documentElement
  if (!mode || mode === 'system') {
    root.removeAttribute('data-theme')
    return
  }
  root.setAttribute('data-theme', mode)
}

const setThemeMode = (mode) => {
  themeMode.value = mode
  applyThemeMode(mode)
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch (_e) {
  }
}

try {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  if (saved === 'light' || saved === 'dark' || saved === 'system') {
    themeMode.value = saved
  }
} catch (_e) {
}
</script>

<template>
  <div id="app">
    <nav>
      <router-link to="/stats">统计</router-link>
      <router-link to="/search">搜索</router-link>
      <router-link to="/random">随机</router-link>
      <div class="theme-toggle" data-testid="theme-toggle">
        <button
          type="button"
          class="theme-btn"
          data-testid="theme-system"
          :aria-pressed="themeMode === 'system'"
          @click="setThemeMode('system')"
        >
          跟随系统
        </button>
        <button
          type="button"
          class="theme-btn"
          data-testid="theme-light"
          :aria-pressed="themeMode === 'light'"
          @click="setThemeMode('light')"
        >
          浅色
        </button>
        <button
          type="button"
          class="theme-btn"
          data-testid="theme-dark"
          :aria-pressed="themeMode === 'dark'"
          @click="setThemeMode('dark')"
        >
          夜间
        </button>
      </div>
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
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
}

nav a {
  font-weight: 700;
  color: var(--color-heading);
  text-decoration: none;
  margin-right: 14px;
  padding: 6px 10px;
  border-radius: 8px;
}

.theme-toggle {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.theme-btn {
  border: 1px solid var(--color-border-muted);
  background: var(--color-surface);
  color: var(--color-heading);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}

.theme-btn:hover {
  background: var(--color-surface-hover);
}

.theme-btn[aria-pressed='true'] {
  color: var(--color-heading-strong);
  background: var(--color-active-bg);
  border-color: var(--color-active-bg);
}

nav a.router-link-active {
  color: var(--color-heading-strong);
  background: var(--color-active-bg);
}
</style>
