<template>
  <section class="stat-card">
    <div class="stat-card-top">
      <p class="stat-label">{{ label }}</p>
      <div class="stat-dot"></div>
    </div>
    <strong>{{ value }}</strong>
  </section>
</template>

<script setup>
defineProps({
  label: String,
  value: [String, Number],
  description: String,
})
</script>
