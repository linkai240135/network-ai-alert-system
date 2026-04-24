<template>
  <div v-if="dashboard" class="page-stack dashboard-command-page">
    <section class="soc-command-stage">
      <div class="soc-command-main">
        <span class="soc-command-kicker">Security Operations Command</span>
        <h3>网络异常检测与智能告警闭环系统</h3>
        <div class="soc-command-tags">
          <span>真实数据</span>
          <span>未知异常检测</span>
          <span>RAG 证据研判</span>
          <span>反馈反哺训练</span>
        </div>
        <div class="soc-command-metric-grid">
          <div class="soc-command-metric pulse-panel">
            <span>接入流量样本</span>
            <strong><CountUpValue :value="dashboard.stats.datasetRecords" /></strong>
          </div>
          <div class="soc-command-metric pulse-panel">
            <span>触发告警</span>
            <strong><CountUpValue :value="dashboard.stats.alertCount" /></strong>
          </div>
          <div class="soc-command-metric pulse-panel">
            <span>未知异常</span>
            <strong><CountUpValue :value="dashboard.stats.unknownCount" /></strong>
          </div>
          <div class="soc-command-metric pulse-panel">
            <span>进入事件</span>
            <strong><CountUpValue :value="dashboard.stats.incidentCount" /></strong>
          </div>
        </div>
      </div>

      <div class="soc-command-side">
        <div class="soc-command-side-grid">
          <div class="soc-side-card">
            <span>AI 证据覆盖率</span>
            <strong><CountUpValue :value="aiCoveragePercent" :decimals="1" />%</strong>
          </div>
          <div class="soc-side-card">
            <span>事件闭环率</span>
            <strong><CountUpValue :value="closurePercent" :decimals="1" />%</strong>
          </div>
          <div class="soc-side-card">
            <span>未知异常占比</span>
            <strong><CountUpValue :value="unknownAlertPercent" :decimals="1" />%</strong>
          </div>
          <div class="soc-side-card">
            <span>反馈样本</span>
            <strong><CountUpValue :value="feedbackSamples" /></strong>
          </div>
        </div>
      </div>
    </section>

    <div class="chain-overview-grid chain-overview-grid-subtle">
      <div v-for="item in chainItems" :key="item.step" class="chain-node-card">
        <span>{{ item.step }}</span>
        <strong>{{ item.title }}</strong>
      </div>
    </div>

    <div class="dashboard-command-grid">
      <div class="dashboard-command-main-column page-stack">
        <PanelCard title="闭环成效看板">
          <InsightBarChart
            :items="businessMetricItems"
            category-key="name"
            value-key="value"
            series-name="占比 / 召回"
            color="#2563eb"
          />
        </PanelCard>

        <PanelCard title="实时告警趋势">
          <LineTrendChart :labels="dashboard.alertTrend?.labels || []" :values="dashboard.alertTrend?.counts || []" series-name="告警数量" />
        </PanelCard>

        <PanelCard title="证据化告警样例">
          <el-empty v-if="!explainAlert" description="暂无数据" />
          <template v-else>
            <div class="security-brief-card">
              <div class="security-brief-head">
                <div>
                  <span class="security-brief-label">当前样例</span>
                  <strong>{{ explainAlert.label }}</strong>
                </div>
                <SeverityTag :level="explainAlert.risk_level" />
              </div>
              <div class="security-brief-tags">
                <span>{{ explainAlert.attack_stage }}</span>
                <span>{{ explainAlert.classifier_name || '--' }}</span>
                <span>{{ explainAlert.detector_name || 'DeepSVDD' }}</span>
                <span>p-value {{ explainAlert.conformal_p_value ?? '--' }}</span>
              </div>
            </div>

            <div class="evidence-card-grid">
              <div v-for="item in sampleEvidenceCards" :key="item.label" class="evidence-card">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </div>

            <InsightBarChart
              v-if="explainFeatureItems.length"
              :items="explainFeatureItems"
              category-key="name"
              value-key="value"
              series-name="特征贡献"
              color="#c2410c"
            />
          </template>
        </PanelCard>
      </div>

      <div class="dashboard-command-side-column page-stack">
        <PanelCard title="训练可信快照">
          <div class="summary-grid">
            <div class="summary-item"><span>生产模型</span><strong>{{ dashboard.training?.best_model || '--' }}</strong></div>
            <div class="summary-item"><span>加权 F1</span><strong>{{ formatPercentValue(weightedF1) }}</strong></div>
            <div class="summary-item"><span>宏平均 F1</span><strong>{{ formatPercentValue(macroF1) }}</strong></div>
            <div class="summary-item"><span>宏平均 Recall</span><strong>{{ formatPercentValue(macroRecall) }}</strong></div>
            <div class="summary-item"><span>最弱类别</span><strong>{{ weakestClass?.label || '--' }}</strong></div>
            <div class="summary-item"><span>最弱类别 F1</span><strong>{{ formatPercentValue(weakestClass?.f1) }}</strong></div>
          </div>
          <div class="trust-note-card">
            <strong>结果解读</strong>
            <p>首页不再主打单个模型高分，而强调类别差异、未知异常覆盖与处置闭环能力。</p>
          </div>
        </PanelCard>

        <section class="security-stack-card">
          <div class="security-stack-head">
            <span>AI 决策链路</span>
            <strong>Decision Stack</strong>
          </div>
          <div class="security-stack-grid">
            <div v-for="item in innovationItems" :key="item.title" class="security-stack-item">
              <span>{{ item.tag }}</span>
              <strong>{{ item.title }}</strong>
            </div>
          </div>
        </section>

        <PanelCard title="事件闭环概览">
          <div class="summary-grid">
            <div class="summary-item"><span>待研判</span><strong>{{ dashboard.incidentBoard?.stats?.pending || 0 }}</strong></div>
            <div class="summary-item"><span>研判中</span><strong>{{ dashboard.incidentBoard?.stats?.processing || 0 }}</strong></div>
            <div class="summary-item"><span>已处置</span><strong>{{ dashboard.incidentBoard?.stats?.resolved || 0 }}</strong></div>
          </div>
          <div class="service-card-grid">
            <div v-for="item in incidentPreview" :key="item.id" class="service-card">
              <div class="service-card-top">
                <div>
                  <strong>{{ item.attack_type }}</strong>
                  <p>{{ item.asset?.asset_name || '--' }}</p>
                </div>
                <SeverityTag :level="item.severity" />
              </div>
              <div class="service-card-metrics">
                <span>{{ item.status }}</span>
                <span>聚合 {{ item.event_count }} 条</span>
              </div>
              <div class="service-card-desc">{{ item.source_ip }} → {{ item.destination_ip }}</div>
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  </div>
  <el-empty v-else description="加载中" />
