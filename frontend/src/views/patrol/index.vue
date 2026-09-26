<template>
  <section class="page" data-module="patrol">
    <header class="page-head">
      <div>
        <h2>巡查任务管理</h2>
        <p class="page-desc">维护巡查单，围绕巡查单号、巡查路线、巡查人员、巡查日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记巡查单</button>
        <button class="btn" type="button" :disabled="exporting" @click="exportRows">
          {{ exporting ? '导出中…' : '导出巡查任务清单' }}
        </button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field.key" class="filter-item">
        <span>{{ field.label }}</span>
        <input v-model="filters[field.key]" :placeholder="`按${field.label}检索`" />
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
          <td :colspan="columns.length + 1" class="empty-state">暂无符合条件的巡查任务（已作废的巡查单不显示），可调整筛选条件或先登记巡查单</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条巡查任务记录</span>
      <span v-if="message" class="error-text">{{ message }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type FilterKey = 'keyword' | 'route' | 'person'

const ENDPOINT = '/api/patrol'
const columns = ["巡查单号", "巡查路线", "巡查人员", "巡查日期", "巡查里程", "发现问题数", "巡查时长", "巡查状态"]
const actions = ["派发巡查", "提交结果", "作废巡查"]
const statuses = ["待派发", "巡查中", "已提交", "已作废"]
const stats = [{"label": "待派发巡查", "value": 0}, {"label": "巡查中任务", "value": 0}, {"label": "本月发现问题", "value": 0}]

// 筛选项的 key 与后端查询参数一一对应，列表与导出共用同一份查询条件
const filterFields: { key: FilterKey; label: string }[] = [
  { key: 'keyword', label: '巡查单号' },
  { key: 'route', label: '巡查路线' },
  { key: 'person', label: '巡查人员' },
]

const rows = ref<Row[]>([])
const total = ref(0)
const message = ref('')
const exporting = ref(false)
const filters = ref<Record<FilterKey, string>>({ keyword: '', route: '', person: '' })

function buildQuery() {
  const params = new URLSearchParams()
  for (const field of filterFields) {
    const value = filters.value[field.key].trim()
    if (value) {
      params.set(field.key, value)
    }
  }
  return params.toString()
}

function resetFilters() {
  filters.value = { keyword: '', route: '', person: '' }
  void reload()
}

async function exportRows() {
  if (exporting.value) {
    return
  }
  message.value = ''
  exporting.value = true
  try {
    // 与列表完全相同的查询条件；失败或中断时不会落盘，重新点击即可重来
    const response = await request(`${ENDPOINT}/export?${buildQuery()}`)
    if (!response.ok) {
      let detail = ''
      try {
        detail = String((await response.json())?.detail ?? '')
      } catch {
        detail = ''
      }
      throw new Error(detail || `导出失败（${response.status}），请调整条件后重试`)
    }
    // 等响应完整到达后再生成文件，避免中断产生半个文件
    const content = await response.text()
    const blob = new Blob([content], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '巡查任务清单.json'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '巡查任务导出失败，请重试'
  } finally {
    exporting.value = false
  }
}

function openCreate() {
  message.value = '巡查单登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  message.value = ''
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
    message.value = error instanceof Error ? error.message : '巡查任务操作失败'
  }
}

async function reload() {
  message.value = ''
  try {
    const response = await request(`${ENDPOINT}?${buildQuery()}`)
    if (!response.ok) {
      throw new Error('巡查单列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    message.value = error instanceof Error ? error.message : '巡查任务列表读取失败'
  }
}

onMounted(reload)
</script>
