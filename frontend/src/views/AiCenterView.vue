<template>
  <div class="ai-center-page ai-center-premium">
    <div class="ai-console-shell ai-console-shell-premium">
      <aside class="ai-console-sidebar">
        <div class="ai-console-sidebar-head">
          <el-segmented v-model="sourceType" :options="sourceOptions" />
          <el-switch
            v-model="useReasonerMode"
            inline-prompt
            active-text="推理"
            inactive-text="对话"
          />
        </div>

        <div class="ai-console-search">
          <el-input v-model="keyword" placeholder="搜索" clearable @keyup.enter="applyFilter" />
          <el-button type="primary" @click="applyFilter">筛选</el-button>
        </div>

        <div class="ai-console-list-head">
          <strong>{{ sourceType === 'alert' ? '分析对象' : '复盘对象' }}</strong>
          <span>{{ filteredItems.length }} 条</span>
        </div>

        <el-scrollbar class="ai-console-list-scroll">
          <div class="ai-console-list">
            <button
              v-for="item in filteredItems"
              :key="`${sourceType}-${item.id}`"
              type="button"
              class="ai-console-item"
              :class="{ active: activeSource?.id === item.id }"
              @click="selectSource(item)"
            >
              <div class="ai-console-item-top">
                <strong>{{ item.title || item.incident_no || item.attack_type || item.label }}</strong>
                <el-tag size="small" :type="severityTagType(item.risk_level || item.severity)">
                  {{ item.risk_level || item.severity || '中' }}
                </el-tag>
              </div>
              <p>
                {{
                  sourceType === 'alert'
                    ? (item.attack_stage || '阶段待定')
                    : `${item.attack_type || '--'} / ${item.status || '--'}`
                }}
              </p>
              <span>{{ item.created_at || item.last_seen_at || '--' }}</span>
            </button>
          </div>
        </el-scrollbar>
      </aside>

      <section class="ai-console-main">
        <header class="ai-command-header">
          <div class="ai-command-title">
            <span>Security Copilot</span>
            <strong>AI 研判工作区</strong>
          </div>
          <div class="ai-command-status">
            <span>{{ sourceType === 'alert' ? '告警流' : '事件流' }}</span>
            <span>{{ currentModel }}</span>
            <span v-if="activeSource">已绑定上下文</span>
          </div>
        </header>

        <div class="ai-console-stream">
          <div v-if="activeSummary" class="ai-source-summary">
            <div class="ai-source-summary-top">
              <div>
                <span class="ai-source-summary-kicker">{{ sourceType === 'alert' ? '当前告警' : '当前事件' }}</span>
                <strong>{{ activeSummary.title }}</strong>
                <p>{{ activeSummary.subtitle }}</p>
              </div>
              <SeverityTag :level="activeSummary.level" />
            </div>
            <div class="service-card-metrics">
              <span>{{ activeSummary.metaA }}</span>
              <span>{{ activeSummary.metaB }}</span>
              <span>{{ activeSummary.metaC }}</span>
            </div>
            <div class="service-card-desc">{{ activeSummary.desc }}</div>
          </div>

          <div v-if="activeSource" class="analysis-stage-strip">
            <div v-for="item in analysisStageItems" :key="item.title" class="analysis-stage-card">
              <span>{{ item.step }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.value }}</p>
            </div>
          </div>

          <div v-if="sourceEvidenceCards.length" class="evidence-card-grid">
            <div v-for="item in sourceEvidenceCards" :key="item.label" class="evidence-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>

          <div v-if="sourceFeatureItems.length" class="ai-inline-section">
            <div class="ai-inline-section-head">
              <strong>模型证据</strong>
              <span>{{ sourceFeatureItems.length }} 项</span>
            </div>
            <InsightBarChart
              :items="sourceFeatureItems"
              category-key="name"
              value-key="value"
              series-name="贡献度"
              color="#c2410c"
            />
          </div>

          <div v-if="analysisLoading || chatLoading || reportLoading" class="ai-assistant-block ai-assistant-loading">
            <strong>AI 正在生成分析结果</strong>
          </div>

          <div v-if="analysisResult" class="copilot-response-shell">
            <div class="ai-assistant-block ai-assistant-primary">
              <div class="ai-assistant-head">
                <strong>{{ lastActionLabel }}</strong>
                <span>{{ currentModel }}</span>
              </div>
              <p>{{ analysisResult.content }}</p>
            </div>

            <div class="copilot-evidence-column">
              <div v-if="retrievalMetricCards.length" class="evidence-card-grid evidence-card-grid-tight">
                <div v-for="item in retrievalMetricCards" :key="item.label" class="evidence-card">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                  <p>{{ item.desc }}</p>
                </div>
              </div>

              <div v-if="analysisResult?.knowledge_hits?.length" class="ai-inline-section">
                <div class="ai-inline-section-head">
                  <strong>知识证据</strong>
                  <span>{{ analysisResult.knowledge_hits.length }} 条</span>
                </div>
                <div class="insight-list compact-list">
                  <div v-for="item in analysisResult.knowledge_hits" :key="item.id" class="insight-card">
                    <div class="insight-card-top">
                      <strong>{{ item.title }}</strong>
                      <span>{{ item.category }} / {{ item.retrieval_method }} / {{ item.retrieval_engine }}</span>
                    </div>
                    <div class="rag-score-grid">
                      <div>
                        <span>融合</span>
                        <el-progress :percentage="toScorePercent(item.fusion_score)" :stroke-width="8" />
                      </div>
                      <div>
                        <span>关键词</span>
                        <el-progress :percentage="toScorePercent(item.keyword_score)" :stroke-width="8" color="#67c23a" />
                      </div>
                      <div>
                        <span>向量</span>
                        <el-progress :percentage="toScorePercent(item.vector_score)" :stroke-width="8" color="#e6a23c" />
                      </div>
                    </div>
                    <div class="rag-meta-row">
                      <el-tag size="small" type="danger">{{ item.severity }}</el-tag>
                      <el-tag size="small" type="info">{{ item.attack_stage }}</el-tag>
                      <el-tag v-for="term in item.matched_terms || []" :key="term" size="small">{{ term }}</el-tag>
                    </div>
                    <p>{{ item.content }}</p>
                  </div>
                </div>
              </div>

              <div v-if="analysisResult?.strategy_plan?.length" class="ai-inline-section">
                <div class="ai-inline-section-head">
                  <strong>处置策略</strong>
                  <span>{{ analysisResult.strategy_plan.length }} 条</span>
                </div>
                <div class="recommendation-list">
                  <div
                    v-for="(item, index) in analysisResult.strategy_plan"
                    :key="`${item.step}-${index}`"
                    class="recommendation-item"
                  >
                    <span>{{ index + 1 }}</span>
                    <p>{{ item.step }} / {{ item.owner }} / {{ item.action }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <el-empty
            v-if="!activeSummary && !analysisLoading && !chatLoading && !reportLoading && !analysisResult"
            description="请选择对象"
          />
        </div>

        <div class="ai-console-composer ai-console-composer-fixed">
          <el-input
            v-model="chatQuestion"
            class="ai-composer-input"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入问题"
            @keydown.ctrl.enter.prevent="handleChat"
          />

          <div class="action-row">
            <el-button
              type="primary"
              :loading="analysisLoading"
              :disabled="!activeSource"
              @click="handleAnalyze"
            >
              {{ sourceType === 'alert' ? '研判当前告警' : '复盘当前事件' }}
            </el-button>
            <el-button
              type="primary"
              plain
              :loading="chatLoading"
              :disabled="!chatQuestion.trim()"
              @click="handleChat"
            >
              发送问题
            </el-button>
            <el-button
              v-if="sourceType === 'incident'"
              type="success"
              plain
              :loading="reportLoading"
              :disabled="!activeSource"
              @click="handleGenerateReport"
            >
              生成 AI 报告
            </el-button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import {
  analyzeAlertWithAi,
  analyzeIncidentWithAi,
  chatWithAi,
  fetchIncidentDetail,
  generateIncidentReportWithAi,
} from '../api/dashboard'
import InsightBarChart from '../components/InsightBarChart.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { useAppStore } from '../stores/app'
import { exportTextFile } from '../utils/export'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

const sourceOptions = [
  { label: '告警研判', value: 'alert' },
  { label: '事件复盘', value: 'incident' },
]

const sourceType = ref('alert')
const keyword = ref('')
const useReasonerMode = ref(false)
const activeSource = ref(null)
const analysisResult = ref(null)
const analysisLoading = ref(false)
const chatLoading = ref(false)
const reportLoading = ref(false)
const chatQuestion = ref('')
const lastAutoRunKey = ref('')
const lastActionLabel = ref('智能研判结果')
const syncingFromRoute = ref(false)

const alerts = computed(() => store.alerts || [])
const incidents = computed(() => store.incidents || [])
const currentModel = computed(() => (useReasonerMode.value ? 'deepseek-reasoner' : 'deepseek-chat'))

const filteredItems = computed(() => {
  const raw = sourceType.value === 'alert' ? alerts.value : incidents.value
  if (!keyword.value.trim()) return raw
  const term = keyword.value.trim().toLowerCase()
  return raw.filter((item) => JSON.stringify(item).toLowerCase().includes(term))
})

const activeSummary = computed(() => {
  if (!activeSource.value) return null

  if (sourceType.value === 'alert') {
    return {
      title: activeSource.value.title || activeSource.value.label || '当前告警',
      subtitle: activeSource.value.attack_stage || '阶段待定',
      level: activeSource.value.risk_level || '中',
      metaA: activeSource.value.classifier_name || '--',
      metaB: `${activeSource.value.service_profile?.protocol || '--'}/${activeSource.value.service_profile?.port || '--'}`,
      metaC: `p-value ${activeSource.value.conformal_p_value ?? '--'}`,
      desc: `${activeSource.value.service_profile?.name || '--'} / ${activeSource.value.service_profile?.keywords || '--'}`,
    }
  }

  return {
    title: activeSource.value.incident_no || activeSource.value.title || '当前事件',
    subtitle: `${activeSource.value.attack_type || '--'} / ${activeSource.value.attack_stage || '--'}`,
    level: activeSource.value.severity || '中',
    metaA: activeSource.value.status || '--',
    metaB: `${activeSource.value.source_ip || '--'} -> ${activeSource.value.destination_ip || '--'}`,
    metaC: `聚合 ${activeSource.value.event_count || 0} 条`,
    desc: activeSource.value.asset?.asset_name || activeSource.value.title || '--',
  }
})

const analysisStageItems = computed(() => {
  if (!activeSource.value) return []

  if (sourceType.value === 'alert') {
    return [
      { step: '01', title: '检测证据', value: activeSource.value.classifier_name || '分类模型' },
      { step: '02', title: '未知校准', value: activeSource.value.unknown_flag ? '触发复核' : '已知样本' },
      { step: '03', title: '知识召回', value: analysisResult.value?.knowledge_hits?.length ? `${analysisResult.value.knowledge_hits.length} 条命中` : '待生成' },
      { step: '04', title: '策略生成', value: analysisResult.value?.strategy_plan?.length ? `${analysisResult.value.strategy_plan.length} 条策略` : '待生成' },
    ]
  }

  return [
    { step: '01', title: '事件聚合', value: `${activeSource.value.event_count || 0} 条` },
    { step: '02', title: '研判上下文', value: activeSource.value.status || '--' },
    { step: '03', title: '知识召回', value: analysisResult.value?.knowledge_hits?.length ? `${analysisResult.value.knowledge_hits.length} 条命中` : '待生成' },
    { step: '04', title: '策略生成', value: analysisResult.value?.strategy_plan?.length ? `${analysisResult.value.strategy_plan.length} 条策略` : '待生成' },
  ]
})

const sourceEvidenceCards = computed(() => {
  if (!activeSource.value) return []

  if (sourceType.value === 'alert') {
    const primaryFeature = (activeSource.value.top_features || [])[0]
    return [
      {
        label: '模型判断',
        value: activeSource.value.classifier_name || '--',
        desc: `预测集合 ${(activeSource.value.prediction_set || []).join(' / ') || '--'}`,
      },
      {
        label: '未知异常',
        value: activeSource.value.unknown_flag ? '触发' : '未触发',
        desc: `${activeSource.value.detector_name || 'DeepSVDD'} / ${activeSource.value.uncertainty_level || '--'}`,
      },
      {
        label: '可信校准',
        value: activeSource.value.conformal_p_value ?? '--',
        desc: 'p-value 越低越需要人工复核',
      },
      {
        label: '首要特征',
        value: primaryFeature?.label || '--',
        desc: primaryFeature ? `贡献 ${primaryFeature.contribution}` : '等待特征解释结果',
      },
    ]
  }

  return [
    {
      label: '事件等级',
      value: activeSource.value.severity || '--',
      desc: activeSource.value.status || '--',
    },
    {
      label: '源地址',
      value: activeSource.value.source_ip || '--',
      desc: `目标 ${activeSource.value.destination_ip || '--'}`,
    },
    {
      label: '攻击类型',
      value: activeSource.value.attack_type || '--',
      desc: activeSource.value.attack_stage || '--',
    },
    {
      label: '关联资产',
      value: activeSource.value.asset?.asset_name || '--',
      desc: `聚合 ${activeSource.value.event_count || 0} 条`,
    },
  ]
})

const sourceFeatureItems = computed(() =>
  (activeSource.value?.top_features || []).slice(0, 6).map((item) => ({
    name: item.label,
    value: Number((Number(item.contribution || 0) * 100).toFixed(2)),
  })),
)

const retrievalMetricCards = computed(() => {
  if (!analysisResult.value) return []

  const hits = analysisResult.value.knowledge_hits || []
  const topFusion = hits.length ? Math.max(...hits.map((item) => Number(item.fusion_score || 0))) : 0
  const matchedTerms = hits.reduce((total, item) => total + (item.matched_terms || []).length, 0)
  const strategies = analysisResult.value.strategy_plan || []

  return [
    {
      label: '命中知识',
      value: `${hits.length} 条`,
      desc: '融合关键词与向量双路召回',
    },
    {
      label: '最高融合分',
      value: `${(topFusion * 100).toFixed(1)}%`,
      desc: '用于衡量知识证据相关性',
    },
    {
      label: '匹配术语',
      value: `${matchedTerms} 个`,
      desc: '来自攻击阶段、服务特征与处置术语',
    },
    {
      label: '处置策略',
      value: `${strategies.length} 条`,
      desc: '输出可执行处置步骤',
    },
  ]
})

const ensureRuntimeData = async () => {
  if (!store.systemOverview || !store.alerts.length || !store.incidents.length) {
    await store.bootstrap()
  }
}

const applyFilter = async () => {
  if (!filteredItems.value.length) {
    activeSource.value = null
    return
  }

  const exists = activeSource.value && filteredItems.value.some((item) => item.id === activeSource.value.id)
  if (!exists) {
    await selectSource(filteredItems.value[0], { updateRoute: false })
  }
}

const selectSource = async (item, options = {}) => {
  const { updateRoute = true } = options
  analysisResult.value = null

  if (sourceType.value === 'incident') {
    const response = await fetchIncidentDetail(item.id)
    activeSource.value = response.data
  } else {
    activeSource.value = item
  }

  if (updateRoute && !syncingFromRoute.value) {
    await router.replace({
      path: '/ai-center',
      query: {
        source: sourceType.value,
        id: String(activeSource.value.id),
      },
    })
  }
}

const handleAnalyze = async (options = {}) => {
  const { silent = false } = options
  if (!activeSource.value) return

  analysisLoading.value = true
  lastActionLabel.value = sourceType.value === 'alert' ? '告警智能研判' : '事件智能复盘'

  try {
    const response =
      sourceType.value === 'alert'
        ? await analyzeAlertWithAi({ alert: activeSource.value, model: currentModel.value })
        : await analyzeIncidentWithAi({ incident: activeSource.value, model: currentModel.value })

    analysisResult.value = response.data
    if (!silent) {
      ElMessage.success('智能研判结果已生成')
    }
  } catch (error) {
    ElMessage.error(error?.message || 'AI 研判失败')
  } finally {
    analysisLoading.value = false
  }
}

const handleGenerateReport = async () => {
  if (!activeSource.value || sourceType.value !== 'incident') return

  reportLoading.value = true
  try {
    const response = await generateIncidentReportWithAi({ incident: activeSource.value, model: currentModel.value })
    analysisResult.value = response.data
    lastActionLabel.value = '事件智能报告'
    exportTextFile(`AI-${activeSource.value.incident_no}.md`, response.data.report, 'text/markdown;charset=utf-8;')
    ElMessage.success('AI 事件报告已导出')
  } catch (error) {
    ElMessage.error(error?.message || 'AI 事件报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

const handleChat = async (options = {}) => {
  const { silent = false } = options
  if (!chatQuestion.value.trim()) return

  chatLoading.value = true
  lastActionLabel.value = '安全问答结果'

  try {
    const response = await chatWithAi({
      question: chatQuestion.value.trim(),
      context: {
        sourceType: sourceType.value,
        selectedSource: activeSource.value,
        latestTraining: store.latestTraining,
        dashboard: store.dashboard,
        latestAnalysis: analysisResult.value?.content || '',
      },
      model: currentModel.value,
    })

    analysisResult.value = response.data
    if (!silent) {
      ElMessage.success('智能问答结果已返回')
    }
  } catch (error) {
    ElMessage.error(error?.message || '智能问答失败')
  } finally {
    chatLoading.value = false
  }
}

const toScorePercent = (value) => Math.max(0, Math.min(100, Math.round(Number(value || 0) * 100)))

const severityTagType = (value) => {
  if (!value) return 'info'
  if (String(value).includes('高')) return 'danger'
  if (String(value).includes('低')) return 'success'
  return 'warning'
}

const syncFromRoute = async () => {
  await ensureRuntimeData()

  const routeSource = typeof route.query.source === 'string' ? route.query.source : ''
  const routeId = typeof route.query.id === 'string' ? route.query.id : ''
  const routeQuestion = typeof route.query.q === 'string' ? route.query.q : ''
  const autoStart = route.query.autostart === '1'

  syncingFromRoute.value = true
  try {
    if (routeSource === 'incident') {
      sourceType.value = 'incident'
      const matched = incidents.value.find((item) => String(item.id) === routeId)
      if (matched) {
        await selectSource(matched, { updateRoute: false })
      }
      if (autoStart && activeSource.value) {
        const autoKey = `incident:${routeId}:${currentModel.value}`
        if (lastAutoRunKey.value !== autoKey) {
          lastAutoRunKey.value = autoKey
          await handleAnalyze({ silent: true })
        }
      }
      if (routeQuestion) {
        chatQuestion.value = routeQuestion
      }
      return
    }

    sourceType.value = 'alert'

    if (routeSource === 'alert') {
      const matched = alerts.value.find((item) => String(item.id) === routeId)
      if (matched) {
        await selectSource(matched, { updateRoute: false })
      }
      if (autoStart && activeSource.value) {
        const autoKey = `alert:${routeId}:${currentModel.value}`
        if (lastAutoRunKey.value !== autoKey) {
          lastAutoRunKey.value = autoKey
          await handleAnalyze({ silent: true })
        }
      }
    } else {
      await applyFilter()
    }

    if (routeQuestion) {
      chatQuestion.value = routeQuestion
      if (autoStart) {
        const autoKey = `chat:${routeQuestion}:${currentModel.value}`
        if (lastAutoRunKey.value !== autoKey) {
          lastAutoRunKey.value = autoKey
          await handleChat({ silent: true })
        }
      }
    }
  } finally {
    syncingFromRoute.value = false
  }
}

watch(
  sourceType,
  async (value) => {
    analysisResult.value = null
    if (syncingFromRoute.value) return

    keyword.value = ''
    activeSource.value = null
    await applyFilter()

    await router.replace({
      path: '/ai-center',
      query: activeSource.value
        ? {
            source: value,
            id: String(activeSource.value.id),
          }
        : {
            source: value,
          },
    })
  },
)

watch(
  () => route.fullPath,
  async () => {
    await syncFromRoute()
  },
)

onMounted(async () => {
  try {
    await syncFromRoute()
    if (!activeSource.value) {
      await applyFilter()
    }
  } catch (error) {
    ElMessage.error(error?.message || 'AI 中心初始化失败')
  }
})
</script>
