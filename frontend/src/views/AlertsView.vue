<template>
  <div class="page-stack operation-page-shell">
    <section class="operation-command-stage operation-command-stage-alerts">
      <div class="operation-command-main">
        <span class="soc-command-kicker">Alert Operations</span>
        <h3>告警证据工作台</h3>
        <div class="soc-command-tags">
          <span>实时检测</span>
          <span>{{ unknownAlertCount }} 未知异常</span>
          <span>{{ reviewCount }} 需复核</span>
          <span>{{ resolvedCount }} 已闭环</span>
        </div>
        <div class="operation-metric-grid">
          <div class="operation-metric-card">
            <span>告警总量</span>
            <strong><CountUpValue :value="alerts.length" /></strong>
          </div>
          <div class="operation-metric-card">
            <span>证据完整</span>
            <strong><CountUpValue :value="evidenceCoverageCount" /></strong>
          </div>
          <div class="operation-metric-card">
            <span>未知异常</span>
            <strong><CountUpValue :value="unknownAlertCount" /></strong>
          </div>
          <div class="operation-metric-card">
            <span>待处置</span>
            <strong><CountUpValue :value="pendingCount" /></strong>
          </div>
        </div>
      </div>

      <div class="operation-command-side">
        <div class="operation-command-card pulse-panel">
          <span>当前选中</span>
          <strong>{{ activeAlert ? (activeAlert.title || activeAlert.label || '当前告警') : '未选择' }}</strong>
          <div class="operation-command-badges">
            <span>{{ activeAlert?.attack_stage || '--' }}</span>
            <span>{{ activeAlert?.classifier_name || '--' }}</span>
          </div>
        </div>
        <div class="action-row">
          <el-button type="primary" :disabled="!activeAlert" @click="openAiCenter">进入 AI 研判</el-button>
          <el-button :disabled="!activeAlert" @click="selectFirstHighRisk">切换高风险</el-button>
        </div>
      </div>
    </section>

    <PanelCard title="筛选与批量处置">
      <template #extra>
        <el-button @click="resetFilters">重置</el-button>
        <el-button @click="handleExportAlerts">导出告警</el-button>
        <el-button type="warning" :disabled="!selectedAlertIds.length" @click="handleBatchResolve">
          批量标记已处置
        </el-button>
      </template>

      <div class="filter-row alert-filter-row">
        <el-select v-model="filters.risk_level" placeholder="风险等级" clearable>
          <el-option label="高" value="高" />
          <el-option label="中" value="中" />
          <el-option label="低" value="低" />
        </el-select>
        <el-select v-model="filters.status" placeholder="处置状态" clearable>
          <el-option label="待处置" value="待处置" />
          <el-option label="已处置" value="已处置" />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="搜索" clearable />
        <el-button type="primary" @click="loadAlerts">查询</el-button>
      </div>
    </PanelCard>

    <div class="alert-workbench operation-workbench">
      <PanelCard title="告警列表">
        <el-empty v-if="!paginatedAlerts.length" description="暂无告警" />
        <el-table
          v-else
          :data="paginatedAlerts"
          stripe
          border
          highlight-current-row
          @selection-change="onAlertSelectionChange"
          @row-click="selectAlert"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="title" label="告警标题" min-width="220" />
          <el-table-column prop="attack_stage" label="攻击阶段" min-width="120" />
          <el-table-column prop="classifier_name" label="分类模型" min-width="130" />
          <el-table-column label="未知异常" width="90">
            <template #default="{ row }">
              {{ row.unknown_flag ? '是' : '否' }}
            </template>
          </el-table-column>
          <el-table-column label="服务端口" min-width="140">
            <template #default="{ row }">
              {{ row.service_profile?.protocol || '--' }}/{{ row.service_profile?.port || '--' }}
            </template>
          </el-table-column>
          <el-table-column label="风险" width="90">
            <template #default="{ row }">
              <SeverityTag :level="row.risk_level" />
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="created_at" label="时间" min-width="160" />
        </el-table>
        <el-pagination
          class="table-pagination"
          background
          layout="total, prev, pager, next"
          :total="alerts.length"
          :page-size="alertPageSize"
          :current-page="alertPage"
          @current-change="alertPage = $event"
        />
      </PanelCard>

      <div class="page-stack">
        <PanelCard title="告警证据视图">
          <Transition name="focus-card-swap" mode="out-in">
            <el-empty v-if="!activeAlert" key="empty" description="请选择告警" />
            <div v-else :key="activeAlert.id" class="page-stack">
              <div class="service-card service-card-standalone operation-focus-card">
                <div class="service-card-top">
                  <div>
                    <strong>{{ activeAlert.title || activeAlert.label || '当前告警' }}</strong>
                    <p>{{ activeAlert.attack_stage || '阶段待定' }}</p>
                  </div>
                  <SeverityTag :level="activeAlert.risk_level" />
                </div>
                <div class="service-card-metrics">
                  <span>{{ activeAlert.service_profile?.name || '未知服务' }}</span>
                  <span>{{ activeAlert.service_profile?.protocol || '--' }}/{{ activeAlert.service_profile?.port || '--' }}</span>
                  <span>{{ activeAlert.classifier_name || '--' }}</span>
                  <span>p-value {{ activeAlert.conformal_p_value ?? '--' }}</span>
                </div>
                <div class="service-card-desc">
                  {{ activeAlert.service_profile?.keywords || '--' }}
                </div>
              </div>

              <div class="evidence-card-grid">
                <div v-for="item in alertEvidenceCards" :key="item.label" class="evidence-card">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                  <p>{{ item.desc }}</p>
                </div>
              </div>

              <div class="status-flow-card">
                <div class="status-flow-track">
                  <div
                    v-for="step in alertStatusFlow"
                    :key="step.key"
                    class="status-flow-step"
                    :class="{ 'is-active': step.active, 'is-current': step.current }"
                  >
                    <span class="status-flow-dot"></span>
                    <strong>{{ step.label }}</strong>
                    <p>{{ step.desc }}</p>
                  </div>
                </div>
              </div>

              <TransitionGroup name="timeline-stagger" tag="div" class="animated-timeline">
                <div v-for="item in alertTimeline" :key="item.key" class="timeline-node">
                  <div class="timeline-node-head">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.time }}</span>
                  </div>
                  <p>{{ item.detail }}</p>
                </div>
              </TransitionGroup>

              <div class="action-row">
                <el-button type="primary" @click="openAiCenter">进入 AI 研判</el-button>
                <el-button type="success" plain @click="markSingleResolved">标记已处置</el-button>
              </div>
            </div>
          </Transition>
        </PanelCard>

        <PanelCard title="特征解释与处置建议">
          <Transition name="focus-card-swap" mode="out-in">
            <el-empty v-if="!activeAlert" key="empty" description="暂无数据" />
            <div v-else :key="`insight-${activeAlert.id}`" class="page-stack">
              <InsightBarChart
                v-if="featureChartItems.length"
                :items="featureChartItems"
                category-key="name"
                value-key="value"
                series-name="贡献度"
                color="#c2410c"
              />

              <div class="recommendation-list">
                <div v-for="(item, index) in recommendations" :key="`${index}-${item}`" class="recommendation-item">
                  <span>{{ index + 1 }}</span>
                  <p>{{ item }}</p>
                </div>
              </div>
            </div>
          </Transition>
        </PanelCard>
      </div>
    </div>

    <div class="two-column operation-bottom-grid">
      <PanelCard title="告警趋势">
        <LineTrendChart
          v-if="alertTrend"
          :labels="alertTrend.labels || []"
          :values="alertTrend.counts || []"
          series-name="告警数量"
        />
        <el-empty v-else description="暂无数据" />
      </PanelCard>

      <PanelCard title="高风险服务画像">
        <el-empty v-if="!(servicePortrait.services || []).length" description="暂无数据" />
        <div v-else class="service-card-grid">
          <div
            v-for="service in portraitPreview"
            :key="`${service.name}-${service.port}`"
            class="service-card"
          >
            <div class="service-card-top">
              <div>
                <strong>{{ service.name }}</strong>
                <p>{{ service.protocol }}/{{ service.port }}</p>
              </div>
              <span>{{ service.count }} 次</span>
            </div>
            <div class="service-card-metrics">
              <span>高风险 {{ service.highRiskCount }}</span>
              <span>{{ service.keywords }}</span>
            </div>
          </div>
        </div>
      </PanelCard>
    </div>

    <PanelCard title="近期检测留痕">
      <template #extra>
        <el-button @click="handleExportLogs">导出日志</el-button>
      </template>

      <el-empty v-if="!paginatedLogs.length" description="暂无日志" />
      <el-table v-else :data="paginatedLogs" stripe border>
        <el-table-column prop="label" label="结论" min-width="120" />
        <el-table-column prop="binary_decision" label="第一层判定" min-width="120" />
        <el-table-column prop="attack_stage" label="攻击阶段" min-width="120" />
        <el-table-column prop="anomaly_score" label="异常分数" width="110" />
        <el-table-column label="未知异常" width="100">
          <template #default="{ row }">
            {{ row.unknown_flag ? '是' : '否' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" min-width="160" />
      </el-table>
      <el-pagination
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="logs.length"
        :page-size="logPageSize"
        :current-page="logPage"
        @current-change="logPage = $event"
      />
    </PanelCard>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import {
  batchUpdateAlerts,
  fetchAlertTrends,
  fetchAlertsFiltered,
  fetchServicePortrait,
} from '../api/dashboard'
import CountUpValue from '../components/CountUpValue.vue'
import InsightBarChart from '../components/InsightBarChart.vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import PanelCard from '../components/PanelCard.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { useAppStore } from '../stores/app'
import { exportRowsToCsv } from '../utils/export'

const router = useRouter()
const store = useAppStore()

const alerts = computed(() => store.alerts || [])
const logs = computed(() => store.detectionLogs || [])
const alertTrend = computed(() => store.alertTrend)

const alertPage = ref(1)
const logPage = ref(1)
const alertPageSize = 6
const logPageSize = 6
const selectedAlertIds = ref([])
const activeAlert = ref(null)
const servicePortrait = ref({ services: [] })

const filters = reactive({
  risk_level: '',
  status: '',
  keyword: '',
})

const highRiskCount = computed(() => alerts.value.filter((item) => isHighLevel(item.risk_level)).length)
const unknownAlertCount = computed(() => alerts.value.filter((item) => item.unknown_flag).length)
const pendingCount = computed(() => alerts.value.filter((item) => item.status !== '已处置').length)
const resolvedCount = computed(() => alerts.value.filter((item) => item.status === '已处置').length)
const reviewCount = computed(() => alerts.value.filter((item) => item.requires_review || item.unknown_flag || isHighUncertainty(item.uncertainty_level)).length)
const evidenceCoverageCount = computed(() =>
  alerts.value.filter((item) => (item.top_features || []).length || (item.recommendations || []).length || item.conformal_p_value != null).length,
)
const portraitPreview = computed(() => (servicePortrait.value.services || []).slice(0, 4))
const topFeatures = computed(() => (activeAlert.value?.top_features || []).slice(0, 6))
const recommendations = computed(() => (activeAlert.value?.recommendations || []).slice(0, 4))
const predictionSetText = computed(() => {
  const set = activeAlert.value?.prediction_set || []
  return set.length ? set.join(' / ') : '暂无'
})
const featureChartItems = computed(() =>
  topFeatures.value.map((item) => ({
    name: item.label,
    value: Number((Number(item.contribution || 0) * 100).toFixed(2)),
  })),
)
const alertEvidenceCards = computed(() => {
  if (!activeAlert.value) return []
  const primaryFeature = topFeatures.value[0]

  return [
    {
      label: '模型判断',
      value: activeAlert.value.classifier_name || '--',
      desc: `预测集合 ${predictionSetText.value}`,
    },
    {
      label: '未知异常',
      value: activeAlert.value.unknown_flag ? '触发' : '未触发',
      desc: `${activeAlert.value.detector_name || 'DeepSVDD'} / ${activeAlert.value.uncertainty_level || '--'}`,
    },
    {
      label: '可信校准',
      value: activeAlert.value.conformal_p_value ?? '--',
      desc: 'p-value 越低越需要人工复核',
    },
    {
      label: '首要特征',
      value: primaryFeature?.label || '--',
      desc: primaryFeature ? `贡献 ${primaryFeature.contribution}` : '等待特征解释结果',
    },
  ]
})

const alertStatusFlow = computed(() => {
  const alert = activeAlert.value
  if (!alert) return []

  const hasPrediction = Boolean(alert.classifier_name || (alert.prediction_set || []).length)
  const hasInsight = Boolean((alert.top_features || []).length || (alert.recommendations || []).length)
  const isResolved = alert.status === '已处置'

  return [
    {
      key: 'capture',
      label: '流量接入',
      desc: '实时流量进入检测链路',
      active: true,
      current: !hasPrediction,
    },
    {
      key: 'classify',
      label: '模型识别',
      desc: `由 ${alert.classifier_name || '分类器'} 输出攻击判断`,
      active: hasPrediction,
      current: hasPrediction && !hasInsight,
    },
    {
      key: 'triage',
      label: '证据复核',
      desc: '结合特征解释与安全知识完成研判',
      active: hasInsight,
      current: hasInsight && !isResolved,
    },
    {
      key: 'resolve',
      label: '闭环处置',
      desc: isResolved ? '已完成处置回写' : '等待人工确认与回写',
      active: isResolved,
      current: !isResolved,
    },
  ]
})

const alertTimeline = computed(() => {
  const alert = activeAlert.value
  if (!alert) return []

  return [
    {
      key: `capture-${alert.id}`,
      title: '流量进入检测链路',
      time: alert.created_at || '--',
      detail: `${alert.service_profile?.protocol || '--'}/${alert.service_profile?.port || '--'} 已纳入实时检测窗口`,
    },
    {
      key: `classify-${alert.id}`,
      title: '已知攻击分类完成',
      time: alert.classifier_name || '--',
      detail: `预测标签集合：${predictionSetText.value}`,
    },
    {
      key: `unknown-${alert.id}`,
      title: '未知异常补充判断',
      time: `p-value ${alert.conformal_p_value ?? '--'}`,
      detail: alert.unknown_flag ? '检测到未知异常风险，已进入重点复核队列' : '当前样本未触发未知异常升级',
    },
    {
      key: `resolve-${alert.id}`,
      title: '处置状态更新',
      time: alert.status || '待处置',
      detail: alert.status === '已处置' ? '告警已完成处置并回写闭环记录' : '告警仍待人工进一步处置',
    },
  ]
})

const paginatedAlerts = computed(() => {
  const start = (alertPage.value - 1) * alertPageSize
  return alerts.value.slice(start, start + alertPageSize)
})

const paginatedLogs = computed(() => {
  const start = (logPage.value - 1) * logPageSize
  return logs.value.slice(start, start + logPageSize)
})

const isHighLevel = (value) => String(value || '').includes('高')
const isHighUncertainty = (value) => ['high', '高', 'HIGH'].includes(String(value || ''))

const ensureActiveAlert = () => {
  if (!alerts.value.length) {
    activeAlert.value = null
    return
  }

  if (!activeAlert.value) {
    activeAlert.value = alerts.value[0]
    return
  }

  const current = alerts.value.find((item) => item.id === activeAlert.value.id)
  activeAlert.value = current || alerts.value[0]
}

const loadAlerts = async () => {
  try {
    const response = await fetchAlertsFiltered(filters)
    store.alerts = response.data.items || []
    alertPage.value = 1
    selectedAlertIds.value = []
    ensureActiveAlert()
  } catch (error) {
    ElMessage.error(error?.message || '告警数据加载失败')
  }
}

const loadAlertTrend = async () => {
  try {
    const response = await fetchAlertTrends()
    store.alertTrend = response.data
  } catch (error) {
    ElMessage.error(error?.message || '告警趋势加载失败')
  }
}

const loadServicePortrait = async () => {
  try {
    const response = await fetchServicePortrait({ limit: 300 })
    servicePortrait.value = response.data || { services: [] }
  } catch (error) {
    ElMessage.error(error?.message || '服务画像加载失败')
  }
}

const resetFilters = async () => {
  filters.risk_level = ''
  filters.status = ''
  filters.keyword = ''
  await loadAlerts()
}

const onAlertSelectionChange = (rows) => {
  selectedAlertIds.value = rows.map((item) => item.id)
}

const selectAlert = (row) => {
  activeAlert.value = row
}

const selectFirstHighRisk = () => {
  const target = alerts.value.find((item) => isHighLevel(item.risk_level)) || alerts.value[0]
  if (target) {
    activeAlert.value = target
  }
}

const openAiCenter = () => {
  if (!activeAlert.value) return
  router.push({
    path: '/ai-center',
    query: {
      source: 'alert',
      id: String(activeAlert.value.id),
      autostart: '1',
    },
  })
}

const handleBatchResolve = async () => {
  if (!selectedAlertIds.value.length) return
  try {
    await batchUpdateAlerts({ ids: selectedAlertIds.value, status: '已处置' })
    ElMessage.success('批量处置完成')
    await store.refreshRuntimeData()
    await loadAlertTrend()
    await loadServicePortrait()
    selectedAlertIds.value = []
    ensureActiveAlert()
  } catch (error) {
    ElMessage.error(error?.message || '批量处置失败')
  }
}

const markSingleResolved = async () => {
  if (!activeAlert.value) return
  try {
    await batchUpdateAlerts({ ids: [activeAlert.value.id], status: '已处置' })
    ElMessage.success('当前告警已标记为已处置')
    await store.refreshRuntimeData()
    await loadAlertTrend()
    await loadServicePortrait()
    ensureActiveAlert()
  } catch (error) {
    ElMessage.error(error?.message || '告警状态更新失败')
  }
}

const handleExportAlerts = () => {
  exportRowsToCsv('alerts.csv', alerts.value)
}

const handleExportLogs = () => {
  exportRowsToCsv('detection_logs.csv', logs.value)
}

watch(
  alerts,
  () => {
    ensureActiveAlert()
  },
  { deep: true },
)

onMounted(async () => {
  try {
    if (!store.alerts.length || !store.detectionLogs.length) {
      await store.bootstrap()
    }
    ensureActiveAlert()
    await loadAlertTrend()
    await loadServicePortrait()
  } catch (error) {
    ElMessage.error(error?.message || '告警中心初始化失败')
  }
})
</script>
