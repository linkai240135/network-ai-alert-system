<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value) return
  chartInstance = chartInstance || echarts.init(chartRef.value)
  chartInstance.setOption({
    animationDuration: 1000,
    animationEasing: 'quarticOut',
    animationDurationUpdate: 500,
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 40, right: 18, top: 42, bottom: 26 },
    xAxis: {
      type: 'category',
      data: props.items.map((item) => item.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.28)' } },
      axisLabel: { color: '#6e83a2' },
    },
    yAxis: {
      type: 'value',
      max: 1,
      splitLine: { lineStyle: { color: 'rgba(118, 145, 182, 0.14)' } },
      axisLabel: { color: '#6e83a2' },
    },
    series: [
      {
        name: 'Accuracy',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { color: '#2563eb', borderRadius: [8, 8, 0, 0] },
        data: props.items.map((item) => item.accuracy),
      },
      {
        name: 'Recall',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { color: '#14b8a6', borderRadius: [8, 8, 0, 0] },
        data: props.items.map((item) => item.recall),
      },
      {
        name: 'F1',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { color: '#f97316', borderRadius: [8, 8, 0, 0] },
        data: props.items.map((item) => item.f1_score),
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
