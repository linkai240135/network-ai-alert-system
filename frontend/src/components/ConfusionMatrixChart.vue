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
    tooltip: { position: 'top' },
    xAxis: { type: 'category', data: props.labels },
    yAxis: { type: 'category', data: props.labels },
    visualMap: {
      min: 0,
      max: Math.max(...data.map((item) => item[2]), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: { show: true },
        emphasis: { itemStyle: { shadowBlur: 8 } },
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
