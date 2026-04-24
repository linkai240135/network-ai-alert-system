<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  categoryKey: { type: String, default: 'name' },
  valueKey: { type: String, default: 'value' },
  seriesName: { type: String, default: '数值' },
  color: { type: String, default: '#1677ff' },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    animationDuration: 900,
    animationEasing: 'quarticOut',
    animationDurationUpdate: 500,
    grid: { left: 48, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.28)' } },
      axisLabel: { interval: 0, rotate: props.items.length > 5 ? 20 : 0, color: '#6e83a2' },
      data: props.items.map((item) => item[props.categoryKey]),
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.14)' } },
      axisLabel: { color: '#6e83a2' },
    },
    series: [
      {
        name: props.seriesName,
        type: 'bar',
        barWidth: 24,
        data: props.items.map((item) => item[props.valueKey]),
        itemStyle: {
          color: props.color,
          borderRadius: [8, 8, 0, 0],
        },
      },
    ],
  })
}

watch(() => props.items, renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chartInstance?.dispose()
})
</script>
