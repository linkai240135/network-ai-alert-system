<template>
  <div class="page-stack">
    <div class="chain-overview-grid train-stage-grid">
      <div v-for="item in assetChain" :key="item.title" class="chain-node-card">
        <span>{{ item.step }}</span>
        <strong>{{ item.title }}</strong>
      </div>
    </div>

    <PanelCard title="资产画像概览" subtitle="从资产、服务和事件维度评估通信业务暴露风险">
      <div class="summary-grid">
        <div class="summary-item"><span>资产总数</span><strong>{{ stats.total || 0 }}</strong></div>
        <div class="summary-item"><span>高风险资产</span><strong>{{ stats.riskyAssets || 0 }}</strong></div>
        <div class="summary-item"><span>关联事件资产</span><strong>{{ stats.incidentBoundAssets || 0 }}</strong></div>
      </div>
    </PanelCard>

    <PanelCard title="资产拓扑 / 业务链路" subtitle="展示源地址、目标资产和安全事件之间的关联关系">
      <TopologyGraph :nodes="topology.nodes || []" :links="topology.links || []" />
    </PanelCard>

    <PanelCard title="资产列表" subtitle="展示平台纳管资产、服务端口、风险评分和最近活跃时间">
      <el-empty v-if="!assets.length" description="暂无资产" />
      <el-table v-else :data="assets" stripe border>
        <el-table-column prop="asset_code" label="资产编号" min-width="150" />
        <el-table-column prop="asset_name" label="资产名称" min-width="160" />
        <el-table-column prop="ip_address" label="IP 地址" min-width="140" />
        <el-table-column prop="business_unit" label="业务域" min-width="160" />
        <el-table-column prop="service_name" label="服务" min-width="120" />
        <el-table-column label="服务端口" min-width="120">
          <template #default="{ row }">{{ row.protocol }}/{{ row.port }}</template>
        </el-table-column>
        <el-table-column prop="risk_score" label="风险评分" width="110" />
        <el-table-column prop="last_seen_at" label="最近活跃" min-width="160" />
      </el-table>
    </PanelCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchAssetTopology } from '../api/dashboard'
import PanelCard from '../components/PanelCard.vue'
import TopologyGraph from '../components/TopologyGraph.vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const assets = computed(() => store.assets)
const stats = computed(() => store.assetStats || {})
const topology = ref({ nodes: [], links: [] })
const assetChain = [
  { step: '01', title: '资产识别', description: '识别目标 IP、业务域、服务端口和资产类型。' },
  { step: '02', title: '风险画像', description: '结合告警数量、事件状态和风险评分形成资产画像。' },
  { step: '03', title: '链路关联', description: '从源地址、目标资产和事件编号还原攻击关联关系。' },
  { step: '04', title: '处置支撑', description: '为事件研判和业务低扰动处置提供资产上下文。' },
]

const loadTopology = async () => {
  const response = await fetchAssetTopology()
  topology.value = response.data || { nodes: [], links: [] }
}

onMounted(async () => {
  if (!store.assets.length) {
    await store.bootstrap()
  }
  await loadTopology()
})
</script>
