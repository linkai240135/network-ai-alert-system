<template>
  <div class="page-stack operation-page-shell">
    <section class="operation-command-stage operation-command-stage-incidents">
      <div class="operation-command-main">
        <span class="soc-command-kicker">Incident Response</span>
        <h3>事件处置工作台</h3>
        <div class="soc-command-tags">
          <span>{{ board.stats?.pending || 0 }} 待研判</span>
          <span>{{ board.stats?.processing || 0 }} 研判中</span>
          <span>{{ board.stats?.resolved || 0 }} 已处置</span>
          <span>{{ board.stats?.feedbackCount || 0 }} 反馈</span>
        </div>
        <div class="operation-metric-grid operation-metric-grid-incident">
          <div class="operation-metric-card">
            <span>事件总数</span>
            <strong><CountUpValue :value="board.stats?.total || 0" /></strong>
          </div>
          <div class="operation-metric-card">
            <span>待研判</span>
            <strong><CountUpValue :value="board.stats?.pending || 0" /></strong>
          </div>
          <div class="operation-metric-card">
            <span>反馈记录</span>
            <strong><CountUpValue :value="board.stats?.feedbackCount || 0" /></strong>
          </div>
        </div>
      </div>

      <div class="operation-command-side">
        <div class="operation-command-card pulse-panel">
          <span>当前事件</span>
          <strong>{{ activeIncident ? (activeIncident.incident_no || activeIncident.attack_type || '当前事件') : '未选择' }}</strong>
          <div class="operation-command-badges">
            <span>{{ activeIncident?.attack_stage || '--' }}</span>
            <span>{{ activeIncident?.status || '--' }}</span>
          </div>
        </div>
        <div class="action-row">
          <el-button type="primary" plain :disabled="!activeIncident" :loading="aiLoading" @click="handleAiAnalyzeIncident">
            DeepSeek 研判
          </el-button>
          <el-button type="success" plain :disabled="!activeIncident" :loading="aiReportLoading" @click="handleAiReport">
            AI 报告
          </el-button>
        </div>
      </div>
    </section>

    <div class="two-column operation-workbench">
      <PanelCard title="事件列表" subtitle="事件是安全运营的核心单位，而不是孤立的单条告警。">
        <div class="filter-row">
          <el-select v-model="filters.status" placeholder="事件状态" clearable>
            <el-option label="待研判" value="待研判" />
            <el-option label="研判中" value="研判中" />
            <el-option label="待处置" value="待处置" />
            <el-option label="已处置" value="已处置" />
          </el-select>
          <el-select v-model="filters.severity" placeholder="风险等级" clearable>
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
          </el-select>
          <div></div>
          <el-button type="primary" @click="loadIncidents">刷新列表</el-button>
        </div>

        <el-table :data="incidents" stripe border @row-click="selectIncident">
          <el-table-column prop="incident_no" label="事件编号" min-width="170" />
          <el-table-column prop="attack_type" label="事件类型" min-width="120" />
          <el-table-column prop="attack_stage" label="攻击阶段" min-width="140" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="event_count" label="聚合数" width="90" />
          <el-table-column prop="last_seen_at" label="最近时间" min-width="160" />
        </el-table>
      </PanelCard>

      <PanelCard title="研判工作台" subtitle="支持状态流转、报告导出、同源链路分析和误报反馈。">
        <Transition name="focus-card-swap" mode="out-in">
          <el-empty v-if="!activeIncident" key="empty" description="请选择事件" />
          <div v-else :key="`${activeIncident.id}-${activeIncident.status}`" class="page-stack">
            <div class="service-card service-card-standalone operation-focus-card">
              <div class="service-card-top">
                <div>
                  <strong>{{ activeIncident.attack_type }}</strong>
                  <p>{{ activeIncident.asset?.asset_name || '--' }}</p>
                </div>
                <SeverityTag :level="activeIncident.severity" />
              </div>
              <div class="service-card-metrics">
                <span>{{ activeIncident.source_ip }} -> {{ activeIncident.destination_ip }}</span>
                <span>{{ activeIncident.status }}</span>
              </div>
              <div class="service-card-desc">
                {{ activeIncident.attack_stage }} · 聚合 {{ activeIncident.event_count }} 条同类事件
              </div>
            </div>

            <div class="status-flow-card">
              <div class="status-flow-track">
                <div
                  v-for="step in incidentStatusFlow"
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

            <div class="action-row">
              <el-button type="primary" @click="changeStatus('研判中')">标记研判中</el-button>
              <el-button type="warning" @click="changeStatus('待处置')">升级待处置</el-button>
              <el-button type="success" @click="changeStatus('已处置')">标记已处置</el-button>
              <el-button type="primary" plain :loading="aiLoading" @click="handleAiAnalyzeIncident">DeepSeek 研判</el-button>
              <el-button type="success" plain :loading="aiReportLoading" @click="handleAiReport">AI 报告</el-button>
              <el-button @click="exportReport">导出事件报告</el-button>
            </div>

            <div class="filter-row">
              <el-switch v-model="useReasonerMode" inline-prompt active-text="深度推理" inactive-text="快速研判" />
              <el-tag type="info">当前模型：{{ currentAiModelLabel }}</el-tag>
            </div>

            <el-input v-model="note" type="textarea" :rows="3" placeholder="输入记录" />
            <div class="action-row">
              <el-button @click="appendNote">追加研判记录</el-button>
            </div>

            <div class="two-column">
              <div class="panel-mini">
                <div class="timeline-panel-head">
                  <h4>同源攻击链路分析</h4>
                  <el-button size="small" @click="loadSourceChain">刷新链路</el-button>
                </div>
                <TransitionGroup
                  v-if="sourceChain.timeline?.length"
                  name="timeline-stagger"
                  tag="div"
                  class="animated-timeline"
                >
                  <div
                    v-for="item in sourceChain.timeline"
                    :key="`${item.incident_no}-${item.time}`"
                    class="timeline-node"
                  >
                    <div class="timeline-node-head">
                      <strong>{{ item.attack_type }}</strong>
                      <span>{{ item.time }}</span>
                    </div>
                    <p>{{ item.attack_stage }} · {{ item.target }}</p>
                  </div>
                </TransitionGroup>
                <el-empty v-else description="暂无链路" />
              </div>

              <div class="panel-mini">
                <h4>误报反馈反哺训练</h4>
                <el-select v-model="feedback.feedback_type" class="full-width" placeholder="反馈类型">
                  <el-option label="误报" value="误报" />
                  <el-option label="漏报修正" value="漏报修正" />
                  <el-option label="标签修正" value="标签修正" />
                </el-select>
                <el-input v-model="feedback.expected_label" class="top-gap" placeholder="期望标签" />
                <el-input v-model="feedback.comment" class="top-gap" type="textarea" :rows="3" placeholder="输入反馈" />
                <div class="action-row">
                  <el-button type="danger" plain @click="submitFeedback">提交反馈</el-button>
                </div>
              </div>
            </div>

            <div class="recommendation-list">
              <div v-for="(item, index) in activeIncident.recommendations || []" :key="`${index}-${item}`" class="recommendation-item">
                <span>{{ index + 1 }}</span>
                <p>{{ item }}</p>
              </div>
            </div>

            <Transition name="ai-card-expand">
              <div v-if="aiIncidentInsight" class="ai-analysis-card">
                <div class="ai-analysis-head">
                  <strong>DeepSeek 事件研判</strong>
                  <span>{{ aiIncidentInsight.provider }} / {{ aiIncidentInsight.model }} / {{ aiIncidentInsight.mode }}</span>
                </div>
                <p>{{ aiIncidentInsight.content }}</p>

                <div v-if="aiIncidentInsight.knowledge_hits?.length" class="ai-analysis-section">
                  <h4>知识库依据</h4>
                  <div class="insight-list compact-list">
                    <div v-for="item in aiIncidentInsight.knowledge_hits" :key="item.id" class="insight-card">
                      <div class="insight-card-top">
                        <strong>{{ item.title }}</strong>
                        <span>{{ item.category }} / {{ item.retrieval_method }} / {{ item.retrieval_engine }}</span>
                      </div>
                      <div class="rag-score-grid">
                        <div>
                          <span>融合分</span>
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

                <div v-if="aiIncidentInsight.strategy_plan?.length" class="ai-analysis-section">
                  <h4>处置策略生成</h4>
                  <div class="recommendation-list">
                    <div v-for="(item, index) in aiIncidentInsight.strategy_plan" :key="`${item.step}-${index}`" class="recommendation-item">
                      <span>{{ index + 1 }}</span>
                      <p>{{ item.step }} / {{ item.owner }} / {{ item.action }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>

            <TransitionGroup name="timeline-stagger" tag="div" class="animated-timeline activity-timeline">
              <div v-for="item in activeIncident.activities || []" :key="item.id" class="timeline-node">
                <div class="timeline-node-head">
                  <strong>{{ item.action_type }}</strong>
                  <span>{{ item.operator }}</span>
                </div>
                <p>{{ item.content }}</p>
                <p>{{ item.created_at }}</p>
              </div>
            </TransitionGroup>
          </div>
        </Transition>
      </PanelCard>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  addIncidentNote,
  analyzeIncidentWithAi,
  fetchIncidentBoard,
  fetchIncidentDetail,
  fetchIncidentReport,
  fetchIncidents,
  fetchSourceChain,
  generateIncidentReportWithAi,
  submitIncidentFeedback,
  updateIncidentStatus,
} from '../api/dashboard'
import CountUpValue from '../components/CountUpValue.vue'
import PanelCard from '../components/PanelCard.vue'
import SeverityTag from '../components/SeverityTag.vue'
import { exportTextFile } from '../utils/export'

