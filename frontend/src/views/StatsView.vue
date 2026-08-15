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
        <div class="card" data-testid="latest-danmu">
          <h2>最新弹幕</h2>
          <template v-if="latestDanmuTs && latestDanmuContent">
            <p class="latest-time">{{ formatTimestamp(latestDanmuTs) }}</p>
            <div class="latest-content" :title="latestDanmuContent">{{ latestDanmuContent }}</div>
          </template>
          <template v-else>
            <p class="unavailable-state">暂无数据</p>
          </template>
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
const latestDanmuTs = ref(null)
const latestDanmuContent = ref(null)
const top20 = ref([])
const isLoading = ref(true)
const error = ref(null)
let pollingInterval = null

const formatTimestamp = (ts) => {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return '时间格式无效'
  return date.toLocaleString() + ' (本地)'
}

// NOTE: backend↔frontend contract is strict. Assume data.top20 is
// an array of { content, count } and assign directly.

const fetchSummary = async () => {
  try {
    const res = await fetch('/api/stats/summary')
    if (!res.ok) throw new Error('获取统计摘要失败')
    const data = await res.json()
    uniqueCount.value = data.unique_count_all_time
    currentMinuteCount.value = data.current_minute_count
    latestDanmuTs.value = data.latest_danmu_ts
    latestDanmuContent.value = data.latest_danmu_content
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
    console.error('当前分钟轮询错误:', err)
  }
}

const fetchLatestDanmu = async () => {
  try {
    const res = await fetch('/api/stats/latest-danmu')
    if (!res.ok) throw new Error('获取最新弹幕失败')
    const data = await res.json()
    latestDanmuTs.value = data.timestamp
    latestDanmuContent.value = data.content
  } catch (err) {
    console.error('最新弹幕轮询错误:', err)
  }
}

const pollAll = () => {
  fetchCurrentMinute()
  fetchLatestDanmu()
}

onMounted(() => {
  fetchSummary()
  pollingInterval = setInterval(pollAll, 5000)
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
  border: 1px solid var(--color-divider);
  padding: 20px;
  border-radius: 8px;
  background: var(--color-surface);
  flex: 1;
  text-align: center;
  box-shadow: var(--shadow-card);
}
.card h2 {
  margin-top: 0;
  font-size: 1.1em;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.card p {
  font-size: 2.5em;
  font-weight: bold;
  margin: 10px 0 0;
  color: var(--color-heading);
}
.card p.latest-time {
  font-size: 1.25em;
}
.card p.unavailable-state {
  font-size: 1.25em;
  color: var(--color-muted);
  font-weight: normal;
}
.card .latest-content {
  font-size: 0.9em;
  color: var(--color-muted);
  margin-top: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-container {
  background: var(--color-surface);
  border-radius: 8px;
  padding: 20px;
  border: 1px solid var(--color-divider);
  box-shadow: var(--shadow-card);
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
  border-bottom: 1px solid var(--color-divider);
}
th {
  background-color: var(--color-surface-soft);
  font-weight: 600;
  color: var(--color-heading);
}
tr:last-child td {
  border-bottom: none;
}
.error {
  color: var(--color-error);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.loading {
  text-align: center;
  color: var(--color-muted);
  font-style: italic;
  padding: 40px;
}
</style>