</template>

<script setup>
import { computed, onMounted } from 'vue'

import InsightBarChart from '../components/InsightBarChart.vue'
import LineTrendChart from '../components/LineTrendChart.vue'
import CountUpValue from '../components/CountUpValue.vue'
import PanelCard from '../components/PanelCard.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const dashboard = computed(() => store.dashboard)
const alerts = computed(() => store.alerts || [])

const chainItems = [
  { step: '01', title: '真实数据接入' },
  { step: '02', title: '已知攻击识别' },
  { step: '03', title: '未知异常发现' },
  { step: '04', title: '可解释证据输出' },
  { step: '05', title: 'RAG 智能研判' },
  { step: '06', title: '事件闭环处置' },
]

const innovationItems = [
  { tag: 'Known Attack', title: 'FT-Transformer / XGBoost 识别已知攻击' },
  { tag: 'Unknown Threat', title: 'Deep SVDD 发现未知异常' },
  { tag: 'Trusted AI', title: 'Conformal 输出可信参考' },
  { tag: 'Security Copilot', title: 'DeepSeek + 知识库生成处置策略' },
]

const incidentPreview = computed(() => (dashboard.value?.incidentBoard?.items || []).slice(0, 4))
const explainAlert = computed(() => {
  const source = alerts.value.length ? alerts.value : dashboard.value?.recentAlerts || []
  return source.find((item) => item.top_features?.length) || source[0] || null
})
const explainFeatureItems = computed(() =>
  (explainAlert.value?.top_features || []).map((item) => ({ name: item.label, value: Number(item.contribution || 0) })),
)

