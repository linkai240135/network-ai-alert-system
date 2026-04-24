<template>
  <div class="page-stack">
    <div class="chain-overview-grid chain-overview-grid-subtle train-stage-grid">
      <div v-for="item in stageItems" :key="item.title" class="chain-node-card">
        <span>{{ item.step }}</span>
        <strong>{{ item.title }}</strong>
      </div>
    </div>

    <PanelCard title="训练任务概览">
      <template #extra>
        <el-button type="primary" :loading="loading" @click="handleTrain">重新训练</el-button>
      </template>

      <div v-if="latestTraining" class="summary-grid summary-grid-wide">
        <div class="summary-item"><span>数据源</span><strong>{{ latestTraining.data_source_name || 'CICIDS2017 Real Flow Dataset' }}</strong></div>
        <div class="summary-item"><span>原始样本</span><strong>{{ formatNumber(latestTraining.source_dataset_size) }}</strong></div>
        <div class="summary-item"><span>训练样本</span><strong>{{ formatNumber(latestTraining.dataset_size) }}</strong></div>
        <div class="summary-item"><span>训练占比</span><strong>{{ formatRatio(latestTraining.training_ratio) }}</strong></div>
        <div class="summary-item"><span>生产模型</span><strong>{{ latestTraining.best_model || '--' }}</strong></div>
        <div class="summary-item"><span>未知检测器</span><strong>{{ latestTraining.detector_name || 'DeepSVDD' }}</strong></div>
      </div>

      <div class="trust-note-card">
        <strong>可信说明</strong>
        <p>本页不再用单个高分指标代表整体效果。多模型表展示测试集加权指标，实际可信性同时参考宏平均指标、弱类表现、未知异常召回以及人工反馈闭环。</p>
      </div>
    </PanelCard>

    <div class="two-column">
      <PanelCard title="生产模型可信快照">
        <div class="summary-grid">
          <div class="summary-item"><span>加权 F1</span><strong>{{ formatScore(weightedF1) }}</strong></div>
          <div class="summary-item"><span>宏平均 F1</span><strong>{{ formatScore(macroF1) }}</strong></div>
          <div class="summary-item"><span>宏平均 Recall</span><strong>{{ formatScore(macroRecall) }}</strong></div>
          <div class="summary-item"><span>最弱类别</span><strong>{{ weakestClass?.label || '--' }}</strong></div>
          <div class="summary-item"><span>最弱类别 F1</span><strong>{{ formatScore(weakestClass?.f1) }}</strong></div>
          <div class="summary-item"><span>最弱类别 Recall</span><strong>{{ formatScore(weakestClass?.recall) }}</strong></div>
        </div>
      </PanelCard>

      <PanelCard title="未知异常与校准能力">
        <div class="summary-grid">
          <div class="summary-item"><span>Benign Recall</span><strong>{{ formatScore(latestTraining?.detector_metrics?.benign_recall) }}</strong></div>
          <div class="summary-item"><span>Attack Recall</span><strong>{{ formatScore(latestTraining?.detector_metrics?.attack_recall) }}</strong></div>
          <div class="summary-item"><span>阈值分位</span><strong>{{ formatScore(latestTraining?.detector_metrics?.selected_quantile) }}</strong></div>
          <div class="summary-item"><span>Conformal 显著性</span><strong>{{ formatScore(latestTraining?.conformal_significance) }}</strong></div>
          <div class="summary-item"><span>解释引擎</span><strong>{{ latestTraining?.explanation_engine || '--' }}</strong></div>
          <div class="summary-item"><span>反馈样本</span><strong>{{ formatNumber(latestTraining?.feedback_loop_count) }}</strong></div>
        </div>
      </PanelCard>
    </div>

    <PanelCard title="多模型测试集对比">
      <div class="trust-inline-note">
        以下结果为测试集加权指标，适合观察总体稳定性，不直接代表长尾攻击类别的识别效果。
      </div>
      <el-table v-if="displayMetricItems.length" :data="displayMetricItems" stripe border>
        <el-table-column prop="name" label="模型" min-width="170" />
        <el-table-column prop="family" label="类别" min-width="120" />
        <el-table-column prop="accuracyText" label="Accuracy" min-width="120" />
        <el-table-column prop="precisionText" label="Precision" min-width="120" />
        <el-table-column prop="recallText" label="Recall" min-width="120" />
        <el-table-column prop="f1Text" label="Weighted F1" min-width="120" />
        <el-table-column label="定位" min-width="140">
          <template #default="{ row }">
            <el-tag v-if="row.name === latestTraining?.best_model" type="primary">生产模型</el-tag>
            <el-tag v-else-if="row.name === latestTraining?.benchmark_best_model" type="warning">传统基线最优</el-tag>
            <span v-else>对比实验</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无数据" />
    </PanelCard>

    <div class="two-column">
      <PanelCard title="类别级评估">
        <el-table v-if="perClassRows.length" :data="perClassRows" stripe border>
          <el-table-column prop="label" label="类别" min-width="150" />
          <el-table-column prop="support" label="样本数" min-width="90" />
          <el-table-column prop="precisionText" label="Precision" min-width="110" />
          <el-table-column prop="recallText" label="Recall" min-width="110" />
          <el-table-column prop="f1Text" label="F1" min-width="110" />
          <el-table-column label="评估结论" min-width="120">
            <template #default="{ row }">
              <el-tag :type="row.flagType">{{ row.flagText }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无数据" />
      </PanelCard>

      <PanelCard title="类别难度画像">
        <InsightBarChart
          v-if="classDifficultyItems.length"
          :items="classDifficultyItems"
          category-key="name"
          value-key="value"
          series-name="F1"
          color="#c2410c"
        />
        <el-empty v-else description="暂无数据" />
      </PanelCard>
    </div>

    <div class="two-column">
      <PanelCard title="混淆矩阵">
        <ConfusionMatrixChart
          v-if="latestTraining && (latestTraining.confusion_matrix || []).length"
          :labels="latestTraining.class_labels || []"
          :matrix="latestTraining.confusion_matrix || []"
        />
        <el-empty v-else description="暂无数据" />
      </PanelCard>

      <PanelCard title="训练历史趋势">
        <LineTrendChart
          v-if="trendData && (trendData.labels || []).length"
          :labels="trendData.labels || []"
          :values="trendData.f1Series || []"
          series-name="最高 Weighted F1"
        />
        <el-empty v-else description="暂无数据" />
      </PanelCard>
    </div>

    <PanelCard title="训练历史记录">
      <el-empty v-if="!history.length" description="暂无记录" />
      <el-timeline v-else>
        <el-timeline-item v-for="item in history" :key="item.id" :timestamp="item.created_at" placement="top">
          <div class="timeline-card">
            <strong>生产模型：{{ item.best_model }}</strong>
            <p>训练样本 {{ formatNumber(item.dataset_size) }}，类别 {{ item.class_count }}，特征 {{ item.feature_count }}。</p>
            <p v-if="item.source_dataset_size">原始样本 {{ formatNumber(item.source_dataset_size) }}，进入训练前完成清洗、采样与反馈样本融合。</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </PanelCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchTrainingHistory, fetchTrainingTrends, triggerTraining } from '../api/dashboard'
