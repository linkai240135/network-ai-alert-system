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
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8' },
    },
    grid: { left: 44, right: 18, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: props.labels,
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
      axisTick: { show: false },
      axisLabel: { color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)', type: 'dashed' } },
      axisLabel: { color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
    },
    series: [
      {
        name: props.seriesName,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#00d4ff', shadowColor: 'rgba(0, 212, 255, 0.5)', shadowBlur: 8 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.01)' },
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
