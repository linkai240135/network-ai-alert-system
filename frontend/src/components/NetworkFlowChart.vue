<template>
  <div ref="chartRef" class="network-flow-chart"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  activeId: { type: [String, Number], default: null },
})

const chartRef = ref(null)
let chartInstance = null

const RISK_COLOR = {
  high: '#ff3366',
  warning: '#ffaa00',
  safe: '#00e676',
  default: '#00d4ff',
}

const getRiskColor = (item) => {
  if (String(item.risk_level || '').includes('高')) return RISK_COLOR.high
  if (item.unknown_flag) return RISK_COLOR.warning
  return RISK_COLOR.safe
}

const buildGraph = () => {
  const items = props.items.slice(0, 12)
  if (!items.length) return { nodes: [], links: [] }

  const sourceMap = new Map()
  const targetMap = new Map()

  items.forEach((item) => {
    const src = item.source_ip || '--'
    const tgt = item.destination_ip || '--'
    if (!sourceMap.has(src)) sourceMap.set(src, { count: 0, highRisk: 0 })
    const s = sourceMap.get(src)
    s.count += 1
    if (String(item.risk_level || '').includes('高')) s.highRisk += 1

    if (!targetMap.has(tgt)) targetMap.set(tgt, { name: item.asset_context?.asset_name || tgt, count: 0 })
    targetMap.get(tgt).count += 1
  })

  const sources = [...sourceMap.entries()].sort((a, b) => b[1].highRisk - a[1].highRisk).slice(0, 5)
  const targets = [...targetMap.entries()].sort((a, b) => b[1].count - a[1].count).slice(0, 5)

  const nodes = []
  const links = []

  // Source nodes — left column
  sources.forEach(([ip, info], i) => {
    const y = 15 + (i * 70) / Math.max(sources.length - 1, 1)
    nodes.push({
      id: `src:${ip}`,
      name: ip,
      x: 10,
      y,
      symbolSize: 10 + info.count * 3,
      itemStyle: { color: info.highRisk > 0 ? RISK_COLOR.high : RISK_COLOR.safe },
      label: { show: true, position: 'right', formatter: ip, fontSize: 11, color: 'rgba(168,200,232,0.9)' },
      category: 0,
    })
  })

  // Target nodes — right column
  targets.forEach(([ip, info], i) => {
    const y = 15 + (i * 70) / Math.max(targets.length - 1, 1)
    nodes.push({
      id: `tgt:${ip}`,
      name: info.name,
      x: 90,
      y,
      symbolSize: 10 + info.count * 3,
      itemStyle: { color: '#7b2fff' },
      label: { show: true, position: 'left', formatter: info.name, fontSize: 11, color: 'rgba(168,200,232,0.9)' },
      category: 1,
    })
  })

  // Links
  items.forEach((item) => {
    const srcId = `src:${item.source_ip || '--'}`
    const tgtId = `tgt:${item.destination_ip || '--'}`
    const hasSrc = nodes.some((n) => n.id === srcId)
    const hasTgt = nodes.some((n) => n.id === tgtId)
    if (!hasSrc || !hasTgt) return

    const color = getRiskColor(item)
    links.push({
      source: srcId,
      target: tgtId,
      lineStyle: { color, width: 1.5, opacity: 0.6, curveness: 0.2 },
      label: {
        show: false,
        formatter: item.label || '--',
        fontSize: 10,
        color: color,
      },
    })
  })

  return { nodes, links }
}

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value, null, { renderer: 'canvas' })

  const { nodes, links } = buildGraph()

  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8', fontSize: 12 },
      formatter: (params) => {
        if (params.dataType === 'node') return params.data.name
        return `${params.data.source?.replace('src:', '')} → ${params.data.target?.replace('tgt:', '')}`
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        coordinateSystem: null,
        left: '5%',
        right: '5%',
        top: '5%',
        bottom: '5%',
        data: nodes,
        links,
        roam: false,
        focusNodeAdjacency: true,
        lineStyle: { curveness: 0.2 },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3 },
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
      },
    ],
  }, true)
}

watch(() => [props.items, props.activeId], renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
