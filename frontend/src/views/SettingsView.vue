<template>
  <div class="page-stack">
    <div class="chain-overview-grid train-stage-grid">
      <div v-for="item in supportChain" :key="item.title" class="chain-node-card">
        <span>{{ item.step }}</span>
        <strong>{{ item.title }}</strong>
      </div>
    </div>

    <PanelCard title="系统设置" subtitle="统一管理训练、检测阈值与智能研判相关参数。">
      <el-form label-position="top">
        <el-form-item v-for="item in editableSettings" :key="item.key" :label="item.description || item.key">
          <el-input v-model="item.value" />
        </el-form-item>
      </el-form>
      <div class="action-row">
        <el-button type="primary" :loading="loading" @click="saveSettings">保存设置</el-button>
      </div>
    </PanelCard>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchSettings, updateSettings } from '../api/dashboard'
import PanelCard from '../components/PanelCard.vue'

const editableSettings = ref([])
const loading = ref(false)
const supportChain = [
  { step: '01', title: '数据接入', description: '支持 CICIDS2017 真实数据导入、清洗与训练样本沉淀。' },
  { step: '02', title: '模型训练', description: '由多类分类与异常检测模块构成双层检测能力。' },
  { step: '03', title: '可信校准', description: '利用可信校准机制输出更稳健的预测区间与标签集合。' },
  { step: '04', title: '智能研判', description: '生成告警分析、事件报告与处置建议，支撑完整业务闭环。' },
]

const loadSettings = async () => {
  const response = await fetchSettings()
  editableSettings.value = response.data.items
}

const saveSettings = async () => {
  loading.value = true
  try {
    const payload = Object.fromEntries(editableSettings.value.map((item) => [item.key, item.value]))
    await updateSettings(payload)
    ElMessage.success('系统设置已更新')
    await loadSettings()
  } finally {
    loading.value = false
  }
}

onMounted(loadSettings)
</script>
