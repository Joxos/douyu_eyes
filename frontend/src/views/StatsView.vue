<template>
  <div class="stats-page">
    <h1>统计</h1>

    <div v-if="isLoading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else class="content">
      <div class="cards">
        <div class="card" data-testid="unique-count">
          <h2>历史唯一弹幕数</h2>
          <p>{{ uniqueCount }}</p>
        </div>
        <div class="card" data-testid="current-minute-count">
          <h2>当前分钟弹幕数</h2>
          <p>{{ currentMinuteCount }}</p>
        </div>
      </div>

      <div class="table-container">
        <h2>Top 20 弹幕内容</h2>
        <table data-testid="top20-table">
          <thead>
            <tr>
              <th>内容</th>
              <th>次数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in top20" :key="index">
              <td>{{ item.content }}</td>
              <td>{{ item.count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const uniqueCount = ref(0)
const currentMinuteCount = ref(0)
const top20 = ref([])
const isLoading = ref(true)
const error = ref(null)
let pollingInterval = null

// NOTE: backend↔frontend contract is strict. Assume data.top20 is
// an array of { content, count } and assign directly.

const fetchSummary = async () => {
  try {
    const res = await fetch('/api/stats/summary')
    if (!res.ok) throw new Error('获取统计摘要失败')
    const data = await res.json()
    uniqueCount.value = data.unique_count_all_time
    currentMinuteCount.value = data.current_minute_count
    // Strict contract: consume backend schema as-is
    top20.value = data.top20
  } catch (err) {
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

const fetchCurrentMinute = async () => {
  try {
    const res = await fetch('/api/stats/current-minute')
    if (!res.ok) throw new Error('获取当前分钟统计失败')
    const data = await res.json()
    currentMinuteCount.value = data.count
  } catch (err) {
    console.error('轮询错误:', err)
  }
}

onMounted(() => {
  fetchSummary()
  pollingInterval = setInterval(fetchCurrentMinute, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
</script>

<style scoped>
.stats-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}
.cards {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}
.card {
  border: 1px solid #ddd;
  padding: 20px;
  border-radius: 8px;
  background: #fff;
  flex: 1;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.card h2 {
  margin-top: 0;
  font-size: 1.1em;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.card p {
  font-size: 2.5em;
  font-weight: bold;
  margin: 10px 0 0;
  color: #333;
}
.table-container {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ddd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.table-container h2 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.2em;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}
th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #444;
}
tr:last-child td {
  border-bottom: none;
}
.error {
  color: #d32f2f;
  background: #ffebee;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.loading {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 40px;
}
</style>
