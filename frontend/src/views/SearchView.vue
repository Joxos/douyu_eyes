<template>
  <div class="search-page">
    <h1>搜索</h1>
    
    <div class="search-controls">
      <input 
        v-model="query" 
        @keyup.enter="performSearch"
        placeholder="请输入搜索关键词..."
        class="search-input"
        data-testid="search-input"
      />
      <button 
        @click="performSearch"
        class="search-button"
        data-testid="search-submit"
        :disabled="loading"
      >
        搜索
      </button>
      <select v-model="sortMode" @change="changeSort" class="sort-select" aria-label="排序方式">
        <option value="count">按出现次数</option>
        <option value="last_seen">按最后出现时间</option>
      </select>
    </div>

    <div v-if="loading" class="loading-state">正在加载搜索结果...</div>
    
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-if="results.length > 0" class="results-container" data-testid="search-results">
      <div v-for="(item, index) in results" :key="index" class="search-result-item">
        <div class="search-result-main">
          <div class="search-result-content">{{ item.content }}</div>
          <div v-if="sortMode === 'count'" class="search-result-count">出现次数：{{ item.count }}</div>
          <div v-else class="search-result-last-seen" :data-testid="`last-seen-${index}`">
            最后出现时间：{{ formatLastSeen(item.last_seen_at) }}
          </div>
        </div>
        <button
          class="copy-button"
          type="button"
          :data-testid="`copy-result-${index}`"
          @click="copyContent(item.content)"
        >
          一键复制
        </button>
      </div>
    </div>
    
    <div v-else-if="!loading && hasSearched" class="no-results">
      未找到相关结果。
    </div>

    <div class="pagination-controls" v-if="hasSearched && (results.length > 0 || offset > 0)">
      <button 
        @click="prevPage" 
        :disabled="offset === 0 || loading"
        class="pagination-btn"
      >
        上一页
      </button>
      <span class="page-info">第 {{ currentPageDisplay }} / {{ totalPagesDisplay }} 页（共 {{ totalResults }} 条）</span>
      <button 
        @click="nextPage" 
        :disabled="!canGoNext || loading"
        class="pagination-btn"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToast } from '../composables/useToast'

const query = ref('')
const activeQuery = ref('')
const results = ref([])
const loading = ref(false)
const error = ref(null)
const offset = ref(0)
const limit = 20
const hasSearched = ref(false)
const sortMode = ref('count')
const totalResults = ref(0)
const totalPages = ref(1)
const currentPageFromServer = ref(1)
const { showToast } = useToast()

const showCopySuccess = () => {
  showToast('复制成功', { type: 'success', duration: 1800 })
}

const formatLastSeen = (value) => {
  if (value === null || typeof value === 'undefined') return '未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知'
  return date.toLocaleString()
}

const copyContent = async (content) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content)
      showCopySuccess()
      return
    }

    const textArea = document.createElement('textarea')
    textArea.value = content
    textArea.setAttribute('readonly', '')
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    showCopySuccess()
  } catch (err) {
    error.value = '复制失败，请手动复制'
  }
}

const currentPage = computed(() => Math.floor(offset.value / limit) + 1)
const currentPageDisplay = computed(() => {
  const page = Number(currentPageFromServer.value)
  return Number.isFinite(page) && page > 0 ? page : currentPage.value
})
const totalPagesDisplay = computed(() => Math.max(1, totalPages.value))
const canGoNext = computed(() => currentPageDisplay.value < totalPagesDisplay.value)

const performSearch = async () => {
  if (!query.value.trim()) return
  
  activeQuery.value = query.value
  offset.value = 0
  totalResults.value = 0
  totalPages.value = 1
  currentPageFromServer.value = 1
  await fetchResults()
}

const fetchResults = async () => {
  if (!activeQuery.value.trim()) return

  loading.value = true
  error.value = null
  hasSearched.value = true
  
  try {
    const params = new URLSearchParams({
      q: activeQuery.value,
      limit: limit.toString(),
      offset: offset.value.toString(),
      sort: sortMode.value,
    })
    
    // In development with Vite proxy, this goes to http://127.0.0.1:8000/api/search
    const response = await fetch(`/api/search?${params.toString()}`)
    
    if (!response.ok) {
      // Try to extract a helpful error message from the backend JSON { detail }
      let errMsg = `搜索失败：${response.status} ${response.statusText}`
      try {
        const errData = await response.json()
        if (errData && typeof errData === 'object' && errData.detail) {
          errMsg = String(errData.detail)
        }
      } catch (e) {
        // ignore JSON parse errors and keep default message
      }
      throw new Error(errMsg)
    }

    const data = await response.json()
    results.value = Array.isArray(data.items) ? data.items : []
    if (sortMode.value === 'last_seen') {
      const missingLastSeen = results.value.some((item) => !item?.last_seen_at)
      if (missingLastSeen) {
        throw new Error('后端未返回有效的最后出现时间，请稍后重试')
      }
    }
    // update offset if backend provided it
    if (typeof data.offset === 'number') offset.value = data.offset
    const parsedTotal = Number(data.total)
    const parsedTotalPages = Number(data.total_pages)
    const parsedCurrentPage = Number(data.current_page)

    if (Number.isFinite(parsedTotal) && parsedTotal >= 0) totalResults.value = parsedTotal
    if (Number.isFinite(parsedTotalPages) && parsedTotalPages >= 1) totalPages.value = parsedTotalPages
    if (Number.isFinite(parsedCurrentPage) && parsedCurrentPage >= 1) currentPageFromServer.value = parsedCurrentPage
    
  } catch (err) {
    error.value = err.message
    results.value = []
  } finally {
    loading.value = false
  }
}

const prevPage = async () => {
  if (offset.value >= limit) {
    offset.value -= limit
    await fetchResults()
  }
}

const nextPage = async () => {
  if (canGoNext.value) {
    offset.value += limit
    await fetchResults()
  }
}

const changeSort = async () => {
  if (!activeQuery.value.trim()) return
  offset.value = 0
  currentPageFromServer.value = 1
  await fetchResults()
}
</script>

<style scoped>
.search-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: sans-serif;
  color: var(--color-heading);
}

.search-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 8px;
  font-size: 16px;
  border: 1px solid var(--color-border-muted);
  border-radius: 4px;
  color: var(--color-heading);
  background-color: var(--color-surface);
}

.search-button {
  padding: 8px 16px;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.sort-select {
  padding: 8px 10px;
  border: 1px solid var(--color-border-muted);
  border-radius: 6px;
  color: var(--color-heading);
  background: var(--color-surface);
}

.search-button:disabled {
  background-color: var(--color-primary-disabled);
  cursor: not-allowed;
}

.search-result-item {
  border: 1px solid var(--color-divider);
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 4px;
  background-color: var(--color-surface-soft);
  color: var(--color-heading);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.search-result-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.search-result-content {
  font-weight: 600;
}

.search-result-count {
  color: var(--color-muted);
  font-size: 14px;
}

.search-result-last-seen {
  color: var(--color-muted);
  font-size: 14px;
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

.search-result-item pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
}

.pagination-btn {
  padding: 5px 10px;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
}

.page-info {
  color: var(--color-heading);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  color: var(--color-error);
  margin-bottom: 10px;
  padding: 10px;
  background-color: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: 4px;
}

.loading-state {
  text-align: center;
  margin: 20px 0;
  color: var(--color-muted);
}

.no-results {
  text-align: center;
  margin: 20px 0;
  color: var(--color-muted);
  font-style: italic;
}
</style>
