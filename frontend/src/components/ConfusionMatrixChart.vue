<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  matrix: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  const data = []
  props.matrix.forEach((row, rowIndex) => {
    row.forEach((value, colIndex) => {
      data.push([colIndex, rowIndex, value])
    })
  })
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8' },
    },
    xAxis: {
      type: 'category',
      data: props.labels,
      axisLabel: { color: 'rgba(0, 212, 255, 0.5)', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
    },
    yAxis: {
      type: 'category',
      data: props.labels,
      axisLabel: { color: 'rgba(0, 212, 255, 0.5)', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.map((item) => item[2]), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['rgba(0, 212, 255, 0.1)', '#00d4ff'] },
      textStyle: { color: 'rgba(168, 200, 232, 0.6)' },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: { show: true, color: '#e8f4ff', fontSize: 11 },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0, 212, 255, 0.5)' } },
      },
    ],
  })
}

watch(() => [props.labels, props.matrix], renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
