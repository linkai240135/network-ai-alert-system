<template>
  <div class="command-center-screen">
    <header class="command-screen-header">
      <div class="command-screen-header-mark"></div>
      <div class="command-screen-title-group">
        <span>Realtime Detection Command Center</span>
        <strong>网络异常流量智能检测与告警大屏</strong>
      </div>
      <div class="command-screen-meta">
        <span>{{ replayRunning ? '引擎运行中' : '引擎已暂停' }}</span>
        <span>{{ sampleSize }} 条窗口</span>
        <span>{{ replaySpeed / 1000 }} 秒/条</span>
      </div>
    </header>

    <section class="command-screen-grid">
      <aside class="command-side-column">
        <section class="command-panel command-panel-metric">
          <div class="command-panel-head">
            <span>流量态势</span>
            <strong>实时指标</strong>
          </div>
          <div class="command-metric-stack">
            <div class="command-metric-item command-metric-item-strong">
              <span>已回放流量</span>
              <strong><CountUpValue :value="playedCount" /></strong>
              <p>当前窗口 {{ replaySummary.total || 0 }} 条</p>
            </div>
            <div class="command-metric-item">
              <span>实时吞吐</span>
              <strong><CountUpValue :value="throughputValue" :decimals="1" /></strong>
              <p>flows / s</p>
            </div>
            <div class="command-metric-item">
              <span>告警触发率</span>
              <strong><CountUpValue :value="alertRate" :decimals="1" />%</strong>
              <p>{{ replaySummary.alerts || 0 }} 条进入告警链路</p>
            </div>
            <div class="command-metric-item">
              <span>未知异常率</span>
              <strong><CountUpValue :value="unknownRate" :decimals="1" />%</strong>
              <p>{{ replaySummary.unknownCount || 0 }} 条触发未知异常</p>
            </div>
          </div>
        </section>

        <section class="command-panel">
          <div class="command-panel-head">
            <span>攻击源热度</span>
            <strong>源地址命中</strong>
          </div>
          <InsightBarChart
            v-if="sourceHeatItems.length"
            :items="sourceHeatItems"
            category-key="name"
            value-key="value"
            series-name="flows"
            color="#26d0ff"
          />
          <el-empty v-else description="暂无数据" />
        </section>

        <section class="command-panel">
          <div class="command-panel-head">
            <span>协议画像</span>
            <strong>当前窗口分布</strong>
          </div>
          <div class="command-protocol-list">
            <div v-for="item in protocolItems" :key="item.name" class="command-protocol-item">
              <div class="command-protocol-row">
                <span>{{ item.name }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="command-protocol-bar">
                <div class="command-protocol-bar-fill" :style="{ width: `${item.percent}%` }"></div>
              </div>
            </div>
          </div>
        </section>
      </aside>

      <section class="command-main-stage">
        <div class="command-main-toolbar">
          <div class="command-main-kicker">
            <span>主检测舞台</span>
            <strong>源节点 -> 攻击链路 -> 目标资产</strong>
          </div>
          <div class="command-main-actions">
            <el-button type="primary" :loading="replayLoading" @click="startReplay">
              {{ replayRunning ? '继续回放' : '开始回放' }}
            </el-button>
            <el-button @click="pauseReplay">暂停</el-button>
            <el-button @click="loadReplayBatch">刷新窗口</el-button>
          </div>
        </div>

        <div class="command-feed-strip">
          <div v-for="item in liveFeedItems" :key="item.key" class="command-feed-chip" :class="item.levelClass">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>

        <div class="command-flow-stage">
          <div class="command-flow-grid"></div>

          <div class="command-flow-column command-flow-column-left">
            <div v-for="item in flowSourceNodes" :key="item.id" class="command-flow-node command-flow-node-source">
              <span>Source</span>
              <strong>{{ item.name }}</strong>
              <p>{{ item.meta }}</p>
            </div>
          </div>

          <div class="command-flow-center">
            <div
              v-for="item in flowLinkItems"
              :key="item.key"
              class="command-link-line"
              :class="item.levelClass"
              :style="{ top: item.top }"
            >
              <div class="command-link-beam"></div>
              <div class="command-link-label">
                <span>{{ item.source }}</span>
                <strong>{{ item.label }}</strong>
                <p>{{ item.target }} / {{ item.service }}</p>
              </div>
            </div>

            <div v-if="activeFlowRoute" class="command-center-core pulse-panel">
              <span>当前焦点链路</span>
              <strong>{{ activeFlowRoute.label }}</strong>
              <p>{{ activeFlowRoute.attackStage }}</p>
              <div class="command-center-core-route">
                <span>{{ activeFlowRoute.source }}</span>
                <strong>{{ activeFlowRoute.service }}</strong>
                <span>{{ activeFlowRoute.target }}</span>
              </div>
            </div>
          </div>

          <div class="command-flow-column command-flow-column-right">
            <div v-for="item in flowTargetNodes" :key="item.id" class="command-flow-node command-flow-node-target">
              <span>Target</span>
              <strong>{{ item.name }}</strong>
              <p>{{ item.meta }}</p>
            </div>
          </div>
        </div>

        <div class="command-summary-row">
          <div class="command-summary-card">
            <span>回放进度</span>
            <strong>{{ replayProgressText }}</strong>
            <el-progress :percentage="replayProgressPercent" :stroke-width="10" />
          </div>
          <div class="command-summary-card">
            <span>高风险流量</span>
            <strong><CountUpValue :value="highRiskCount" /></strong>
            <p>当前窗口需优先处置的检测结果</p>
          </div>
          <div class="command-summary-card">
            <span>稳定业务流</span>
            <strong><CountUpValue :value="benignCount" /></strong>
            <p>用于体现正常流量与异常流量共存场景</p>
          </div>
        </div>

        <section class="command-panel command-main-list-panel">
          <div class="command-panel-head">
            <span>实时流量窗口</span>
            <strong>流量回放列表</strong>
          </div>
          <div v-if="streamItems.length" class="command-stream-list">
            <button
              v-for="item in streamItems"
              :key="item.id"
              type="button"
              class="command-stream-card"
              :class="{ active: activeResult?.id === item.id }"
              @click="selectStreamItem(item)"
            >
              <div class="command-stream-top">
                <div>
                  <span>{{ item.timestamp }}</span>
                  <strong>{{ item.label }}</strong>
                </div>
                <SeverityTag :level="item.risk_level" />
              </div>
              <div class="command-stream-route">
                <span>{{ item.source_ip }}</span>
                <strong>{{ item.attack_stage }}</strong>
                <p>{{ item.destination_ip }}</p>
              </div>
              <div class="command-stream-tags">
                <span>{{ item.service_profile?.name || '--' }}</span>
                <span>{{ item.service_profile?.protocol || '--' }}/{{ item.service_profile?.port || '--' }}</span>
                <span>{{ item.asset_context?.asset_name || '--' }}</span>
              </div>
            </button>
          </div>
          <el-empty v-else description="暂无回放流量" />
        </section>
      </section>

      <aside class="command-side-column">
        <section class="command-panel command-panel-focus">
          <div class="command-panel-head">
            <span>当前威胁焦点</span>
            <strong>{{ activeResult?.label || '等待流量进入' }}</strong>
          </div>
          <div class="command-focus-meta">
            <span>{{ activeResult?.attack_stage || '--' }}</span>
            <span>{{ activeResult?.classifier_name || '--' }}</span>
            <span>{{ activeResult?.detector_name || '--' }}</span>
          </div>
          <div class="command-focus-grid">
            <div class="command-focus-item">
              <span>分类置信度</span>
              <strong>{{ formatPercent(activeResult?.confidence) }}</strong>
            </div>
            <div class="command-focus-item">
              <span>异常得分</span>
              <strong>{{ formatPercent(activeResult?.anomaly_score) }}</strong>
            </div>
            <div class="command-focus-item">
              <span>可信 p-value</span>
              <strong>{{ activeResult?.conformal_p_value ?? '--' }}</strong>
            </div>
            <div class="command-focus-item">
              <span>未知异常</span>
              <strong>{{ activeResult?.unknown_flag ? '是' : '否' }}</strong>
            </div>
          </div>
          <div class="command-focus-route" v-if="activeFlowRoute">
            <span>{{ activeFlowRoute.source }}</span>
            <strong>{{ activeFlowRoute.service }}</strong>
            <p>{{ activeFlowRoute.target }}</p>
          </div>
        </section>

        <section class="command-panel">
          <div class="command-panel-head">
            <span>证据链</span>
            <strong>检测判断依据</strong>
          </div>
          <div class="evidence-card-grid evidence-card-grid-tight" v-if="resultEvidenceCards.length">
            <div v-for="item in resultEvidenceCards" :key="item.label" class="evidence-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>
          <el-empty v-else description="暂无数据" />
        </section>

        <section class="command-panel">
          <div class="command-panel-head">
            <span>解释结果</span>
            <strong>特征贡献</strong>
          </div>
          <InsightBarChart
            v-if="featureContributionItems.length"
            :items="featureContributionItems"
            category-key="name"
            value-key="value"
            series-name="贡献度"
            color="#17c8ff"
          />
          <el-empty v-else description="暂无数据" />
        </section>

        <section class="command-panel">
          <div class="command-panel-head">
            <span>闭环动作</span>
            <strong>处置建议</strong>
          </div>
          <div v-if="activeResult?.recommendations?.length" class="recommendation-list">
            <div v-for="(item, index) in activeResult.recommendations" :key="`${index}-${item}`" class="recommendation-item">
              <span>{{ index + 1 }}</span>
              <p>{{ item }}</p>
            </div>
          </div>
          <el-empty v-else description="暂无数据" />
        </section>
      </aside>
    </section>

    <section class="command-bottom-panels">
      <PanelCard title="流量明细表">
        <el-empty v-if="!streamItems.length" description="暂无回放流量" />
        <el-table v-else :data="streamItems" stripe border highlight-current-row row-key="id" @row-click="selectStreamItem">
          <el-table-column prop="timestamp" label="时间" min-width="160" />
          <el-table-column prop="source_ip" label="源IP" min-width="140" />
          <el-table-column prop="destination_ip" label="目标IP" min-width="140" />
          <el-table-column prop="label" label="检测结论" min-width="120" />
          <el-table-column prop="attack_stage" label="攻击阶段" min-width="130" />
          <el-table-column label="服务" min-width="140">
            <template #default="{ row }">
              {{ row.service_profile?.protocol || '--' }}/{{ row.service_profile?.port || '--' }}
            </template>
          </el-table-column>
          <el-table-column label="风险" width="90">
            <template #default="{ row }">
              <SeverityTag :level="row.risk_level" />
            </template>
          </el-table-column>
          <el-table-column label="未知异常" width="90">
            <template #default="{ row }">
              {{ row.unknown_flag ? '是' : '否' }}
            </template>
          </el-table-column>
        </el-table>
      </PanelCard>

      <PanelCard title="高级调试">
        <template #extra>
          <el-button @click="openBatchDetection">去批量检测</el-button>
        </template>
        <el-collapse v-model="debugPanels">
          <el-collapse-item title="手工输入特征调试" name="manual">
            <el-form label-position="top" :model="form" class="detect-form">
              <el-form-item v-for="field in featureColumns" :key="field" :label="featureLabelMap[field] || field">
                <el-input-number v-model="form[field]" :controls="false" class="full-width" />
              </el-form-item>
            </el-form>
            <div class="action-row">
              <el-button type="primary" :loading="manualLoading" @click="handleManualDetect">开始调试</el-button>
              <el-button @click="fillAttackSample">攻击样本</el-button>
              <el-button @click="fillBenignSample">正常样本</el-button>
            </div>
          </el-collapse-item>
        </el-collapse>
      </PanelCard>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { runDetection, simulateRealtimeStream } from '../api/dashboard'
import CountUpValue from '../components/CountUpValue.vue'
import InsightBarChart from '../components/InsightBarChart.vue'
import PanelCard from '../components/PanelCard.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { useAppStore } from '../stores/app'

const router = useRouter()
const store = useAppStore()

const featureLabelMap = {
  flow_duration: '流持续时间',
  packet_rate: '包速率',
  byte_rate: '字节速率',
  syn_rate: 'SYN 比率',
  dst_port_entropy: '目标端口熵',
  failed_login_rate: '失败登录率',
  request_interval_std: '请求间隔波动',
  payload_mean: '平均载荷长度',
}

const replayLoading = ref(false)
const replayRunning = ref(false)
const manualLoading = ref(false)
const sampleSize = ref(12)
const replaySpeed = ref(1400)
const replaySummary = ref({ total: 0, alerts: 0, unknownCount: 0 })
const replayQueue = ref([])
const streamItems = ref([])
const activeResult = ref(null)
const playedCount = ref(0)
const debugPanels = ref([])
const featureColumns = computed(() => store.systemOverview?.featureColumns || [])
const form = reactive({})

let playbackTimer = null

const throughputValue = computed(() => Number((1000 / replaySpeed.value).toFixed(1)))
const highRiskCount = computed(() => streamItems.value.filter((item) => String(item.risk_level || '').includes('高')).length)
const benignCount = computed(() => streamItems.value.filter((item) => String(item.label || '').toUpperCase() === 'BENIGN').length)
const alertRate = computed(() => {
  const total = Number(replaySummary.value.total || 0)
  if (!total) return 0
  return Number((((replaySummary.value.alerts || 0) / total) * 100).toFixed(1))
})
const unknownRate = computed(() => {
  const total = Number(replaySummary.value.total || 0)
  if (!total) return 0
  return Number((((replaySummary.value.unknownCount || 0) / total) * 100).toFixed(1))
})

const predictionSetText = computed(() => {
  const set = activeResult.value?.prediction_set || []
  return set.length ? set.join(' / ') : '暂无'
})

const featureContributionItems = computed(() =>
  (activeResult.value?.top_features || []).map((item) => ({
    name: item.label,
    value: Number((Number(item.contribution || 0) * 100).toFixed(2)),
  })),
)

const resultEvidenceCards = computed(() => {
  if (!activeResult.value) return []
  const primaryFeature = (activeResult.value.top_features || [])[0]
  return [
    {
      label: '模型判断',
      value: activeResult.value.classifier_name || '--',
      desc: `结论 ${activeResult.value.label || '--'}`,
    },
    {
      label: '未知异常',
      value: activeResult.value.unknown_flag ? '触发' : '未触发',
      desc: `${activeResult.value.detector_name || 'DeepSVDD'} / ${activeResult.value.uncertainty_level || '--'}`,
    },
    {
      label: '可信校准',
      value: activeResult.value.conformal_p_value ?? '--',
      desc: 'p-value 越低越需要人工复核',
    },
    {
      label: '首要特征',
      value: primaryFeature?.label || '--',
      desc: primaryFeature ? `贡献 ${primaryFeature.contribution}` : '等待解释结果',
    },
  ]
})

const runtimeChain = computed(() => [
  { step: '01', title: '已知攻击分类', value: activeResult.value?.classifier_name || '等待模型输出' },
  { step: '02', title: '未知异常检测', value: activeResult.value?.unknown_flag ? '触发未知异常' : '未触发未知异常' },
  { step: '03', title: '可信校准评估', value: activeResult.value?.conformal_p_value ?? '等待 p-value' },
  { step: '04', title: '告警事件闭环', value: activeResult.value?.binary_decision === 'anomaly' ? '已进入闭环' : '保持观察' },
])

const replayProgressPercent = computed(() => {
  const total = Number(replaySummary.value.total || 0)
  if (!total) return 0
  return Math.min(100, Math.round((playedCount.value / total) * 100))
})

const replayProgressText = computed(() => `${playedCount.value} / ${replaySummary.value.total || 0}`)

const liveFeedItems = computed(() =>
  streamItems.value.slice(0, 5).map((item) => ({
    key: `${item.id}-${item.timestamp}`,
    label: item.attack_stage || '阶段待定',
    value: item.label,
    levelClass: String(item.risk_level || '').includes('高') ? 'is-danger' : item.unknown_flag ? 'is-warning' : 'is-safe',
  })),
)

const flowSourceNodes = computed(() => {
  const sourceMap = new Map()
  streamItems.value.forEach((item) => {
    const key = item.source_ip || '--'
    if (!sourceMap.has(key)) {
      sourceMap.set(key, { id: key, name: key, count: 0, highRisk: 0 })
    }
    const current = sourceMap.get(key)
    current.count += 1
    if (String(item.risk_level || '').includes('高')) current.highRisk += 1
  })
  return [...sourceMap.values()]
    .sort((a, b) => b.highRisk - a.highRisk || b.count - a.count)
    .slice(0, 4)
    .map((item) => ({
      ...item,
      meta: `${item.count} flows / 高风险 ${item.highRisk}`,
    }))
})

const flowTargetNodes = computed(() => {
  const targetMap = new Map()
  streamItems.value.forEach((item) => {
    const key = item.asset_context?.asset_code || item.destination_ip || '--'
    if (!targetMap.has(key)) {
      targetMap.set(key, {
        id: key,
        name: item.asset_context?.asset_name || item.destination_ip || '--',
        count: 0,
        meta: `${item.destination_ip || '--'} / ${item.service_profile?.name || '--'}`,
      })
    }
    targetMap.get(key).count += 1
  })
  return [...targetMap.values()].sort((a, b) => b.count - a.count).slice(0, 4)
})

const flowLinkItems = computed(() =>
  streamItems.value.slice(0, 5).map((item, index) => ({
    key: `${item.id}-${item.timestamp}`,
    source: item.source_ip || '--',
    target: item.destination_ip || '--',
    label: item.label,
    attackStage: item.attack_stage || '--',
    service: `${item.service_profile?.protocol || '--'}/${item.service_profile?.port || '--'}`,
    top: `${12 + index * 14}%`,
    levelClass: String(item.risk_level || '').includes('高') ? 'is-danger' : item.unknown_flag ? 'is-warning' : 'is-safe',
  })),
)

const activeFlowRoute = computed(() => {
  if (!activeResult.value) return null
  return {
    source: activeResult.value.source_ip || '--',
    target: activeResult.value.destination_ip || '--',
    label: activeResult.value.label || '--',
    attackStage: activeResult.value.attack_stage || '--',
    service: `${activeResult.value.service_profile?.name || '--'} / ${activeResult.value.service_profile?.protocol || '--'}/${activeResult.value.service_profile?.port || '--'}`,
  }
})

const sourceHeatItems = computed(() =>
  flowSourceNodes.value.map((item) => ({
    name: item.name,
    value: item.count,
  })),
)

const protocolItems = computed(() => {
  const counter = new Map()
  streamItems.value.forEach((item) => {
    const protocol = item.service_profile?.protocol || 'N/A'
    counter.set(protocol, (counter.get(protocol) || 0) + 1)
  })
  const total = Math.max(1, streamItems.value.length)
  return [...counter.entries()]
    .map(([name, value]) => ({
      name,
      value,
      percent: Number(((value / total) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.value - a.value)
})

const patchForm = (source) => {
  Object.keys(form).forEach((key) => delete form[key])
  Object.entries(source).forEach(([key, value]) => {
    form[key] = value
  })
}

const fillAttackSample = () => {
  patchForm({
    flow_duration: 1293792,
    packet_rate: 7.7292,
    byte_rate: 8991.3989,
    syn_rate: 0,
    dst_port_entropy: 0.0012,
    failed_login_rate: 0,
    request_interval_std: 4.3087,
    payload_mean: 1163.3,
  })
}

const fillBenignSample = () => {
  patchForm({
    flow_duration: 250,
    packet_rate: 70,
    byte_rate: 2600,
    syn_rate: 0.04,
    dst_port_entropy: 0.21,
    failed_login_rate: 0.01,
    request_interval_std: 0.56,
    payload_mean: 680,
  })
}

const formatPercent = (value) => (value == null ? '--' : `${(Number(value) * 100).toFixed(2)}%`)

const stopPlaybackTimer = () => {
  if (playbackTimer) {
    clearTimeout(playbackTimer)
    playbackTimer = null
  }
}

const buildReplayItems = (items) => {
  const logMap = new Map((store.detectionLogs || []).map((item) => [item.id, item]))
  return items.map((item) => {
    const detail = logMap.get(item.id) || {}
    const assetContext = detail.asset_context || {}
    const sourceIp = assetContext.source_ip || `10.1.${(item.id % 200) + 10}.${(item.id % 100) + 10}`
    const destinationIp = assetContext.destination_ip || `172.16.${(item.id % 6) + 1}.${(item.id % 180) + 20}`
    return {
      ...item,
      ...detail,
      asset_context: assetContext,
      source_ip: sourceIp,
      destination_ip: destinationIp,
      timestamp: item.timestamp || detail.created_at,
      source: detail.source || 'stream_simulation',
    }
  })
}

const pumpReplay = async () => {
  stopPlaybackTimer()
  if (!replayRunning.value) return

  playbackTimer = setTimeout(async () => {
    if (!replayQueue.value.length) {
      await loadReplayBatch({ autoPlay: true })
      return
    }

    const next = replayQueue.value.shift()
    activeResult.value = next
    playedCount.value += 1
    streamItems.value = [next, ...streamItems.value.filter((item) => item.id !== next.id)].slice(0, 10)
    await pumpReplay()
  }, replaySpeed.value)
}

const loadReplayBatch = async (options = {}) => {
  const { autoPlay = false, resetStream = true } = options
  replayLoading.value = true
  try {
    const response = await simulateRealtimeStream({ sample_size: sampleSize.value })
    replaySummary.value = response.data || { total: 0, alerts: 0, unknownCount: 0 }
    await store.refreshRuntimeData()
    replayQueue.value = buildReplayItems(response.data.items || [])
    if (resetStream) {
      streamItems.value = []
      playedCount.value = 0
    }
    if (!activeResult.value && replayQueue.value.length) {
      activeResult.value = replayQueue.value[0]
    }
    if (autoPlay) {
      replayRunning.value = true
      await pumpReplay()
    }
  } catch (error) {
    ElMessage.error(error?.message || '实时流回放加载失败')
  } finally {
    replayLoading.value = false
  }
}

const startReplay = async () => {
  if (!replayQueue.value.length) {
    await loadReplayBatch({ autoPlay: true })
    return
  }
  replayRunning.value = true
  await pumpReplay()
}

const pauseReplay = () => {
  replayRunning.value = false
  stopPlaybackTimer()
}

const selectStreamItem = (row) => {
  activeResult.value = row
}

const handleManualDetect = async () => {
  manualLoading.value = true
  try {
    pauseReplay()
    const response = await runDetection({ ...form, _source: 'manual_debug' })
    const assetContext = response.data.result.asset_context || {}
    const result = {
      ...response.data.result,
      source: 'manual_debug',
      timestamp: response.data.result.created_at,
      source_ip: assetContext.source_ip || '10.1.10.10',
      destination_ip: assetContext.destination_ip || '172.16.1.20',
      asset_context: assetContext,
    }
    activeResult.value = result
    streamItems.value = [result, ...streamItems.value.filter((item) => item.id !== result.id)].slice(0, 10)
    await store.refreshRuntimeData()
    ElMessage.success('调试检测已完成')
  } catch (error) {
    ElMessage.error(error?.message || '调试检测失败')
  } finally {
    manualLoading.value = false
  }
}

const openBatchDetection = () => {
  router.push('/batch-detection')
}

onMounted(async () => {
  if (!store.systemOverview) {
    await store.bootstrap()
  }
  fillAttackSample()
  await loadReplayBatch()
  await startReplay()
})

onBeforeUnmount(() => {
  pauseReplay()
})
</script>