const incidents = ref([])
const board = ref({ stats: {} })
const activeIncident = ref(null)
const aiIncidentInsight = ref(null)
const aiLoading = ref(false)
const aiReportLoading = ref(false)
const useReasonerMode = ref(false)
const sourceChain = ref({ timeline: [] })
const note = ref('')
const filters = reactive({
  status: '',
  severity: '',
})
const feedback = reactive({
  feedback_type: '误报',
  expected_label: 'BENIGN',
  comment: '',
})

const currentAiModel = computed(() => (useReasonerMode.value ? 'deepseek-reasoner' : 'deepseek-chat'))
const currentAiModelLabel = computed(() => (useReasonerMode.value ? 'deepseek-reasoner' : 'deepseek-chat'))
const incidentStatusFlow = computed(() => {
  const incident = activeIncident.value
  if (!incident) return []

  const status = incident.status

  return [
    {
      key: 'aggregate',
      label: '事件聚合',
      desc: '按源地址与攻击阶段完成告警聚合',
      active: true,
      current: status === '待研判',
    },
    {
      key: 'triage',
      label: '人工研判',
      desc: '结合 DeepSeek 与知识库完成定级',
      active: ['研判中', '待处置', '已处置'].includes(status),
      current: status === '研判中',
    },
    {
      key: 'response',
      label: '处置执行',
      desc: '输出隔离、封禁与加固动作',
      active: ['待处置', '已处置'].includes(status),
      current: status === '待处置',
    },
    {
      key: 'closure',
      label: '闭环回写',
      desc: status === '已处置' ? '已回写处置结果与反馈样本' : '等待闭环复盘与回写',
      active: status === '已处置',
      current: status === '已处置',
    },
  ]
})

