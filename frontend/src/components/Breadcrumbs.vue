<template>
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <template v-for="(item, i) in items" :key="i">
      <router-link v-if="item.to" :to="item.to" class="crumb-link">{{ item.label }}</router-link>
      <button v-else-if="item.onClick" type="button" class="crumb-link crumb-btn" @click="item.onClick">{{ item.label }}</button>
      <span v-else class="crumb-current">{{ item.label }}</span>
      <span v-if="i < items.length - 1" class="crumb-sep">/</span>
    </template>
  </nav>
</template>

<script setup>
defineProps({
  // [{ label, to? , onClick? }] — `to` for a real route, `onClick` for a
  // step that's just in-page state (e.g. a forum category, not its own
  // URL). Items with neither render as the plain, non-clickable current
  // page. Every ancestor should be reachable so the full path back to
  // Home is always one click away, not just the immediate parent.
  items: { type: Array, required: true },
})
</script>

<style scoped>
.breadcrumbs {
  display: flex; align-items: center; flex-wrap: wrap; gap: 7px;
  margin-bottom: 22px; font-size: 13px;
}
.crumb-link {
  color: var(--text-dim); text-decoration: none; font-weight: 600;
  transition: color .15s;
}
.crumb-link:hover { color: var(--accent); }
.crumb-btn { background: none; border: none; padding: 0; font: inherit; cursor: pointer; }
.crumb-current { color: var(--text); font-weight: 700; }
.crumb-sep { color: var(--text-dim); opacity: .45; }
</style>
