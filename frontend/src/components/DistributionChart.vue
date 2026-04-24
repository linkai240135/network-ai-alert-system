<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({}),
  },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    color: ['#b54d2d', '#d08a2f', '#3b8f6b', '#4a76b6', '#7e5ad7', '#d85d78'],
    series: [
      {
        name: '攻击分布',
        type: 'pie',
        radius: ['42%', '72%'],
        roseType: 'area',
        itemStyle: { borderRadius: 12 },
        data: Object.entries(props.data).map(([name, value]) => ({ name, value })),
      },
    ],
  })
}

watch(() => props.data, renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
