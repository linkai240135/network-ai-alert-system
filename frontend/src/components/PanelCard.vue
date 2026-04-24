<template>
  <section class="panel-card">
    <div class="panel-header">
      <div class="panel-title-group">
        <h3>{{ title }}</h3>
      </div>
      <div class="panel-extra">
        <slot name="extra" />
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  title: String,
  subtitle: String,
})
</script>
