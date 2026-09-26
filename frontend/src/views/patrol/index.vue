<template>
  <section class="page" data-module="patrol">
    <header class="page-head">
      <div>
        <h2>巡查任务管理</h2>
        <p class="page-desc">维护巡查单，围绕巡查单号、巡查路线、巡查人员、巡查日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记巡查单</button>
        <button class="btn" type="button" @click="exportRows">导出巡查任务清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <label class="filter-item">
        <span>巡查状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无巡查任务数据，可先登记巡查单</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条巡查任务记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/patrol'
const columns = ["巡查单号", "巡查路线", "巡查人员", "巡查日期", "巡查里程", "发现问题数", "巡查时长", "巡查状态"]
const actions = ["派发巡查", "提交结果", "作废巡查"]
const statuses = ["待派发", "巡查中", "已提交", "已作废"]
const stats = [{"label": "待派发巡查", "value": 0}, {"label": "巡查中任务", "value": 0}, {"label": "本月发现问题", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const statusFilter = ref('')
const filterFields = columns.slice(0, 3)

function buildQuery() {
  const params = new URLSearchParams()
  const keyword = (filters.value['巡查单号'] ?? '').trim()
  const route = (filters.value['巡查路线'] ?? '').trim()
  const person = (filters.value['巡查人员'] ?? '').trim()
  if (keyword) params.set('keyword', keyword)
  if (route) params.set('route', route)
  if (person) params.set('person', person)
  if (statusFilter.value) params.set('status', statusFilter.value)
  return params.toString()
}

function resetFilters() {
  filters.value = {}
  statusFilter.value = ''
  void reload()
}

async function exportRows() {
  errorMessage.value = ''
  const query = buildQuery()
  try {
    const response = await request(`${ENDPOINT}/export?${query}`)
    if (!response.ok) {
      let detail = '巡查任务清单导出失败，请稍后重试'
      try {
        const payload = await response.json()
        if (typeof payload?.detail === 'string') detail = payload.detail
      } catch {
        // 错误响应不是 JSON 时保留默认提示
      }
      throw new Error(detail)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '巡查任务清单.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '巡查任务清单导出失败，请稍后重试'
  }
}

function openCreate() {
  errorMessage.value = '巡查单登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('巡查任务动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '巡查任务操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = buildQuery()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('巡查单列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '巡查任务列表读取失败'
  }
}

onMounted(reload)
</script>
