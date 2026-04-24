<template>
  <el-tag :type="type" effect="dark">{{ level }}风险</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: { type: String, default: '中' },
})

const type = computed(() => {
  if (props.level === '低') return 'success'
  if (props.level === '中') return 'warning'
  return 'danger'
})
</script>
