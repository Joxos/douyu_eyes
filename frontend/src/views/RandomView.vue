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
        <div class="random-meta" data-testid="random-meta-count">被刷次数：{{ content.count }}</div>
        <div class="random-meta" data-testid="random-meta-last-seen">
          最后出现时间：{{ formatLastSeen(content.last_seen_at) }}
        </div>
        <button
          class="copy-button"
          type="button"
          data-testid="copy-random"
          @click="copyRandomContent"
        >
          一键复制
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useToast } from '../composables/useToast'

const content = ref(null)
const loading = ref(false)
const error = ref(null)
const { showToast } = useToast()

const formatLastSeen = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    throw new Error('最后出现时间格式无效')
  }
  return date.toLocaleString()
}

const copyRandomContent = async () => {
  if (!content.value?.content) {
    throw new Error('随机弹幕内容为空，无法复制')
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content.value.content)
      showToast('复制成功', { type: 'success', duration: 1800 })
      return
    }

    const textArea = document.createElement('textarea')
    textArea.value = content.value.content
    textArea.setAttribute('readonly', '')
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    showToast('复制成功', { type: 'success', duration: 1800 })
  } catch (_e) {
    error.value = '复制失败，请手动复制'
  }
}

const fetchRandom = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/random')
    if (!response.ok) {
      throw new Error(`请求失败，状态码：${response.status}`)
    }
    const data = await response.json()
    if (typeof data.content !== 'string' || !data.content.trim()) {
      throw new Error('随机弹幕内容无效')
    }
    if (!Number.isInteger(data.count) || data.count < 1) {
      throw new Error('随机弹幕次数无效')
    }
    if (!data.last_seen_at) {
      throw new Error('随机弹幕最后出现时间缺失')
    }
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
  color: var(--color-heading);
}

.controls {
  margin-bottom: 20px;
}

.random-btn {
  padding: 10px 20px;
  background-color: var(--color-accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.random-btn:hover:not(:disabled) {
  background-color: var(--color-accent-strong);
}

.random-btn:disabled {
  background-color: var(--color-primary-disabled);
  cursor: not-allowed;
}

.error-message {
  color: var(--color-error);
  margin-bottom: 10px;
  padding: 15px;
  background-color: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: 4px;
}

.result-container {
  margin-top: 20px;
  animation: fadeIn 0.5s ease-in-out;
}

.danmu-card {
  border: 1px solid var(--color-divider);
  padding: 20px;
  border-radius: 8px;
  background-color: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.danmu-content {
  font-size: 20px;
  font-weight: 500;
  margin-bottom: 15px;
  color: var(--color-heading);
  line-height: 1.5;
}

.random-meta {
  color: var(--color-muted);
  font-size: 14px;
  margin-bottom: 8px;
}

.copy-button {
  padding: 6px 10px;
  border: 1px solid var(--color-border-muted);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-heading-strong);
  cursor: pointer;
  white-space: nowrap;
}

.copy-button:hover {
  background: var(--color-surface-hover);
}


@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