import ConfusionMatrixChart from '../components/ConfusionMatrixChart.vue'
import InsightBarChart from '../components/InsightBarChart.vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import PanelCard from '../components/PanelCard.vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const loading = ref(false)
const history = ref([])
const trendData = ref(null)
const latestTraining = computed(() => store.latestTraining)
const metricItems = computed(() => latestTraining.value?.models || latestTraining.value?.metrics || [])

const stageItems = [
  { step: '01', title: '真实数据接入' },
  { step: '02', title: '多模型对比训练' },
  { step: '03', title: '弱类风险评估' },
  { step: '04', title: '未知异常校准' },
]

const classificationReport = computed(() => latestTraining.value?.classification_report || {})

const perClassRows = computed(() =>
  Object.entries(classificationReport.value || {})
    .filter(([name]) => !['accuracy', 'macro avg', 'weighted avg'].includes(name))
    .map(([name, item]) => {
      const precision = Number(item?.precision || 0)
      const recall = Number(item?.recall || 0)
      const f1 = Number(item?.['f1-score'] || 0)
      let flagText = '稳定'
      let flagType = 'success'

      if (f1 < 0.3 || recall < 0.3) {
        flagText = '重点优化'
        flagType = 'danger'
      } else if (f1 < 0.7 || recall < 0.7) {
        flagText = '仍有风险'
        flagType = 'warning'
      }

      return {
        label: name,
        support: Number(item?.support || 0),
        precision,
        recall,
        f1,
        precisionText: precision.toFixed(4),
        recallText: recall.toFixed(4),
        f1Text: f1.toFixed(4),
        flagText,
        flagType,
      }
    })
    .sort((a, b) => a.f1 - b.f1),
)

const weightedF1 = computed(() => Number(classificationReport.value?.['weighted avg']?.['f1-score'] || 0))
const macroF1 = computed(() => Number(classificationReport.value?.['macro avg']?.['f1-score'] || 0))
const macroRecall = computed(() => Number(classificationReport.value?.['macro avg']?.recall || 0))
const weakestClass = computed(() => perClassRows.value[0] || null)

const displayMetricItems = computed(() => {
  const rank = (name) => {
    if (name === latestTraining.value?.best_model) return 0
    if (name === latestTraining.value?.benchmark_best_model) return 1
    return 2
  }

  return [...metricItems.value]
    .sort((a, b) => {
      const rankDiff = rank(a.name) - rank(b.name)
      if (rankDiff !== 0) return rankDiff
      return Number(b.f1_score || 0) - Number(a.f1_score || 0)
    })
    .map((item) => ({
      ...item,
      family: item.family || '--',
      accuracyText: Number(item.accuracy || 0).toFixed(4),
      precisionText: Number(item.precision || 0).toFixed(4),
      recallText: Number(item.recall || 0).toFixed(4),
      f1Text: Number(item.f1_score || 0).toFixed(4),
    }))
})

const classDifficultyItems = computed(() =>
  perClassRows.value.slice(0, 8).map((item) => ({
    name: item.label,
    value: Number((item.f1 * 100).toFixed(2)),
  })),
)

const formatNumber = (value) => Number(value || 0).toLocaleString('zh-CN')
const formatScore = (value) => (value == null ? '--' : `${(Number(value) * 100).toFixed(2)}%`)
const formatRatio = (value) => (value == null ? '--' : `${(Number(value) * 100).toFixed(2)}%`)

const loadHistory = async () => {
  try {
    const response = await fetchTrainingHistory()
    history.value = response.data.items || []
  } catch {
    history.value = []
  }
}

const loadTrends = async () => {
  try {
    const response = await fetchTrainingTrends()
    trendData.value = response.data
  } catch {
    trendData.value = null
  }
}

const handleTrain = async () => {
  loading.value = true
  try {
    await triggerTraining()
    await store.bootstrap()
    await loadHistory()
    await loadTrends()
    ElMessage.success('训练任务已完成，结果已更新')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!store.latestTraining) {
    await store.bootstrap()
  }
  await loadHistory()
  await loadTrends()
})
</script>
