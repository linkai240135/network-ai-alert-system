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
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8' },
    },
    legend: {
      top: 0,
      textStyle: { color: 'rgba(168, 200, 232, 0.7)', fontSize: 11 },
    },
    grid: { left: 40, right: 18, top: 42, bottom: 26 },
    xAxis: {
      type: 'category',
      data: props.items.map((item) => item.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
      axisLabel: { color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      max: 1,
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)', type: 'dashed' } },
      axisLabel: { color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
    },
    series: [
      {
        name: 'Accuracy',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#00d4ff', borderRadius: [3, 3, 0, 0] },
        data: props.items.map((item) => item.accuracy),
      },
      {
        name: 'Recall',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#7b2fff', borderRadius: [3, 3, 0, 0] },
        data: props.items.map((item) => item.recall),
      },
      {
        name: 'F1',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#00e676', borderRadius: [3, 3, 0, 0] },
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
