<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  seriesName: { type: String, default: '趋势' },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    tooltip: { trigger: 'axis' },
    grid: { left: 44, right: 18, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: props.labels,
      axisLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.28)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6e83a2' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.14)' } },
      axisLabel: { color: '#6e83a2' },
    },
    series: [
      {
        name: props.seriesName,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3, color: '#1976ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(25, 118, 255, 0.26)' },
            { offset: 1, color: 'rgba(25, 118, 255, 0.02)' },
          ]),
        },
        data: props.values,
      },
    ],
  })
}

watch(() => [props.labels, props.values], renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
