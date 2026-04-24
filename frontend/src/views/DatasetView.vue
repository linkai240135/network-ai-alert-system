<template>
  <div v-if="datasetOverview" class="page-stack">
    <PanelCard title="数据集总览" subtitle="统一管理真实数据来源、样本规模、导入任务与训练准备状态">
      <template #extra>
        <el-upload :auto-upload="false" :limit="8" multiple :on-change="onFileChange" accept=".csv">
          <template #trigger>
            <el-button type="primary">上传 CICIDS2017 CSV</el-button>
          </template>
        </el-upload>
        <el-button type="success" :loading="uploading" @click="submitImport">单文件导入并训练</el-button>
        <el-button type="warning" :loading="uploadingBatch" @click="submitBatchImport">多文件批量导入</el-button>
      </template>

      <div class="summary-grid summary-grid-wide">
        <div class="summary-item">
          <span>数据集名称</span>
          <strong>{{ datasetOverview.name }}</strong>
        </div>
        <div class="summary-item">
          <span>样本总量</span>
          <strong>{{ formatNumber(datasetOverview.total) }}</strong>
        </div>
        <div class="summary-item">
          <span>数据源说明</span>
          <strong>真实流量导入链路</strong>
        </div>
      </div>
    </PanelCard>

    <div class="two-column">
      <PanelCard title="类别分布" subtitle="展示当前训练数据中不同攻击标签的样本构成">
        <div class="distribution-list">
          <div v-for="(value, key) in datasetOverview.distribution || {}" :key="key" class="distribution-item">
            <span>{{ key }}</span>
            <strong>{{ formatNumber(value) }}</strong>
          </div>
        </div>
      </PanelCard>

      <PanelCard title="数据来源构成" subtitle="突出系统已经正式接入真实来源数据，而不是纯演示样本">
        <div class="distribution-list distribution-list-compact">
          <div v-for="(value, key) in datasetOverview.sources || {}" :key="key" class="distribution-item">
            <span>{{ key }}</span>
            <strong>{{ formatNumber(value) }}</strong>
          </div>
        </div>
      </PanelCard>
    </div>

    <PanelCard title="导入记录" subtitle="记录每次数据接入任务的文件名、导入条数、跳过条数和处理时间">
      <template #extra>
        <el-button @click="handleExportImportJobs">导出导入记录</el-button>
      </template>

      <el-empty v-if="!paginatedImportJobs.length" description="暂无记录" />
      <el-table v-else :data="paginatedImportJobs" stripe border>
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="source_type" label="来源" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="imported_count" label="导入数" width="110" />
        <el-table-column prop="skipped_count" label="跳过数" width="110" />
        <el-table-column prop="created_at" label="时间" min-width="170" />
      </el-table>

      <el-pagination
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="importJobs.length"
        :page-size="importPageSize"
        :current-page="importPage"
        @current-change="importPage = $event"
      />
    </PanelCard>

    <PanelCard title="样本预览" subtitle="查看已入库样本的字段结构，证明数据处理结果已经进入系统数据库">
      <template #extra>
        <el-button @click="handleExportPreview">导出预览样本</el-button>
      </template>

      <el-empty v-if="!paginatedPreview.length" description="暂无样本" />
      <el-table v-else :data="paginatedPreview" stripe border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="source" label="来源" min-width="150" />
        <el-table-column prop="label" label="标签" width="120" />
        <el-table-column prop="flow_duration" label="flow_duration" min-width="130" />
        <el-table-column prop="packet_rate" label="packet_rate" min-width="120" />
        <el-table-column prop="byte_rate" label="byte_rate" min-width="120" />
        <el-table-column prop="syn_rate" label="syn_rate" min-width="120" />
      </el-table>

      <el-pagination
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="datasetOverview.preview?.length || 0"
        :page-size="previewPageSize"
        :current-page="previewPage"
        @current-change="previewPage = $event"
      />
    </PanelCard>
  </div>

  <el-empty v-else description="加载中" />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchImportJobs, uploadCicidsDataset, uploadCicidsDatasetBatch } from '../api/dashboard'
import PanelCard from '../components/PanelCard.vue'
import { useAppStore } from '../stores/app'
import { exportRowsToCsv } from '../utils/export'

const store = useAppStore()
const datasetOverview = computed(() => store.datasetOverview)
const importJobs = ref([])
const uploading = ref(false)
const uploadingBatch = ref(false)
const currentFiles = ref([])
const importPage = ref(1)
const previewPage = ref(1)
const importPageSize = 5
const previewPageSize = 6

const formatNumber = (value) => Number(value || 0).toLocaleString('zh-CN')

const paginatedImportJobs = computed(() => {
  const start = (importPage.value - 1) * importPageSize
  return importJobs.value.slice(start, start + importPageSize)
})

const paginatedPreview = computed(() => {
  const preview = datasetOverview.value?.preview || []
  const start = (previewPage.value - 1) * previewPageSize
  return preview.slice(start, start + previewPageSize)
})

const loadImportJobs = async () => {
  try {
    const response = await fetchImportJobs()
    importJobs.value = response.data.items || []
  } catch {
    importJobs.value = []
  }
}

const onFileChange = (file) => {
  if (!file?.raw) return
  const exists = currentFiles.value.find((item) => item.name === file.raw.name)
  if (!exists) currentFiles.value.push(file.raw)
}

const submitImport = async () => {
  if (!currentFiles.value.length) {
    ElMessage.warning('请先选择 CICIDS2017 CSV 文件')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', currentFiles.value[0])
    await uploadCicidsDataset(formData)
    ElMessage.success('数据导入完成，训练链路已刷新')
    await store.bootstrap()
    await loadImportJobs()
    importPage.value = 1
  } finally {
    uploading.value = false
  }
}

const submitBatchImport = async () => {
  if (!currentFiles.value.length) {
    ElMessage.warning('请先选择至少一个 CSV 文件')
    return
  }
  uploadingBatch.value = true
  try {
    const formData = new FormData()
    currentFiles.value.forEach((file) => formData.append('files', file))
    await uploadCicidsDatasetBatch(formData)
    ElMessage.success('批量导入完成，训练任务已触发')
    await store.bootstrap()
    await loadImportJobs()
    importPage.value = 1
  } finally {
    uploadingBatch.value = false
  }
}

const handleExportImportJobs = () => exportRowsToCsv('dataset_import_jobs.csv', importJobs.value)
const handleExportPreview = () => exportRowsToCsv('dataset_preview.csv', datasetOverview.value?.preview || [])

onMounted(async () => {
  if (!store.datasetOverview) {
    await store.bootstrap()
  }
  await loadImportJobs()
})
</script>
