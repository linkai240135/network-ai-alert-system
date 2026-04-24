<template>
  <span>{{ displayText }}</span>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  duration: { type: Number, default: 1200 },
  decimals: { type: Number, default: null },
  locale: { type: String, default: 'zh-CN' },
})

const currentValue = ref(0)
let frameId = 0

const stopAnimation = () => {
  if (frameId) {
    cancelAnimationFrame(frameId)
    frameId = 0
  }
}

const toNumber = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const animateTo = (nextValue) => {
  stopAnimation()
  const startValue = currentValue.value
  const delta = nextValue - startValue
  const startTime = performance.now()

  const step = (time) => {
    const progress = Math.min((time - startTime) / props.duration, 1)
    const eased = 1 - (1 - progress) * (1 - progress)
    currentValue.value = startValue + delta * eased
    if (progress < 1) {
      frameId = requestAnimationFrame(step)
    } else {
      currentValue.value = nextValue
      frameId = 0
    }
  }

  frameId = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (next) => {
    animateTo(toNumber(next))
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopAnimation()
})

const displayText = computed(() => {
  const numeric = currentValue.value
  if (props.decimals != null) {
    return numeric.toLocaleString(props.locale, {
      minimumFractionDigits: props.decimals,
      maximumFractionDigits: props.decimals,
    })
  }

  if (Math.abs(numeric) >= 1000) {
    return Math.round(numeric).toLocaleString(props.locale)
  }

  if (Number.isInteger(numeric)) {
    return String(numeric)
  }

  return numeric.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
})
</script>
