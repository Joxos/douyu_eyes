<template>
  <div class="search-page">
    <h1>Search</h1>
    
    <div class="search-controls">
      <input 
        v-model="query" 
        @keyup.enter="performSearch"
        placeholder="Enter search terms..."
        class="search-input"
        data-testid="search-input"
      />
      <button 
        @click="performSearch"
        class="search-button"
        data-testid="search-submit"
        :disabled="loading"
      >
        Search
      </button>
    </div>

    <div v-if="loading" class="loading-state">Loading results...</div>
    
    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="results.length > 0" class="results-container" data-testid="search-results">
      <div v-for="(item, index) in results" :key="index" class="search-result-item">
        <!-- Render result strings as plain text -->
        <div>{{ item }}</div>
      </div>
    </div>
    
    <div v-else-if="!loading && hasSearched" class="no-results">
      No results found.
    </div>

    <div class="pagination-controls" v-if="hasSearched && (results.length > 0 || offset > 0)">
      <button 
        @click="prevPage" 
        :disabled="offset === 0 || loading"
        class="pagination-btn"
      >
        Previous
      </button>
      <span class="page-info">Page {{ currentPage }}</span>
      <button 
        @click="nextPage" 
        :disabled="results.length < limit || loading"
        class="pagination-btn"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const query = ref('')
const activeQuery = ref('')
const results = ref([])
const loading = ref(false)
const error = ref(null)
const offset = ref(0)
const limit = 20
const hasSearched = ref(false)

const currentPage = computed(() => Math.floor(offset.value / limit) + 1)

const performSearch = async () => {
  if (!query.value.trim()) return
  
  activeQuery.value = query.value
  offset.value = 0
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
      offset: offset.value.toString()
    })
    
    // In development with Vite proxy, this goes to http://127.0.0.1:8000/api/search
    const response = await fetch(`/api/search?${params.toString()}`)
    
    if (!response.ok) {
      // Try to extract a helpful error message from the backend JSON { detail }
      let errMsg = `Search failed: ${response.status} ${response.statusText}`
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
    const items = Array.isArray(data.items) ? data.items : []
    results.value = [...new Set(items)]
    // update offset if backend provided it
    if (typeof data.offset === 'number') offset.value = data.offset
    
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
  // Only allow next page if we have a full page of results
  // If results < limit, we are at the end
  if (results.value.length >= limit) {
    offset.value += limit
    await fetchResults()
  }
}
</script>

<style scoped>
.search-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: sans-serif;
  /* Ensure page text is high-contrast on white backgrounds */
  color: #1f2937; /* dark slate */
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
  border: 1px solid #ccc;
  border-radius: 4px;
  /* Inputs should be readable on white backgrounds */
  color: #1f2937;
  background-color: #ffffff;
}

.search-button {
  padding: 8px 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.search-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.search-result-item {
  border: 1px solid #eee;
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 4px;
  background-color: #f9f9f9;
  /* Ensure result text is dark and readable */
  color: #1f2937;
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
}

.page-info {
  color: #1f2937; /* dark page info / pagination label color */
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  color: red;
  margin-bottom: 10px;
  padding: 10px;
  background-color: #ffeaea;
  border-radius: 4px;
}

.loading-state {
  text-align: center;
  margin: 20px 0;
  color: #666;
}

.no-results {
  text-align: center;
  margin: 20px 0;
  color: #666;
  font-style: italic;
}
</style>
