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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(4, 18, 48, 0.92)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#a8c8e8' },
    },
    xAxis: {
      type: 'category',
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
      axisLabel: { interval: 0, rotate: props.items.length > 5 ? 20 : 0, color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
      data: props.items.map((item) => item[props.categoryKey]),
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)', type: 'dashed' } },
      axisLabel: { color: 'rgba(0, 212, 255, 0.45)', fontSize: 11 },
    },
    series: [
      {
        name: props.seriesName,
        type: 'bar',
        barWidth: 20,
        data: props.items.map((item) => item[props.valueKey]),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: props.color || '#00d4ff' },
            { offset: 1, color: (props.color || '#00d4ff') + '44' },
          ]),
          borderRadius: [3, 3, 0, 0],
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
