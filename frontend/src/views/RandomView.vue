<template>
  <div class="random-page">
    <h1>随机弹幕</h1>
    
    <div class="controls">
      <button 
        @click="fetchRandom" 
        data-testid="random-btn"
        :disabled="loading"
        class="random-btn"
      >
        {{ loading ? '加载中...' : '随机一条弹幕' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="content" class="result-container" data-testid="random-content">
      <div class="danmu-card">
        <p class="danmu-content">{{ content.content }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const content = ref(null)
const loading = ref(false)
const error = ref(null)

const fetchRandom = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/random')
    if (!response.ok) {
      throw new Error(`请求失败，状态码：${response.status}`)
    }
    const data = await response.json()
    content.value = data
  } catch (e) {
    error.value = '获取随机弹幕失败：' + e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRandom()
})
</script>

<style scoped>
.random-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 20px;
  color: #333;
}

.controls {
  margin-bottom: 20px;
}

.random-btn {
  padding: 10px 20px;
  background-color: #ff5f00; /* Douyu orange-ish */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.random-btn:hover:not(:disabled) {
  background-color: #e04e00;
}

.random-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.error-message {
  color: #721c24;
  margin-bottom: 10px;
  padding: 15px;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}

.result-container {
  margin-top: 20px;
  animation: fadeIn 0.5s ease-in-out;
}

.danmu-card {
  border: 1px solid #ddd;
  padding: 20px;
  border-radius: 8px;
  background-color: white;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.danmu-content {
  font-size: 20px;
  font-weight: 500;
  margin-bottom: 15px;
  color: #333;
  line-height: 1.5;
}


@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