const classificationReport = computed(() => dashboard.value?.training?.classification_report || {})
const weightedF1 = computed(() => Number(classificationReport.value?.['weighted avg']?.['f1-score'] || 0))
const macroF1 = computed(() => Number(classificationReport.value?.['macro avg']?.['f1-score'] || 0))
const macroRecall = computed(() => Number(classificationReport.value?.['macro avg']?.recall || 0))
const weakestClass = computed(() => {
  const rows = Object.entries(classificationReport.value || {})
    .filter(([name]) => !['accuracy', 'macro avg', 'weighted avg'].includes(name))
    .map(([name, item]) => ({
      label: name,
      f1: Number(item?.['f1-score'] || 0),
      recall: Number(item?.recall || 0),
      support: Number(item?.support || 0),
    }))
  if (!rows.length) return null
  return rows.sort((a, b) => a.f1 - b.f1)[0]
})

const aiCoveragePercent = computed(() => {
  if (!alerts.value.length) return 0
  const covered = alerts.value.filter((item) => (item.top_features || []).length || (item.recommendations || []).length).length
  return Number(((covered / alerts.value.length) * 100).toFixed(1))
})
const closurePercent = computed(() => {
  const stats = dashboard.value?.incidentBoard?.stats || {}
  const total = Number(stats.total || 0)
  if (!total) return 0
  return Number(((Number(stats.resolved || 0) / total) * 100).toFixed(1))
})
const unknownAlertPercent = computed(() => {
  const total = Number(dashboard.value?.stats?.alertCount || 0)
  if (!total) return 0
  return Number(((Number(dashboard.value?.stats?.unknownCount || 0) / total) * 100).toFixed(1))
})
const feedbackSamples = computed(() => Number(dashboard.value?.incidentBoard?.stats?.feedbackSamples || dashboard.value?.incidentBoard?.stats?.feedbackCount || 0))
const businessMetricItems = computed(() => [
  { name: 'AI 证据覆盖率', value: aiCoveragePercent.value },
  { name: '事件闭环率', value: closurePercent.value },
  { name: '未知异常占比', value: unknownAlertPercent.value },
  { name: '未知攻击召回', value: Number(((dashboard.value?.training?.detector_metrics?.attack_recall || 0) * 100).toFixed(1)) },
])
const sampleEvidenceCards = computed(() => {
  const alert = explainAlert.value
  if (!alert) return []
  const primaryFeature = (alert.top_features || [])[0]
  return [
    {
      label: '模型判断',
      value: alert.classifier_name || '--',
      desc: `预测集合 ${((alert.prediction_set || []).join(' / ')) || '--'}`,
    },
    {
      label: '异常参考',
      value: alert.unknown_flag ? '未知异常' : '已知分类',
      desc: `${alert.detector_name || 'DeepSVDD'} / ${alert.uncertainty_level || '--'}`,
    },
    {
      label: '可信校准',
      value: alert.conformal_p_value ?? '--',
      desc: 'p-value 越低越需要人工复核',
    },
    {
      label: '首要信号',
      value: primaryFeature?.label || '--',
      desc: primaryFeature ? `贡献 ${primaryFeature.contribution}` : '等待特征解释结果',
    },
  ]
})

const formatPercentValue = (value) => {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return `${(Number(value) * 100).toFixed(2)}%`
}

onMounted(async () => {
  if (!store.dashboard) {
    await store.bootstrap()
  }
})
</script>
