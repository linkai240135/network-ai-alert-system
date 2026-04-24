<template>
  <div class="page-stack">
    <PanelCard title="CSV 批量检测" subtitle="上传包含流量特征字段的 CSV 文件，自动完成批量检测与告警生成">
      <el-upload :auto-upload="false" :limit="1" :on-change="onFileChange" accept=".csv">
        <template #trigger>
          <el-button type="primary">选择 CSV 文件</el-button>
        </template>
      </el-upload>
      <div class="action-row">
        <el-button type="success" :loading="loading" @click="submitBatch">开始批量检测</el-button>
      </div>
    </PanelCard>

    <PanelCard title="批量检测结果" subtitle="展示本次批量处理摘要与前 50 条检测结果">
      <template #extra>
        <el-button @click="handleExportResults">导出结果</el-button>
      </template>
      <el-descriptions v-if="summary" :column="3" border>
        <el-descriptions-item label="总条数">{{ summary.total }}</el-descriptions-item>
        <el-descriptions-item label="触发告警">{{ summary.alertCount }}</el-descriptions-item>
        <el-descriptions-item label="未知异常">{{ summary.unknownCount }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-if="summary && !summary.results?.length" description="暂无数据" />
      <el-table v-if="paginatedResults.length" :data="paginatedResults" stripe border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="label" label="类别" width="120" />
        <el-table-column prop="binary_decision" label="第一层判断" width="120" />
        <el-table-column prop="attack_stage" label="攻击阶段" min-width="140" />
        <el-table-column label="风险" width="100">
          <template #default="{ row }">
            <SeverityTag :level="row.risk_level" />
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" />
        <el-table-column prop="created_at" label="时间" min-width="160" />
      </el-table>
      <el-pagination
        v-if="summary?.results?.length"
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="summary.results.length"
        :page-size="pageSize"
        :current-page="page"
        @current-change="page = $event"
      />
    </PanelCard>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { uploadBatchDetection } from '../api/dashboard'
import PanelCard from '../components/PanelCard.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { exportRowsToCsv } from '../utils/export'

const loading = ref(false)
const currentFile = ref(null)
const summary = ref(null)
const page = ref(1)
const pageSize = 8

const paginatedResults = computed(() => {
  if (!summary.value?.results) return []
  const start = (page.value - 1) * pageSize
  return summary.value.results.slice(start, start + pageSize)
})

const onFileChange = (file) => {
  currentFile.value = file.raw
}

const submitBatch = async () => {
  if (!currentFile.value) {
    ElMessage.warning('请先选择 CSV 文件')
    return
  }
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', currentFile.value)
    const response = await uploadBatchDetection(formData)
    summary.value = response.data
    page.value = 1
    ElMessage.success('批量检测完成')
  } finally {
    loading.value = false
  }
}

const handleExportResults = () => {
  if (!summary.value?.results?.length) return
  exportRowsToCsv('batch_detection_results.csv', summary.value.results)
}
</script>
