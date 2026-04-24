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
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8' },
    },
    color: ['#00d4ff', '#7b2fff', '#00e676', '#ffaa00', '#ff3366', '#00b8d4', '#6200ea'],
    series: [
      {
        name: '攻击分布',
        type: 'pie',
        radius: ['42%', '72%'],
        roseType: 'area',
        itemStyle: { borderRadius: 4, borderColor: 'rgba(2, 11, 24, 0.5)', borderWidth: 2 },
        label: { color: 'rgba(168, 200, 232, 0.8)', fontSize: 11 },
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