const loadIncidents = async () => {
  const response = await fetchIncidents(filters)
  incidents.value = response.data.items || []
  if (!activeIncident.value && incidents.value.length) {
    await selectIncident(incidents.value[0])
  }
}

const loadBoard = async () => {
  const response = await fetchIncidentBoard()
  board.value = response.data || { stats: {} }
}

const loadSourceChain = async () => {
  if (!activeIncident.value?.source_ip) return
  const response = await fetchSourceChain(activeIncident.value.source_ip)
  sourceChain.value = response.data || { timeline: [] }
}

const selectIncident = async (row) => {
  const response = await fetchIncidentDetail(row.id)
  activeIncident.value = response.data
  aiIncidentInsight.value = null
  await loadSourceChain()
}

const handleAiAnalyzeIncident = async () => {
  if (!activeIncident.value) return
  aiLoading.value = true
  try {
    const response = await analyzeIncidentWithAi({ incident: activeIncident.value, model: currentAiModel.value })
    aiIncidentInsight.value = response.data
    ElMessage.success(response.data.mode === 'online' ? 'DeepSeek 事件研判已生成' : '事件研判结果已生成')
  } catch (error) {
    ElMessage.error(error?.message || 'DeepSeek 事件研判失败，请检查后端服务和 API Key')
  } finally {
    aiLoading.value = false
  }
}

const handleAiReport = async () => {
  if (!activeIncident.value) return
  aiReportLoading.value = true
  try {
    const response = await generateIncidentReportWithAi({ incident: activeIncident.value, model: currentAiModel.value })
    exportTextFile(`AI-${activeIncident.value.incident_no}.md`, response.data.report, 'text/markdown;charset=utf-8;')
    aiIncidentInsight.value = response.data
    ElMessage.success('AI 事件报告已导出')
  } catch (error) {
    ElMessage.error(error?.message || 'AI 事件报告生成失败')
  } finally {
    aiReportLoading.value = false
  }
}

const changeStatus = async (status) => {
  if (!activeIncident.value) return
  await updateIncidentStatus(activeIncident.value.id, { status, operator: 'analyst' })
  ElMessage.success('事件状态已更新')
  await loadBoard()
  await loadIncidents()
  await selectIncident(activeIncident.value)
}

const appendNote = async () => {
  if (!activeIncident.value || !note.value.trim()) return
  await addIncidentNote(activeIncident.value.id, { content: note.value.trim(), operator: 'analyst' })
  ElMessage.success('研判记录已追加')
  note.value = ''
  await selectIncident(activeIncident.value)
}

const exportReport = async () => {
  if (!activeIncident.value) return
  const response = await fetchIncidentReport(activeIncident.value.id)
  exportTextFile(response.data.filename, response.data.content, 'text/markdown;charset=utf-8;')
  ElMessage.success('事件报告已导出')
}

const toScorePercent = (value) => Math.max(0, Math.min(100, Math.round(Number(value || 0) * 100)))

const submitFeedback = async () => {
  if (!activeIncident.value) return
  const response = await submitIncidentFeedback(activeIncident.value.id, {
    feedback_type: feedback.feedback_type,
    expected_label: feedback.expected_label,
    comment: feedback.comment,
    operator: 'analyst',
  })
  const created = response.data.feedback_sample_created
  ElMessage.success(created ? '反馈已提交，并已回写训练样本' : '反馈已提交')
  feedback.comment = ''
  await loadBoard()
  await selectIncident(activeIncident.value)
}

onMounted(async () => {
  await loadBoard()
  await loadIncidents()
})
</script>
