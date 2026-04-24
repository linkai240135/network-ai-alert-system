<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { top: 0, data: ['源IP', '业务资产'] },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        force: { repulsion: 180, edgeLength: [80, 140] },
        data: props.nodes.map((item) => ({
          ...item,
          category: item.category === 'source' ? 0 : 1,
          itemStyle: {
            color: item.category === 'source' ? '#d95c4f' : '#2f7df6',
          },
        })),
        categories: [{ name: '源IP' }, { name: '业务资产' }],
        links: props.links.map((item) => ({
          ...item,
          lineStyle: {
            width: item.severity === '高' ? 3 : 2,
            color: item.severity === '高' ? '#d95c4f' : '#7aa7ff',
          },
          label: { show: true, formatter: item.label },
        })),
        label: { show: true, position: 'right' },
      },
    ],
  })
}

watch(() => [props.nodes, props.links], renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
