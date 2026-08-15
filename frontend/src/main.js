import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const THEME_STORAGE_KEY = 'dy_theme_mode'

const applyThemeMode = (mode) => {
  const root = document.documentElement
  if (!mode || mode === 'system') {
    root.removeAttribute('data-theme')
    return
  }
  root.setAttribute('data-theme', mode)
}

try {
  const savedThemeMode = localStorage.getItem(THEME_STORAGE_KEY)
  applyThemeMode(savedThemeMode)
} catch (_e) {
  applyThemeMode('system')
}

createApp(App)
  .use(router)
  .mount('#app')
